from __future__ import annotations

from langgraph.graph import END, StateGraph

from agent.utils.config.config import CustomConfig
from agent.utils.node.check_grammer import check_grammar_and_vocabulary
from agent.utils.node.clear import clear_and_prepare_regeneration
from agent.utils.node.fix_grammer import fix_grammar_and_regenerate
from agent.utils.node.generate_detailed_record import generate_detailed_record
from agent.utils.node.validate_input_inclusion import validate_input_inclusion
from agent.utils.state.state import StudentState


# 조건부 라우팅 함수들
def should_regenerate_for_missing_info(state: StudentState) -> str:
    """입력 정보 검증 후 라우팅 결정"""
    # validation_result가 있고 is_valid가 False면 재생성 필요
    validation_result = state.get("validation_result", {})
    if not validation_result.get("is_valid", True):
        return "clear_for_regeneration"
    return "check_grammar"


def should_fix_grammar(state: StudentState) -> str:
    """문법 검증 후 라우팅 결정"""
    # 최종 승인되면 종료
    if state.get("final_approval", False):
        return "end"
    # grammar_result가 있고 is_valid가 False면 문법 수정 필요
    grammar_result = state.get("grammar_result", {})
    if not grammar_result.get("is_valid", True):
        return "fix_grammar"
    # 그 외의 경우도 종료
    return "end"



# LangGraph Server용 워크플로우 정의
workflow = StateGraph(StudentState, config_schema=CustomConfig)

# 노드 추가
workflow.add_node("generate", generate_detailed_record)
workflow.add_node("validate_input", validate_input_inclusion)
workflow.add_node("clear_for_regeneration", clear_and_prepare_regeneration)
workflow.add_node("check_grammar", check_grammar_and_vocabulary)
workflow.add_node("fix_grammar", fix_grammar_and_regenerate)

# 엣지 정의
# 시작 → 생성
workflow.add_edge("__start__", "generate")

# 생성 → 입력 검증
workflow.add_edge("generate", "validate_input")

# 입력 검증 → 조건부 라우팅
workflow.add_conditional_edges(
    "validate_input",
    should_regenerate_for_missing_info,
    {
        "clear_for_regeneration": "clear_for_regeneration",
        "check_grammar": "check_grammar"
    }
)

# 정보 삭제 → 다시 생성
workflow.add_edge("clear_for_regeneration", "generate")

# 문법 검증 → 조건부 라우팅
workflow.add_conditional_edges(
    "check_grammar",
    should_fix_grammar,
    {
        "fix_grammar": "fix_grammar",
        "end": END
    }
)

# 문법 수정 → 다시 문법 검증
workflow.add_edge("fix_grammar", "check_grammar")

# 그래프 컴파일
graph = workflow.compile(name="세부능력 특기사항 생성 워크플로우")
