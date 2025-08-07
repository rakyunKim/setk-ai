"""API 응답 DTO
"""
from datetime import datetime

from fastapi.responses import JSONResponse
from pydantic import BaseModel

from agent.utils.dto.types import DetailedRecord


class DetailedRecordResponse(BaseModel):
    """API 응답용 세특 모델"""
    student_id: int
    subject: str
    content: str
    generated_at: datetime
    version: int
    status: str = "success"
    
    @classmethod
    def from_dict(cls, data: DetailedRecord):
        """딕셔너리에서 생성"""
        return cls(**data)


class ErrorResponse(BaseModel):
    """에러 응답 모델"""
    error_code: str
    message: str
    
    def to_json_response(self, status_code: int = 500) -> JSONResponse:
        """JSONResponse로 변환"""
        return JSONResponse(
            status_code=status_code,
            content=self.model_dump()
        )