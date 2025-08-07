
from typing import Optional

from langchain_core.runnables import RunnableConfig

from agent.utils.state.state import StudentState


def clear_and_prepare_regeneration(state: StudentState, config: Optional[RunnableConfig] = None) -> StudentState:
    """검증 실패 시 기존 세특을 삭제하고 재생성을 위한 상태로 초기화하는 노드
    """
    # 검증 결과 확인
    needs_regeneration = state.get("needs_regeneration", False)
    
    if not needs_regeneration:
        # 재생성이 필요없으면 그대로 반환
        return state
    
    # 기존 세특 삭제
    state["detailed_record"] = None
    
    # 생성 상태를 pending으로 변경 (다시 generate_detailed_record를 호출할 준비)
    state["generation_status"] = "pending"
    
    # 에러 정보 초기화
    state["error_info"] = None
    
    # 재생성 시도 횟수 추적 (무한 루프 방지용)
    if "regeneration_attempts" not in state:
        state["regeneration_attempts"] = 0
    state["regeneration_attempts"] += 1
    
    # 최대 3번까지만 재생성 시도
    if state["regeneration_attempts"] > 3:
        raise Exception(
            error_code="429",
            message="재생성 시도 횟수를 초과했습니다. (최대 3회)"
        )
    
    return state