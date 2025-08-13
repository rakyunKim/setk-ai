"""LangGraph 서버 없이 직접 그래프를 실행하는 서비스."""
import asyncio
import json
from typing import Dict, Any
from uuid import uuid4

from src.api.dto.request_dto import TeacherInputRequest
from src.api.config.app_config import logger
from agent.utils.config.config import DEFAULT_MODEL


class DirectGraphService:
    """
    LangGraph 서버 없이 직접 그래프를 실행하는 서비스.
    메모리에서 직접 그래프를 실행하여 동시성 제한 없이 처리 가능.
    """
    
    def __init__(self):
        """서비스 초기화."""
        self.logger = logger
        self._graph = None
        self._graph_lock = asyncio.Lock()
    
    @property
    async def graph(self):
        """그래프 인스턴스를 lazy loading으로 가져오기."""
        if self._graph is None:
            async with self._graph_lock:
                if self._graph is None:  # double-check locking
                    # agent 모듈에서 graph import
                    from agent.agent import graph
                    self._graph = graph
                    self.logger.info("LangGraph 그래프 로드 완료")
        return self._graph
    
    async def process_single_student(self, student: TeacherInputRequest) -> Dict[str, Any]:
        """단일 학생 처리 (직접 그래프 실행)."""
        try:
            # 그래프 가져오기
            graph_instance = await self.graph
            
            # Thread ID 생성 (메모리 실행이므로 UUID 사용)
            thread_id = str(uuid4())
            self.logger.debug(f"Thread 생성됨: {thread_id} (메모리 실행)")
            
            # 입력 데이터 준비
            teacher_dict = student.to_dict()
            self.logger.debug(f"[DEBUG] TeacherInputRequest.to_dict(): {teacher_dict}")
            
            input_data = {
                "teacher_input": teacher_dict,
                "generation_status": "in_progress",
                "semester": student.semester,
                "academic_year": student.academic_year
            }
            
            # 그래프 실행 설정
            config = {
                "configurable": {
                    "thread_id": thread_id,
                    "model_name": DEFAULT_MODEL  # 환경변수에서 읽도록 수정
                }
            }
            
            # 비동기로 그래프 실행
            self.logger.debug(f"그래프 실행 시작: {thread_id}")
            
            # ainvoke를 사용하여 비동기 실행
            result = await graph_instance.ainvoke(
                input_data,
                config=config
            )
            
            self.logger.debug(f"그래프 실행 완료: {thread_id}")
            
            # 결과에서 detailed_record 추출
            detailed_record = None
            
            if isinstance(result, dict):
                if "detailed_record" in result:
                    detailed_record = result["detailed_record"]
            
            if not detailed_record:
                self.logger.error("detailed_record를 찾을 수 없음")
                self.logger.error(f"전체 결과: {json.dumps(result, ensure_ascii=False, indent=2)[:500]}")
                raise ValueError("세특 생성 결과를 찾을 수 없습니다")
            
            # content만 로그에 출력
            content_only = detailed_record.get("content", "내용 없음") if isinstance(detailed_record, dict) else str(detailed_record)
            self.logger.info(f"세특 결과 (content): {content_only}")
            
            return detailed_record
            
        except Exception as e:
            self.logger.error(f"처리 실패: {type(e).__name__}: {str(e)}")
            raise
    
    async def process_batch_students(self, students: list[TeacherInputRequest]) -> list[Dict[str, Any]]:
        """여러 학생을 동시에 처리."""
        # 각 학생에 대해 비동기 태스크 생성
        tasks = [
            self.process_single_student(student) 
            for student in students
        ]
        
        # 모든 태스크를 동시에 실행
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 에러 처리
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                self.logger.error(f"학생 {students[i].name} 처리 실패: {result}")
                # 실패한 경우 에러 정보 포함
                processed_results.append({
                    "error": str(result),
                    "student_name": students[i].name
                })
            else:
                processed_results.append(result)
        
        return processed_results


# 싱글톤 인스턴스 생성
direct_graph_service = DirectGraphService()