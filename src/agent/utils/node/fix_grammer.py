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
    grammar_issues = state.get("grammar_issues", [])
    needs_grammar_fix = state.get("needs_grammar_fix", False)
    
    if not needs_grammar_fix:
        # 문법 수정이 필요없으면 그대로 반환
        return state
    
    # KeyError 발생하면 FastAPI에서 처리
    detailed_record = state["detailed_record"]
    
    # 현재 content 저장
    current_content = detailed_record.get('content', '')
    
    # 문법 수정 시도 횟수 추적
    if "grammar_fix_attempts" not in state:
        state["grammar_fix_attempts"] = 0
    state["grammar_fix_attempts"] += 1
    
    # 최대 3번까지만 수정 시도
    if state["grammar_fix_attempts"] > 3:
        # 3번 시도해도 문법 문제가 해결되지 않으면 현재 상태로 승인
        state["needs_grammar_fix"] = False
        state["final_approval"] = True
        state["grammar_fix_note"] = "문법 수정 시도 횟수 초과. 현재 상태로 승인."
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
        generated_at=datetime.now(),
        version=current_version + 1
    )
    
    # 상태 업데이트
    state["detailed_record"] = updated_record
    state["generation_status"] = "grammar_fixed"
    state["needs_grammar_fix"] = False  # 일단 수정 완료로 표시
    state["grammar_check_status"] = "pending"  # 다시 검증 필요
    
    # 수정 기록 저장
    if "grammar_fix_history" not in state:
        state["grammar_fix_history"] = []
    state["grammar_fix_history"].append({
        "attempt": state["grammar_fix_attempts"],
        "previous_content": current_content,
        "fixed_at": datetime.now().isoformat(),
        "issues_fixed": len(grammar_issues)
    })
        
    return state