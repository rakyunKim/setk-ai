"""환경별 설정 관리 모듈
"""
import os
from pathlib import Path

from dotenv import load_dotenv

from src.utils.logger import setup_logger

logger = setup_logger(__name__)

class EnvConfig:
    """환경 설정 관리 클래스"""
    
    @staticmethod
    def load_environment():
        """환경에 따라 적절한 .env 파일을 로드
        
        ENVIRONMENT는 반드시 시스템 환경변수로 설정:
        - ENVIRONMENT=local → .env.local 사용
        - ENVIRONMENT=production → .env.production 사용
        - 미설정 시 기본값: local (개발 환경 우선)
        """
        # 프로젝트 루트 디렉토리 찾기 (setk_ai 폴더를 찾을 때까지 상위로 이동)
        current_path = Path(__file__).resolve()
        root_dir = None
        
        # 상위 디렉토리를 탐색하며 setk_ai 폴더 찾기
        for parent in current_path.parents:
            if parent.name == "setk_ai":
                root_dir = parent
                break
        
        # setk_ai 폴더를 못 찾은 경우 fallback
        if root_dir is None:
            logger.warning("setk_ai 루트 디렉토리를 찾을 수 없음. 기본 경로 사용")
            root_dir = Path(__file__).parent.parent.parent
        
        # ENVIRONMENT는 시스템 환경변수에서만 읽음 (순환 의존성 방지)
        # 기본값을 local로 설정 (개발 환경 우선)
        environment = os.getenv("ENVIRONMENT", "local").lower()
        
        # 환경별 .env 파일 경로 설정
        env_file_map = {
            "local": root_dir / ".env.local",
            "production": root_dir / ".env.production",
            "prod": root_dir / ".env.production",  # prod 별칭 지원
        }
        
        # 환경별 .env 파일 결정 (기본값: .env.local)
        env_file = env_file_map.get(environment, root_dir / ".env.local")
        
        # 환경별 .env 파일 로드
        if env_file.exists():
            load_dotenv(env_file)
            logger.info(f"{environment} 환경 파일 로드: {env_file}")
            
            # 디버그: 로드된 주요 설정 확인
            logger.debug(f"로드된 CORS_ORIGINS: {os.getenv('CORS_ORIGINS')}")
            logger.debug(f"로드된 DEBUG_MODE: {os.getenv('DEBUG_MODE')}")
            logger.debug(f"로드된 API_PORT: {os.getenv('API_PORT')}")
        else:
            logger.error(f"환경 파일을 찾을 수 없음: {env_file}")
            logger.error("환경 파일이 없습니다. .env.local 또는 .env.production을 생성해주세요.")
        
        # 로드된 환경 정보 출력
        logger.info(f"현재 환경: {environment.upper()}")
        logger.info(f"디버그 모드: {os.getenv('DEBUG_MODE', 'false')}")
        logger.info(f"로그 레벨: {os.getenv('LOG_LEVEL', 'INFO')}")
        
        return environment
    
    @staticmethod
    def get_config():
        """현재 환경 설정을 딕셔너리로 반환"""
        import json
        
        # CORS origins 파싱 (문자열을 리스트로 변환)
        cors_origins_str = os.getenv("CORS_ORIGINS", '["*"]')
        try:
            cors_origins = json.loads(cors_origins_str)
        except json.JSONDecodeError:
            cors_origins = ["*"]
        
        # CORS methods 파싱
        cors_methods_str = os.getenv("CORS_ALLOW_METHODS", '["*"]')
        try:
            cors_methods = json.loads(cors_methods_str)
        except json.JSONDecodeError:
            cors_methods = ["*"]
        
        # CORS headers 파싱
        cors_headers_str = os.getenv("CORS_ALLOW_HEADERS", '["*"]')
        try:
            cors_headers = json.loads(cors_headers_str)
        except json.JSONDecodeError:
            cors_headers = ["*"]
        
        return {
            "environment": os.getenv("ENVIRONMENT", "local"),
            "debug_mode": os.getenv("DEBUG_MODE", "false").lower() == "true",
            "log_level": os.getenv("LOG_LEVEL", "INFO"),
            "langgraph_server_url": os.getenv("LANGGRAPH_SERVER_URL", "http://localhost:8123"),
            "assistant_id": os.getenv("ASSISTANT_ID", "agent"),
            "api_host": os.getenv("API_HOST", "0.0.0.0"),
            "api_port": int(os.getenv("API_PORT", "8000")),
            "cors_origins": cors_origins,
            "cors_allow_credentials": os.getenv("CORS_ALLOW_CREDENTIALS", "true").lower() == "true",
            "cors_allow_methods": cors_methods,
            "cors_allow_headers": cors_headers,
        }

# 모듈 import 시 자동으로 환경 로드
environment = EnvConfig.load_environment()