import logging
import sys


class ColoredFormatter(logging.Formatter):
    """컬러 출력을 위한 커스텀 포매터"""
    
    # ANSI 색상 코드
    COLORS = {
        'DEBUG': '\033[36m',     # Cyan
        'INFO': '\033[32m',      # Green  
        'WARNING': '\033[33m',   # Yellow
        'ERROR': '\033[31m',     # Red
    }
    RESET = '\033[0m'
    
    def format(self, record):
        # 로그 레벨에 따른 색상 적용
        log_color = self.COLORS.get(record.levelname, self.RESET)
        record.levelname = f"{log_color}{record.levelname}{self.RESET}"
        record.msg = f"{log_color}{record.msg}{self.RESET}"
        return super().format(record)

def setup_logger(
    name: str = "setk_ai",
    level: str = "INFO",
    debug_mode: bool = False
) -> logging.Logger:
    """로거 설정
    
    Args:
        name: 로거 이름
        level: 기본 로그 레벨 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        debug_mode: 디버그 모드 활성화 여부
    
    Returns:
        설정된 로거 객체
    """
    logger = logging.getLogger(name)
    
    # 환경변수에서 로그 레벨 다시 확인 (동적 업데이트)
    import os
    env_log_level = os.getenv("LOG_LEVEL", level).upper()
    env_debug_mode = os.getenv("DEBUG_MODE", str(debug_mode)).lower() == "true"
    
    # 디버그 모드나 환경변수에 따라 레벨 설정
    if env_debug_mode or debug_mode:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(getattr(logging, env_log_level, logging.INFO))
    
    # 이미 핸들러가 설정되어 있으면 중복 설정 방지
    if logger.handlers:
        return logger
    
    # INFO, DEBUG, WARNING용 stdout 핸들러
    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setLevel(logging.DEBUG)
    stdout_handler.addFilter(lambda record: record.levelno < logging.ERROR)
    
    # ERROR용 stderr 핸들러  
    stderr_handler = logging.StreamHandler(sys.stderr)
    stderr_handler.setLevel(logging.ERROR)
    
    # 포맷 설정
    formatter = ColoredFormatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    stdout_handler.setFormatter(formatter)
    stderr_handler.setFormatter(formatter)
    
    # 핸들러 추가
    logger.addHandler(stdout_handler)
    logger.addHandler(stderr_handler)
    
    return logger

# 기본 로거 인스턴스
logger = setup_logger()