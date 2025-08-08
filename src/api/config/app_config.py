"""FastAPI 애플리케이션 설정 모듈
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.config.env_config import EnvConfig
from src.utils.logger import setup_logger
from src.api.exception.global_exception_handler import register_exception_handlers


class AppConfig:
    """FastAPI 애플리케이션 설정 클래스"""
    
    def __init__(self):
        # 환경 설정 로드
        self.config = EnvConfig.get_config()
        
        # 로거 설정
        self.logger = setup_logger(
            __name__,
            level=self.config["log_level"],
            debug_mode=self.config["debug_mode"]
        )
        
        # LangGraph 서버 설정
        self.langgraph_server_url = self.config["langgraph_server_url"]
        self.assistant_id = self.config["assistant_id"]
        
        # FastAPI 앱 인스턴스 생성
        self.app = self._create_app()
    
    def _create_app(self) -> FastAPI:
        """FastAPI 앱 생성 및 설정"""
        app = FastAPI(
            title="세부능력 특기사항 생성 API",
            description="LangGraph Server를 활용한 세특 생성 서비스",
            version="1.0.0"
        )
        
        # CORS 미들웨어 설정
        app.add_middleware(
            CORSMiddleware,
            allow_origins=self.config["cors_origins"],
            allow_credentials=self.config["cors_allow_credentials"],
            allow_methods=self.config["cors_allow_methods"],
            allow_headers=self.config["cors_allow_headers"],
        )
        
        # Global Exception Handler 등록
        register_exception_handlers(app)
        
        self.logger.info(f"FastAPI 앱 생성 완료 - 환경: {self.config['environment']}")
        self.logger.info(f"CORS origins: {self.config['cors_origins']}")
        
        return app
    
    def get_app(self) -> FastAPI:
        """FastAPI 앱 인스턴스 반환"""
        return self.app
    
    def get_logger(self):
        """로거 인스턴스 반환"""
        return self.logger
    
    def get_langgraph_config(self) -> dict:
        """LangGraph 서버 설정 반환"""
        return {
            "server_url": self.langgraph_server_url,
            "assistant_id": self.assistant_id
        }


# 싱글톤 인스턴스 생성
app_config = AppConfig()

# 외부에서 사용할 인스턴스들
app = app_config.get_app()
logger = app_config.get_logger()
LANGGRAPH_SERVER_URL = app_config.langgraph_server_url
ASSISTANT_ID = app_config.assistant_id