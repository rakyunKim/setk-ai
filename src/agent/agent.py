"""RAG 기반 세부능력 특기사항 생성 워크플로우"""

from __future__ import annotations

from langgraph.graph import END, StateGraph

from agent.utils.config.config import CustomConfig
from agent.utils.node.prepare_examples import prepare_examples
from agent.utils.node.generate import generate
from agent.utils.node.validate import validate
from agent.utils.node.fix import fix
from agent.utils.state.state import StudentState


# 조건부 라우팅 함수
def should_fix_or_end(state: StudentState) -> str:
    """검증 후 라우팅 결정 - 수정 필요 여부 판단"""
    
    # 최종 승인되면 종료
    if state.get("final_approval", False):
        return "end"
    
    # fix 시도 횟수 확인 - 1번 이상이면 무조건 종료
    fix_attempts = state.get("fix_attempts", 0)
    if fix_attempts >= 1:
        return "end"
    
    # 검증 결과 확인
    validation_result = state.get("validation_result", {})
    
    # is_valid가 False면 수정 필요
    if not validation_result.get("is_valid", True):
        return "fix"
    
    # 그 외의 경우 종료
    return "end"


# LangGraph 워크플로우 정의
workflow = StateGraph(StudentState, config_schema=CustomConfig)

# 노드 추가 (새로운 3노드 시스템 + prepare)
workflow.add_node("prepare", prepare_examples)    # RAG 검색
workflow.add_node("generate", generate)           # 생성
workflow.add_node("validate", validate)           # 통합 검증
workflow.add_node("fix", fix)                    # 수정

# 엣지 정의
# 시작 → prepare (RAG 검색부터)
workflow.add_edge("__start__", "prepare")

# prepare → generate (검색된 예시로 생성)
workflow.add_edge("prepare", "generate")

# generate → validate (검증)
workflow.add_edge("generate", "validate")

# validate → 조건부 라우팅 (수정 또는 종료)
workflow.add_conditional_edges(
    "validate",
    should_fix_or_end,
    {
        "fix": "fix",
        "end": END
    }
)

# fix → validate (수정 후 재검증)
workflow.add_edge("fix", "validate")

# 그래프 컴파일
graph = workflow.compile(
    name="RAG 기반 세부능력 특기사항 생성 워크플로우",
    # 디버깅을 위한 설정
    debug=False,
)