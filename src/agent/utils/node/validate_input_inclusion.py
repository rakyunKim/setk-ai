import json
from typing import Optional

from langchain_anthropic import ChatAnthropic
from langchain_core.runnables import RunnableConfig
from langchain_openai import ChatOpenAI

from agent.utils.config.config import DEFAULT_MODEL
from agent.utils.state.state import StudentState
from src.static.prompt import (
    VALIDATE_INPUT_PROMPT,
)


def validate_input_inclusion(state: StudentState, config: Optional[RunnableConfig] = None) -> StudentState:
    """생성된 세특에 선생님이 입력한 정보가 모두 포함되어 있는지 검증하는 노드
    """
    # 필요한 정보 추출 (없으면 KeyError 발생 → FastAPI에서 처리)
    teacher_input = state["teacher_input"]
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
        raise ValueError(f"지원하지 않는 모델입니다: {model_name}")
    
    # 검증 프롬프트 생성
    prompt = VALIDATE_INPUT_PROMPT.format(
        name=teacher_input['name'],
        student_number=teacher_input['student_id'],
        subject_name=teacher_input['subject'],
        midterm_score=teacher_input['midterm_score'],
        final_score=teacher_input['final_score'],
        additional_notes=teacher_input.get('additional_notes', '없음'),
        generated_content=detailed_record['content']
    )
    
    # 검증 수행
    response = model.invoke(prompt)
    validation_result = json.loads(response.content)
    
    # 검증 결과를 state에 저장
    state["validation_status"] = "completed"
    state["validation_result"] = validation_result
    
    # 검증 실패 시 재생성 필요 표시
    if not validation_result.get("is_valid", False):
        state["needs_regeneration"] = True
        state["regeneration_reason"] = "missing_info"
        state["missing_items"] = validation_result.get("missing_items", [])
    else:
        state["needs_regeneration"] = False
    
    return state

