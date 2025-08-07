"""응답 유틸리티 클래스
Java Spring의 ResponseEntity 패턴을 FastAPI에 적용
"""
from fastapi.responses import JSONResponse

from agent.utils.dto.types import DetailedRecord
from src.api.dto.response_dto import DetailedRecordResponse, ErrorResponse


class ResponseUtil:
    """응답 생성 유틸리티"""
    
    @staticmethod
    def success(data: DetailedRecord) -> DetailedRecordResponse:
        """성공 응답 생성"""
        return DetailedRecordResponse.from_dict(data)
    
    @staticmethod
    def error(error_code: str, message: str, status_code: int = 500) -> JSONResponse:
        """에러 응답 생성"""
        error_response = ErrorResponse(
            error_code=error_code,
            message=message
        )
        return error_response.to_json_response(status_code)