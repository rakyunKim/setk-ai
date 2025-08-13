import os
from typing import Optional
from datetime import datetime

from langchain_core.runnables import RunnableConfig
from typing_extensions import TypedDict

# 기본 AI 모델 설정
DEFAULT_MODEL = os.getenv("AI_MODEL", "gemini")

class CustomConfigParam(TypedDict):
    model_name: str  # "openai", "anthropic", or "ollama"

class CustomConfig(RunnableConfig):
    configurable: CustomConfigParam

def get_model_name(config: Optional[RunnableConfig] = None) -> str:
    """설정에서 모델 이름을 가져오는 유틸리티 함수
    
    Args:
        config: RunnableConfig 객체 (선택적)
        
    Returns:
        모델 이름 문자열 (기본값: DEFAULT_MODEL)
    """
    if config and hasattr(config, 'configurable'):
        return config.configurable.get("model_name", DEFAULT_MODEL)
    return DEFAULT_MODEL

def log_token_usage(response, logger, node_name=""):
    """토큰 사용량 로깅 유틸리티 함수
    
    Args:
        response: LLM 모델의 응답 객체
        logger: 로깅에 사용할 logger 인스턴스
        node_name: 로그에 표시할 노드 이름 (선택적)
        
    Returns:
        dict: 토큰 사용량 정보 (usage_metadata가 있는 경우) 또는 None
    """

    # 토큰 사용량 로그 파일 경로
    token_log_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))),
        "token_usage.log"
    )
    
    if hasattr(response, 'usage_metadata') and response.usage_metadata:
        usage = response.usage_metadata
        
        # dict 형태로 접근
        if isinstance(usage, dict):
            input_tokens = usage.get('input_tokens', 0)
            output_tokens = usage.get('output_tokens', 0)
            total_tokens = usage.get('total_tokens', 0)
        # 객체 속성으로 접근
        else:
            input_tokens = getattr(usage, 'input_tokens', 0)
            output_tokens = getattr(usage, 'output_tokens', 0)
            total_tokens = getattr(usage, 'total_tokens', 0)
        
        # 로그 메시지 생성
        log_message = f"[{node_name}] 토큰 사용량 - 입력: {input_tokens}, 출력: {output_tokens}, 총: {total_tokens}"
        
        # 토큰 전용 로그 파일에 직접 기록
        try:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            with open(token_log_path, 'a', encoding='utf-8') as f:
                f.write(f"{timestamp} - {log_message}\n")
                
                # Gemini 1.5 Flash 비용 계산 (참고용)
                cost_per_1m_input = 0.075  # $0.075 per 1M input tokens
                cost_per_1m_output = 0.30  # $0.30 per 1M output tokens
                input_cost = (input_tokens / 1_000_000) * cost_per_1m_input
                output_cost = (output_tokens / 1_000_000) * cost_per_1m_output
                total_cost = input_cost + output_cost
                
                f.write(f"{timestamp} - [{node_name}] 예상 비용: ${total_cost:.6f} (입력: ${input_cost:.6f}, 출력: ${output_cost:.6f})\n")
                f.write("-" * 80 + "\n")
        except Exception as e:
            logger.warning(f"토큰 사용량 파일 기록 실패: {e}")
        
        return {
            'input_tokens': input_tokens,
            'output_tokens': output_tokens,
            'total_tokens': total_tokens
        }
    
    # usage_metadata가 없는 경우 디버깅 로그
    logger.debug(f"[{node_name}] 토큰 사용량 정보 없음 (usage_metadata 미지원)")
    
    # 파일에도 기록
    try:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(token_log_path, 'a', encoding='utf-8') as f:
            f.write(f"{timestamp} - [{node_name}] 토큰 사용량 정보 없음\n")
    except:
        pass
    
    return None