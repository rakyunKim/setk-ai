"""LangGraph Server와 통신하는 프록시 API
"""
import asyncio
import json
from datetime import datetime
from typing import List

import httpx
from fastapi import HTTPException

# App 설정 import
from src.api.config.app_config import ASSISTANT_ID, LANGGRAPH_SERVER_URL, app, logger

# DTO import
from src.api.dto.request_dto import TeacherInputRequest
from src.api.dto.response_dto import DetailedRecordResponse, ErrorResponse
from src.api.exception.api_exception import ApiException
from src.api.utils.response_util import ResponseUtil


# LangGraph Thread/Run Helper Functions
async def create_thread() -> str:
    """LangGraph Thread 생성"""
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"{LANGGRAPH_SERVER_URL}/threads",
            json={
                "metadata": {
                    "workflow": "세부능력특기사항생성",
                    "created_by": "api"
                }
            }
        )
        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail=f"Thread 생성 실패: {response.text}")
        
        data = response.json()
        return data["thread_id"]


async def run_workflow(thread_id: str, student_data: TeacherInputRequest) -> str:
    """워크플로우 실행 (Run 생성)"""
    async with httpx.AsyncClient(timeout=30.0) as client:
        payload = {
            "assistant_id": ASSISTANT_ID,
            "input": {
                "teacher_input": student_data.to_dict(),
                "generation_status": "pending",
                "semester": "2학기",
                "academic_year": 2024
            },
            "config": {
                "configurable": {
                    "model_name": "openai"
                }
            }
        }
        
        response = await client.post(
            f"{LANGGRAPH_SERVER_URL}/threads/{thread_id}/runs",
            json=payload
        )
        
        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail=f"Run 실행 실패: {response.text}")
        
        data = response.json()
        return data["run_id"]


async def get_run_result(thread_id: str, run_id: str) -> dict:
    """Run 결과 가져오기 (폴링)"""
    async with httpx.AsyncClient(timeout=60.0) as client:
        max_attempts = 30  # 최대 30초 대기
        for attempt in range(max_attempts):
            # Run 상태 확인
            response = await client.get(
                f"{LANGGRAPH_SERVER_URL}/threads/{thread_id}/runs/{run_id}"
            )
            
            if response.status_code != 200:
                raise HTTPException(status_code=response.status_code, detail=f"Run 상태 조회 실패: {response.text}")
            
            run_data = response.json()
            status = run_data.get("status")
            
            logger.info(f"Run 상태: {status} (attempt {attempt + 1}/{max_attempts})")
            
            if status == "success":
                # 실제 결과 가져오기 (state endpoint 사용)
                result_response = await client.get(
                    f"{LANGGRAPH_SERVER_URL}/threads/{thread_id}/state"
                )
                
                logger.debug(f"State 응답 코드: {result_response.status_code}")
                
                if result_response.status_code == 200:
                    state_data = result_response.json()
                    logger.debug(f"State 데이터 키: {state_data.keys()}")
                    
                    # values는 현재 state의 모든 필드를 담고 있는 dict
                    if "values" in state_data:
                        values = state_data["values"]
                        logger.debug(f"values 타입: {type(values)}")
                        
                        if isinstance(values, dict):
                            # values가 state 자체인 경우 (LangGraph Server의 일반적인 형태)
                            logger.debug(f"State 필드들: {list(values.keys())[:10]}...")  # 처음 10개만 출력
                            
                            # detailed_record가 있는지 확인
                            if "detailed_record" in values:
                                logger.info("values에서 detailed_record 발견!")
                                return values  # 전체 state 반환
                            else:
                                logger.warning("values에 detailed_record 없음")
                                logger.debug(f"values 내용 일부: {str(values)[:500]}...")
                                return values
                        elif isinstance(values, list) and len(values) > 0:
                            # 리스트인 경우 마지막 값
                            final_state = values[-1]
                            logger.info(f"최종 상태 (리스트): {final_state.keys() if isinstance(final_state, dict) else type(final_state)}")
                            return final_state
                        else:
                            logger.warning(f"values가 예상치 못한 타입: {type(values)}")
                            return values
                    else:
                        logger.warning("values 키 없음, 전체 state 반환")
                        return state_data
                else:
                    logger.error(f"State 조회 실패: {result_response.text[:200]}")
                    raise HTTPException(status_code=500, detail="워크플로우 결과 조회 실패")
                    
            elif status == "error":
                error_msg = run_data.get("error", "워크플로우 실행 실패")
                logger.error(f"워크플로우 에러: {error_msg}")
                raise HTTPException(status_code=500, detail=error_msg)
            
            # 아직 진행중이면 1초 대기
            await asyncio.sleep(1)
        
        raise HTTPException(status_code=504, detail="워크플로우 실행 시간 초과")


