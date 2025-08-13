"""LangGraph 서버와의 통신을 담당하는 서비스 모듈."""
import asyncio
import json
from typing import Dict, Any
import httpx
from fastapi import HTTPException
from src.api.dto.request_dto import TeacherInputRequest
from src.api.config.app_config import logger, LANGGRAPH_SERVER_URL, ASSISTANT_ID
from agent.utils.config.config import DEFAULT_MODEL


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
        # 여러 LangGraph 서버 엔드포인트 (로드 밸런싱용)
        self.server_urls = [
            "http://localhost:8123",
            "http://localhost:8124",
            "http://localhost:8125"
        ]
        
        # 배치 할당 방식: 각 서버당 10개씩
        self.batch_size = 10
        self.current_server_index = 0
        self.current_server_count = 0  # 현재 서버에 할당된 요청 수
        
        self.assistant_id = ASSISTANT_ID
        self.logger = logger
        
        # 기본 서버 URL (환경변수에서 읽은 값, 폴백용)
        self.fallback_server_url = LANGGRAPH_SERVER_URL
    
    def get_next_server_url(self) -> str:
        """
        배치 방식으로 다음 서버 URL 반환.
        각 서버에 10개씩 할당한 후 다음 서버로 이동.
        """
        # 서버가 여러 개 있을 때만 로드 밸런싱
        if len(self.server_urls) > 1:
            url = self.server_urls[self.current_server_index]
            
            # 현재 서버에 할당된 요청 수 증가
            self.current_server_count += 1
            
            # 디버깅 로그
            self.logger.debug(
                f"서버 할당: {url} (서버 {self.current_server_index + 1}/{len(self.server_urls)}, "
                f"현재 서버 요청 수: {self.current_server_count}/{self.batch_size})"
            )
            
            # 현재 서버가 배치 크기만큼 찼으면 다음 서버로
            if self.current_server_count >= self.batch_size:
                self.current_server_index = (self.current_server_index + 1) % len(self.server_urls)
                self.current_server_count = 0
                self.logger.info(f"다음 서버로 전환: 서버 {self.current_server_index + 1}")
            
            return url
        else:
            # 서버가 하나면 폴백 URL 사용
            return self.fallback_server_url
    
    async def create_thread(self, server_url: str = None) -> tuple[str, str]:
        """
        LangGraph Thread 생성.
        Returns: (thread_id, server_url) 튜플
        """
        # 서버 URL이 지정되지 않으면 자동 선택
        if server_url is None:
            server_url = self.get_next_server_url()
            
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{server_url}/threads",
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
            thread_id = data["thread_id"]
            
            # thread_id와 서버 URL을 함께 반환
            return thread_id, server_url
    
    async def run_workflow(self, thread_id: str, student_data: TeacherInputRequest, server_url: str) -> str:
        """워크플로우 실행 (Run 생성)."""
        async with httpx.AsyncClient(timeout=120.0) as client:
            # 디버깅: student_data 내용 확인
            teacher_dict = student_data.to_dict()
            self.logger.debug(f"[DEBUG] TeacherInputRequest.to_dict(): {teacher_dict}")
            self.logger.debug(f"[DEBUG] student_number in teacher_dict: {teacher_dict.get('student_id', 'NOT_FOUND')}")
            
            payload = {
                "assistant_id": self.assistant_id,
                "input": {
                    "teacher_input": teacher_dict,
                    "generation_status": "in_progress",
                    "semester": student_data.semester,
                    "academic_year": student_data.academic_year
                },
                "config": {
                    "configurable": {
                        "model_name": DEFAULT_MODEL  # 환경변수에서 읽도록 수정
                    }
                }
            }
            
            response = await client.post(
                f"{server_url}/threads/{thread_id}/runs",
                json=payload
            )

            if response.status_code != 200:
                raise HTTPException(
                    status_code=response.status_code, 
                    detail=f"Run 실행 실패: {response.text}"
                )
            
            data = response.json()
            return data["run_id"]
    
    async def get_run_result(self, thread_id: str, run_id: str, server_url: str) -> Dict[str, Any]:
        """Run 결과 가져오기 (폴링)."""
        # 개별 요청당 타임아웃 설정 (전체 세션은 제한 없음)
        timeout = httpx.Timeout(10.0, connect=5.0, read=10.0, write=10.0, pool=None)
        async with httpx.AsyncClient(timeout=timeout) as client:
            max_attempts = 200  # 더 많은 폴링 허용
            
            for attempt in range(max_attempts):
                # Run 상태 확인
                response = await client.get(
                    f"{server_url}/threads/{thread_id}/runs/{run_id}"
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
                        f"{server_url}/threads/{thread_id}/state"
                    )
                    
                    self.logger.debug(f"런 실행 결과 State 응답 코드: {result_response.status_code}")

                    if result_response.status_code != 200:
                        raise HTTPException(
                            status_code=result_response.status_code,
                            detail=f"결과 조회 실패: {result_response.text}"
                        )
                    
                    state_data = result_response.json()
                    values = state_data.get("values", {})

                    if values:
                        return values
                    else:
                        raise HTTPException(status_code=500, detail="성공은 했으나 결과 값이 없음")
                    
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
            # 1. Thread 생성 (서버 URL도 함께 받음)
            thread_id, server_url = await self.create_thread()
            self.logger.debug(f"Thread 생성됨: {thread_id} (서버: {server_url})")
            
            # 2. 같은 서버로 Run 실행
            run_id = await self.run_workflow(thread_id, student, server_url)
            self.logger.debug(f"Run 시작됨: {run_id} (서버: {server_url})")
            
            # 3. 같은 서버에서 결과 가져오기
            result = await self.get_run_result(thread_id, run_id, server_url)
            
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