"""LangGraph 서버와의 통신을 담당하는 서비스 모듈."""
import asyncio
import json
from typing import Dict, Any
import httpx
from fastapi import HTTPException
from src.api.dto.request_dto import TeacherInputRequest
from src.api.config.app_config import logger, LANGGRAPH_SERVER_URL, ASSISTANT_ID


class LangGraphService:
    """
    LangGraph 서버 통신 서비스.
    랭그래프 생성을 요청할때에는 총 3단계로 나뉨
    1. 쓰레드 생성
    2. 런 실행
    3. 결과 가져오기
    """
    
    def __init__(self):
        """서비스 초기화."""
        self.server_url = LANGGRAPH_SERVER_URL
        self.assistant_id = ASSISTANT_ID
        self.logger = logger
    
    async def create_thread(self) -> str:
        """LangGraph Thread 생성."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self.server_url}/threads",
                json={
                    "metadata": {
                        "workflow": "세부능력특기사항생성",
                        "created_by": "api"
                    }
                }
            )

            if response.status_code != 200:
                raise HTTPException(
                    status_code=response.status_code, 
                    detail=f"Thread 생성 실패: {response.text}"
                )
            
            data = response.json()
            return data["thread_id"]
    
    async def run_workflow(self, thread_id: str, student_data: TeacherInputRequest) -> str:
        """워크플로우 실행 (Run 생성)."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            # 디버깅: student_data 내용 확인
            teacher_dict = student_data.to_dict()
            self.logger.debug(f"[DEBUG] TeacherInputRequest.to_dict(): {teacher_dict}")
            self.logger.debug(f"[DEBUG] student_number in teacher_dict: {teacher_dict.get('student_number', 'NOT_FOUND')}")
            
            payload = {
                "assistant_id": self.assistant_id,
                "input": {
                    "teacher_input": teacher_dict,
                    "generation_status": "pending",
                    "semester": student_data.semester,
                    "academic_year": student_data.academic_year
                },
                "config": {
                    "configurable": {
                        "model_name": "openai"
                    }
                }
            }
            
            response = await client.post(
                f"{self.server_url}/threads/{thread_id}/runs",
                json=payload
            )

            if response.status_code != 200:
                raise HTTPException(
                    status_code=response.status_code, 
                    detail=f"Run 실행 실패: {response.text}"
                )
            
            data = response.json()
            return data["run_id"]
    
    async def get_run_result(self, thread_id: str, run_id: str) -> Dict[str, Any]:
        """Run 결과 가져오기 (폴링)."""
        async with httpx.AsyncClient(timeout=60.0) as client:
            max_attempts = 100  # 더 많은 시도 횟수 (간격이 짧아졌으므로)
            
            for attempt in range(max_attempts):
                # Run 상태 확인
                response = await client.get(
                    f"{self.server_url}/threads/{thread_id}/runs/{run_id}"
                )
                
                if response.status_code != 200:
                    raise HTTPException(
                        status_code=response.status_code, 
                        detail=f"Run 상태 조회 실패: {response.text}"
                    )
                
                run_data = response.json()
                status = run_data.get("status")
                
                # 5번마다만 로그 출력 (또는 상태가 변경될 때)
                if attempt % 5 == 0 or status in ["success", "error"]:
                    self.logger.debug(f"Run 상태: {status} (attempt {attempt + 1}/{max_attempts})")
                
                if status == "success":
                    # 실제 결과 가져오기 (state endpoint 사용)
                    result_response = await client.get(
                        f"{self.server_url}/threads/{thread_id}/state"
                    )
                    
                    self.logger.debug(f"런 실행 결과 State 응답 코드: {result_response.status_code}")
                    
                    if result_response.status_code == 200:
                        state_data = result_response.json()
                        
                        # values는 현재 state의 모든 필드를 담고 있는 dict
                        if "values" in state_data:
                            values = state_data["values"]
                            
                            if isinstance(values, dict):
                                # values가 state 자체인 경우
                                
                                # detailed_record가 있는지 확인
                                if "detailed_record" in values:
                                    return values  # 전체 state 반환
                                else:
                                    self.logger.warning("values에 detailed_record 없음")
                                    self.logger.debug(f"values 내용 일부: {str(values)[:500]}...")
                                    return values
                            elif isinstance(values, list) and len(values) > 0:
                                # 리스트인 경우 마지막 값
                                final_state = values[-1]
                                self.logger.info(
                                    f"최종 상태 (리스트): "
                                    f"{final_state.keys() if isinstance(final_state, dict) else type(final_state)}"
                                )
                                return final_state
                            else:
                                self.logger.warning(f"values가 예상치 못한 타입: {type(values)}")
                                raise HTTPException(status_code=500, detail="values가 예상치 못한 타입")
                        else:
                            self.logger.warning("values 키 없음, 전체 state 반환")
                            raise HTTPException(status_code=500, detail="values 키 없음")
                    else:
                        self.logger.error(f"State 조회 실패: {result_response.text[:200]}")
                        raise HTTPException(status_code=500, detail="워크플로우 결과 조회 실패")
                        
                elif status == "error":
                    error_msg = run_data.get("error", "워크플로우 실행 실패")
                    self.logger.error(f"워크플로우 에러: {error_msg}")
                    raise HTTPException(status_code=500, detail=error_msg)
                
                # 점진적 백오프 패턴으로 대기
                if attempt < 10:
                    await asyncio.sleep(0.3)  # 처음 10번은 0.3초 (3초간)
                elif attempt < 30:
                    await asyncio.sleep(0.5)  # 다음 20번은 0.5초 (10초간)
                else:
                    await asyncio.sleep(1.0)  # 그 이후는 1초
            
            raise HTTPException(status_code=504, detail="워크플로우 실행 시간 초과")
    
    async def process_single_student(self, student: TeacherInputRequest) -> Dict[str, Any]:
        """단일 학생 처리 (Thread 생성 → Run 실행 → 결과 반환)."""
        try:
            # 1. Thread 생성
            thread_id = await self.create_thread()
            self.logger.debug(f"Thread 생성됨: {thread_id}")
            
            # 2. Run 실행
            run_id = await self.run_workflow(thread_id, student)
            self.logger.debug(f"Run 시작됨: {run_id}")
            
            # 3. 결과 가져오기
            result = await self.get_run_result(thread_id, run_id)
            
            # 4. 결과에서 detailed_record 추출
            detailed_record = None
            
            if isinstance(result, dict):
                if "detailed_record" in result:
                    detailed_record = result["detailed_record"]
            if not detailed_record:
                self.logger.error("detailed_record를 찾을 수 없음")
                self.logger.error(f"전체 결과: {json.dumps(result, ensure_ascii=False, indent=2)[:500]}")
                raise HTTPException(status_code=500, detail="세특 생성 결과를 찾을 수 없습니다")
                
            # content만 로그에 출력 (전체 결과가 아닌)
            content_only = detailed_record.get("content", "내용 없음") if isinstance(detailed_record, dict) else str(detailed_record)
            self.logger.info(f"세특 결과 (content): {content_only}")
            return detailed_record
            
        except Exception as e:
            self.logger.error(f"처리 실패: {type(e).__name__}: {str(e)}")
            raise


# 싱글톤 인스턴스 생성
langgraph_service = LangGraphService()