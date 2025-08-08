"""전역 예외 처리 핸들러 모듈."""
import httpx
from fastapi import HTTPException
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from src.api.exception.api_exception import ApiException
from src.api.utils.response_util import ResponseUtil
from src.utils.logger import setup_logger

# 로거 인스턴스 생성 (app_config에서 분리)
logger = setup_logger(__name__, level="DEBUG", debug_mode=True)


async def global_exception_handler(request, exc: Exception):
    """
    모든 예외를 통합 처리하는 Global Exception Handler.
    
    Spring의 @ControllerAdvice + @ExceptionHandler와 유사한 역할
    """
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
            return JSONResponse(status_code=exc.status_code, content=exc.detail)
        # detail이 문자열이면 ResponseUtil로 변환
        return ResponseUtil.error(str(exc.status_code), exc.detail, exc.status_code)
    
    # Pydantic 검증 에러 처리
    elif isinstance(exc, ValidationError):
        logger.debug(f"ValidationError 처리: {str(exc)}")
        # ValidationError에서 첫 번째 에러의 필드와 메시지 추출
        first_error = exc.errors()[0]
        field_name = ".".join(str(loc) for loc in first_error["loc"])
        error_message = f"필드 '{field_name}': {first_error['msg']}"
        return ResponseUtil.error("400", f"입력 값 검증 실패: {error_message}", 400)
    
    # httpx 오류를 구체적으로 처리
    elif isinstance(exc, httpx.RequestError):
        logger.debug(f"httpx.RequestError 처리: {str(exc)}")
        return ResponseUtil.error("503", f"외부 서비스(LangGraph) 연결 실패: {type(exc).__name__}", 503)
    
    # 기타 일반 예외 처리
    else:
        logger.debug(f"일반 Exception 처리: {str(exc)}")
        return ResponseUtil.error("500", f"서버 내부 오류: {str(exc)}", 500)


def register_exception_handlers(app):
    """
    FastAPI 앱에 예외 핸들러를 등록하는 함수.
    
    Spring의 @EnableWebMvc와 유사한 설정 역할
    """
    # Pydantic ValidationError 핸들러 등록
    app.add_exception_handler(ValidationError, global_exception_handler)
    # 모든 Exception 핸들러 등록
    app.add_exception_handler(Exception, global_exception_handler)
    logger.info("Global Exception Handler 등록 완료")