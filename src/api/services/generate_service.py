"""세부능력 특기사항 생성 비즈니스 로직을 담당하는 서비스 모듈."""
import asyncio
from typing import List, Dict, Any

import httpx
from fastapi import HTTPException

from src.api.dto.request_dto import TeacherInputRequest
from src.api.services.langgraph_service import langgraph_service
from src.api.utils.response_util import ResponseUtil
from src.api.config.app_config import logger


class GenerateService:
    """세부능력 특기사항 생성 서비스."""
    
    def __init__(self):
        """서비스 초기화."""
        self.langgraph_service = langgraph_service
        self.logger = logger
    
    async def generate_single_student(self, request: TeacherInputRequest):
        """단일 학생 세부능력 특기사항 생성."""
        try:
            # LangGraph 서비스 사용
            detailed_record = await self.langgraph_service.process_single_student(request)
            
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
    
    async def generate_batch_students(self, requests: List[TeacherInputRequest]):
        """여러 학생의 세부능력 특기사항을 동시에 생성."""
        try:
            # 모든 학생을 병렬로 처리
            tasks = []
            for student in requests:
                task = self.langgraph_service.process_single_student(student)
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
                self.logger.warning(f"{len(failed_results)}명 처리 실패: {failed_results}")
            
            return successful_results
            
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"배치 처리 오류: {str(e)}"
            )


# 싱글톤 인스턴스 생성
generate_service = GenerateService()