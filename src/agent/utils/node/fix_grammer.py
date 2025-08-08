from datetime import datetime
from typing import Optional

from langchain_core.runnables import RunnableConfig

from agent.utils.config.config import DEFAULT_MODEL
from agent.utils.dto.types import DetailedRecord
from agent.utils.node.helper_nodes import _get_model
from agent.utils.state.state import StudentState
from src.static.prompt import FIX_GRAMMAR_PROMPT


def fix_grammar_and_regenerate(state: StudentState, config: Optional[RunnableConfig] = None) -> StudentState:
    """문법 문제를 수정하여 세특을 재생성하는 노드
    """
    # 필요한 정보 추출
    detailed_record = state.get("detailed_record")
    grammar_result = state.get("grammar_result", {})
    grammar_issues = grammar_result.get("issues", [])
    
    # 문법 수정이 필요없으면 그대로 반환
    if grammar_result.get("is_valid", True):
        return state
    
    # KeyError 발생하면 FastAPI에서 처리
    detailed_record = state["detailed_record"]
    
    # 현재 content 저장
    current_content = detailed_record.get('content', '')
    
    # 문법 수정 시도 횟수 추적 (임시 변수 사용)
    fix_attempts = state.get("_grammar_fix_attempts", 0) + 1
    state["_grammar_fix_attempts"] = fix_attempts
    
    # 최대 3번까지만 수정 시도
    if fix_attempts > 3:
        # 3번 시도해도 문법 문제가 해결되지 않으면 현재 상태로 승인
        state["final_approval"] = True
        state["grammar_result"]["details"]["max_attempts_reached"] = True
        return state
    
    # 모델 선택
    model_name = DEFAULT_MODEL
    if config and hasattr(config, 'configurable'):
        model_name = config.configurable.get("model_name", DEFAULT_MODEL)
    model = _get_model(model_name)
    
    # 문법 문제 포맷팅
    issues_text = "\n".join([
        f"- {issue.get('type', '문제')}: {issue.get('text', '')} → {issue.get('suggestion', '수정 필요')}"
        for issue in grammar_issues
    ])
    
    # 문법 수정 프롬프트 생성
    prompt = FIX_GRAMMAR_PROMPT.format(
        current_content=current_content,
        grammar_issues=issues_text if issues_text else "문법 및 어휘 개선 필요"
    )
    
    # 문법 수정된 세특 생성
    response = model.invoke(prompt)
    fixed_content = response.content
    
    # DetailedRecord 업데이트 (version 증가)
    current_version = detailed_record.get('version', 1)
    updated_record = DetailedRecord(
        student_id=detailed_record['student_id'],
        subject=detailed_record['subject'],
        content=fixed_content,
        generated_at=datetime.now().isoformat(),  # ISO format string으로 저장
        version=current_version + 1
    )
    
    # 상태 업데이트
    state["detailed_record"] = updated_record
    state["generation_status"] = "completed"
    
    # grammar_result 업데이트 (수정 완료 상태로)
    state["grammar_result"] = {
        "status": "fixed",  # 수정됨 표시
        "is_valid": False,  # 재검증 필요
        "issues": [],  # 수정 후 재검증 필요
        "details": {"fixed_at": datetime.now().isoformat()}
    }
        
    return state