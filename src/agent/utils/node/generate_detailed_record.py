from datetime import datetime
from typing import Optional

from langchain_anthropic import ChatAnthropic
from langchain_core.runnables import RunnableConfig
from langchain_openai import ChatOpenAI

from agent.utils.config.config import DEFAULT_MODEL
from agent.utils.dto.types import DetailedRecord
from agent.utils.state.state import StudentState
from src.static.prompt import (
    GENERATE_DETAILED_RECORD_PROMPT,
)


def generate_detailed_record(state: StudentState, config: Optional[RunnableConfig] = None) -> StudentState:
    """세부능력 특기사항을 생성하는 노드
    """
    # 선생님 입력 정보 추출 (없으면 KeyError 발생 → FastAPI에서 처리)
    teacher_input = state["teacher_input"]
    
    # 상태 업데이트
    state["generation_status"] = "in_progress"
    
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
        # 지원하지 않는 모델이면 ValueError 발생 → FastAPI에서 처리
        raise ValueError(f"지원하지 않는 모델입니다: {model_name}")
    
    # 프롬프트 생성
    prompt = GENERATE_DETAILED_RECORD_PROMPT.format(
        name=teacher_input['name'],
        student_number=teacher_input['student_number'],
        subject_name=teacher_input['subject_name'],
        midterm_score=teacher_input['midterm_score'],
        final_score=teacher_input['final_score'],
        additional_notes=teacher_input.get('additional_notes', '없음')
    )
    
    # 세특 생성
    response = model.invoke(prompt)
    generated_content = response.content
    
    # DetailedRecord 생성
    detailed_record = DetailedRecord(
        student_id=teacher_input['student_number'],
        subject=teacher_input['subject_name'],
        content=generated_content,
        generated_at=datetime.now(),
        version=1
    )
    
    # 상태 업데이트
    state["detailed_record"] = detailed_record
    state["generation_status"] = "completed"
    state["error_info"] = None
    
    return state