async def process_single_student(student: TeacherInputRequest) -> dict:
    """단일 학생 처리 (Thread 생성 → Run 실행 → 결과 반환)"""
    try:
        # 1. Thread 생성
        thread_id = await create_thread()
        logger.info(f"Thread 생성됨: {thread_id}")
        
        # 2. Run 실행
        run_id = await run_workflow(thread_id, student)
        logger.info(f"Run 시작됨: {run_id}")
        
        # 3. 결과 가져오기
        result = await get_run_result(thread_id, run_id)
        logger.debug(f"결과 타입: {type(result)}")
        logger.debug(f"결과 키: {result.keys() if isinstance(result, dict) else 'Not a dict'}")
        
        # 4. 결과에서 detailed_record 추출
        detailed_record = None
        
        # 다양한 위치에서 detailed_record 찾기
        if isinstance(result, dict):
            if "detailed_record" in result:
                detailed_record = result["detailed_record"]
                logger.info("detailed_record 바로 발견")
            elif "values" in result and isinstance(result["values"], list):
                # values 배열에서 찾기
                for value in result["values"]:
                    if isinstance(value, dict) and "detailed_record" in value:
                        detailed_record = value["detailed_record"]
                        logger.info("values 배열에서 detailed_record 발견")
                        break
            elif "value" in result and isinstance(result["value"], dict):
                if "detailed_record" in result["value"]:
                    detailed_record = result["value"]["detailed_record"]
                    logger.info("value에서 detailed_record 발견")
        
        if not detailed_record:
            logger.error("detailed_record를 찾을 수 없음")
            logger.debug(f"전체 결과: {json.dumps(result, ensure_ascii=False, indent=2)[:500]}")
            raise HTTPException(status_code=500, detail="세특 생성 결과를 찾을 수 없습니다")
            
        logger.info(f"detailed_record 찾음: {type(detailed_record)}")
        return detailed_record
        
    except Exception as e:
        logger.error(f"처리 실패: {type(e).__name__}: {str(e)}")
        raise

# Global Exception Handler
@app.exception_handler(Exception)
async def global_exception_handler(exc: Exception):
    """모든 예외를 통합 처리하는 Global Exception Handler"""
    logger.debug(f"Global Exception Handler Called: {type(exc)} - {str(exc)}")
    
    # ApiException 처리
    if isinstance(exc, ApiException):
        logger.debug("ApiException 처리")
        return ResponseUtil.error(exc.error_code, exc.message, int(exc.error_code))
    
    # HTTPException 처리
    elif isinstance(exc, HTTPException):
        logger.debug(f"HTTPException 처리: {exc.status_code} - {exc.detail}")
        # detail이 이미 dict 형태면 그대로 반환 (기존 ErrorResponse 형식)
        if isinstance(exc.detail, dict):
            from fastapi.responses import JSONResponse
            return JSONResponse(status_code=exc.status_code, content=exc.detail)
        # detail이 문자열이면 ResponseUtil로 변환
        return ResponseUtil.error(str(exc.status_code), exc.detail, exc.status_code)
    
    # httpx 오류를 구체적으로 처리
    elif isinstance(exc, httpx.RequestError):
        logger.debug(f"httpx.RequestError 처리: {str(exc)}")
        return ResponseUtil.error("503", f"외부 서비스(LangGraph) 연결 실패: {type(exc).__name__}", 503)
    
    # 기타 일반 예외 처리
    else:
        logger.debug(f"일반 Exception 처리: {str(exc)}")
        return ResponseUtil.error("500", f"서버 내부 오류: {str(exc)}", 500)


@app.post(
    "/api/v1/generate",
    response_model=DetailedRecordResponse,
    responses={
        400: {"model": ErrorResponse},
        500: {"model": ErrorResponse}
    },
    summary="세부능력 특기사항 생성",
    tags=["세특 생성"]
)
async def generate_detailed_record(request: TeacherInputRequest):
    """학생의 세부능력 특기사항을 생성합니다.
    
    - **student_number**: 학생 번호
    - **name**: 학생 이름
    - **subject_name**: 과목명
    - **midterm_score**: 2학기 중간 수행평가 점수
    - **final_score**: 2학기 기말 수행평가 점수
    - **additional_notes**: 추가 특이사항 (선택)
    """
    try:
        # LangGraph Thread/Run API 사용
        detailed_record = await process_single_student(request)
        
        # 성공 응답
        return ResponseUtil.success(detailed_record)
        
    except httpx.RequestError as e:
        raise HTTPException(
            status_code=503,
            detail=f"LangGraph Server 연결 실패: {str(e)}"
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"서버 오류: {str(e)}"
        )


@app.post(
    "/api/v1/generate-batch",
    response_model=List[DetailedRecordResponse],
    responses={
        400: {"model": ErrorResponse},
        500: {"model": ErrorResponse}
    },
    summary="세부능력 특기사항 배치 생성",
    tags=["세특 생성"]
)
async def generate_batch_detailed_records(requests: List[TeacherInputRequest]):
    """여러 학생의 세부능력 특기사항을 동시에 생성합니다.
    
    병렬 처리로 빠른 속도를 보장합니다.
    """
    try:
        # 모든 학생을 병렬로 처리
        tasks = []
        for student in requests:
            task = process_single_student(student)
            tasks.append(task)
        
        # 모든 작업 동시 실행
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 결과 처리
        successful_results = []
        failed_results = []
        
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                failed_results.append({
                    "student": requests[i].name,
                    "error": str(result)
                })
            else:
                successful_results.append(ResponseUtil.success(result))
        
        # 일부 실패한 경우 경고와 함께 성공한 것만 반환
        if failed_results:
            logger.warning(f"{len(failed_results)}명 처리 실패: {failed_results}")
        
        return successful_results
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"배치 처리 오류: {str(e)}"
        )


@app.get("/health", tags=["시스템"])
async def health_check():
    """헬스 체크 엔드포인트"""
    # LangGraph Server 상태도 체크
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{LANGGRAPH_SERVER_URL}/health")
            langgraph_status = "healthy" if response.status_code == 200 else "unhealthy"
    except Exception:
        langgraph_status = "unreachable"
    
    return {
        "status": "healthy",
        "langgraph_server": langgraph_status,
        "timestamp": datetime.now().isoformat()
    }


@app.get("/", tags=["시스템"])
async def root():
    """API 정보"""
    return {
        "name": "세부능력 특기사항 생성 API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health"
    }


if __name__ == "__main__":
    import uvicorn

    from src.api.config.app_config import app_config
    
    config = app_config.config
    uvicorn.run(
        "src.api.proxy_api:app", 
        host=config["api_host"], 
        port=config["api_port"], 
        reload=config["debug_mode"]
    )