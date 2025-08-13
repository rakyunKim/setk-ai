"""LangGraph Server와 통신하는 프록시 API.
"""
from datetime import datetime
from typing import List
import httpx

from src.api.config.app_config import LANGGRAPH_SERVER_URL, app
from src.api.services.generate_service import generate_service
from src.api.dto.request_dto import TeacherInputRequest
from src.api.dto.response_dto import DetailedRecordResponse, ErrorResponse


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
    return await generate_service.generate_single_student(request)


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
    return await generate_service.generate_batch_students(requests)


@app.get("/health", tags=["시스템"])
async def health_check():
    """헬스 체크 엔드포인트"""
    # Direct Graph Mode인지 확인
    import os
    use_direct_graph = os.environ.get("USE_DIRECT_GRAPH", "true").lower() == "true"
    
    if not use_direct_graph:
        # 기존: LangGraph Server 상태도 체크
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{LANGGRAPH_SERVER_URL}/health")
                langgraph_status = "healthy" if response.status_code == 200 else "unhealthy"
        except Exception:
            langgraph_status = "unreachable"
    else:
        # 새로운: Direct Graph Mode
        langgraph_status = "direct_mode (no server)"
    
    return {
        "status": "healthy",
        "mode": "direct_graph" if use_direct_graph else "langgraph_server",
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