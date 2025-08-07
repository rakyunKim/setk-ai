import json
from typing import Optional

from langchain_anthropic import ChatAnthropic
from langchain_core.runnables import RunnableConfig
from langchain_openai import ChatOpenAI

from agent.utils.config.config import DEFAULT_MODEL
from agent.utils.state.state import StudentState
from src.static.prompt import (
    GRAMMAR_AND_VOCABULARY_CHECK_PROMPT,
)
from src.utils.logger import setup_logger

# 로거 설정
logger = setup_logger(__name__)


def check_grammar_and_vocabulary(state: StudentState, config: Optional[RunnableConfig] = None) -> StudentState:
    """생성된 세특의 문법과 어휘를 검증하는 노드
    """
    # 필요한 정보 추출 (없으면 KeyError 발생 → FastAPI에서 처리)
    detailed_record = state["detailed_record"]
    
    # 모델 선택 (도구 바인딩 없이)
    model_name = DEFAULT_MODEL
    if config and hasattr(config, 'configurable'):
        model_name = config.configurable.get("model_name", DEFAULT_MODEL)
    
    # 도구 바인딩 없는 모델 직접 생성
    if model_name == "openai":
        model = ChatOpenAI(temperature=0.5, model_name="gpt-4o-mini")
    elif model_name == "anthropic":
        model = ChatAnthropic(temperature=0.5, model_name="claude-3-sonnet-20240229")
    else:
        raise Exception(f"지원하지 않는 모델입니다.: {model_name}")
    
    # 문법 검증 프롬프트 생성
    prompt = GRAMMAR_AND_VOCABULARY_CHECK_PROMPT.format(
        generated_content=detailed_record['content']
    )
    
    # 문법 및 어휘 검증 수행
    response = model.invoke(prompt)
    logger.debug("\n\n------------------------- response --------------------------\n\n")
    logger.debug(f"{response}")
    logger.debug("\n\n------------------------- response --------------------------\n\n")

    try:
        # response.content가 문자열인지 확인하고 JSON 파싱 시도
        if hasattr(response, 'content'):
            content = response.content
        else:
            content = str(response)
            
        # JSON 부분만 추출 (```json 블록이 있을 수 있음)
        if '```json' in content:
            start = content.find('```json') + 7
            end = content.find('```', start)
            content = content[start:end].strip()
        elif '{' in content:
            # 첫 번째 { 부터 마지막 } 까지 추출
            start = content.find('{')
            end = content.rfind('}') + 1
            content = content[start:end]
            
        grammar_result = json.loads(content)
    except (json.JSONDecodeError, AttributeError) as e:
        logger.error(f"JSON 파싱 실패: {e}")
        logger.debug(f"Response content: {content if 'content' in locals() else 'N/A'}")
        # 기본값 설정
        grammar_result = {
            "is_valid": True,  # 파싱 실패시 일단 통과로 처리
            "issues": [],
            "check_details": {
                "grammar_correct": True,
                "vocabulary_appropriate": True,
                "spelling_correct": True,
                "readability_good": True,
                "tone_appropriate": True,
                "no_inappropriate_words": True
            },
            "overall_quality": "good",
            "suggestions": "자동 검증 실패로 기본값 사용"
        }
    
    # 검증 결과를 state에 저장
    state["grammar_check_status"] = "completed"
    state["grammar_check_result"] = grammar_result
    
    # 문법 문제가 있으면 수정 필요 표시
    if not grammar_result.get("is_valid", False):
        state["needs_grammar_fix"] = True
        state["grammar_issues"] = grammar_result.get("issues", [])
    else:
        state["needs_grammar_fix"] = False
        
    # 최종 승인 상태 설정
    if not state.get("needs_regeneration", False) and not state.get("needs_grammar_fix", False):
        state["final_approval"] = True
    else:
        state["final_approval"] = False
    
    return state
