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
    
    # 이미 핸들러가 설정되어 있으면 중복 설정 방지
    if logger.handlers:
        return logger
    
    # 디버그 모드에서는 DEBUG 레벨로 설정
    if debug_mode:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    
    # 콘솔 핸들러 생성
    console_handler = logging.StreamHandler(sys.stdout)
    
    # 포맷 설정
    formatter = ColoredFormatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_handler.setFormatter(formatter)
    
    # 핸들러 추가
    logger.addHandler(console_handler)
    
    return logger

# 기본 로거 인스턴스
logger = setup_logger()