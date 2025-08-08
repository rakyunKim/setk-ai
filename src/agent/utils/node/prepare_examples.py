"""RAG 검색을 수행하는 Prepare 노드"""

from typing import Optional
from langchain_core.runnables import RunnableConfig
from agent.utils.state.state import StudentState
from agent.utils.vector_db.retriever import example_retriever
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


def prepare_examples(state: StudentState, config: Optional[RunnableConfig] = None) -> StudentState:
    """워크플로우 시작 시 관련 예시를 검색하여 state에 저장
    
    이 노드는 generate 노드 전에 실행되어 관련 예시를 미리 준비합니다.
    검색된 예시는 state["retrieved_examples"]에 저장되어 
    이후 generate, fix 노드에서 활용됩니다.
    
    Args:
        state: 학생 상태
        config: 런타임 설정
        
    Returns:
        예시가 추가된 상태
    """
    try:
        # 1. 필요한 정보 추출
        teacher_input = state["teacher_input"]
        subject = teacher_input["subject"]
        additional_notes = teacher_input.get("additional_notes", "")
        
        # 2. 사용자가 제공한 커스텀 예시 (있는 경우)
        custom_examples = state.get("custom_examples", None)
        
        logger.info(f"예시 검색 시작 - 과목: {subject}")
        
        # 3. RAG 검색 수행
        retrieved_examples = example_retriever.search_examples(
            subject=subject,
            additional_notes=additional_notes,
            custom_examples=custom_examples,
            k=3  # 기본 3개 검색
        )
        
        # 4. 검색 결과를 state에 저장
        state["retrieved_examples"] = retrieved_examples
        
        # 5. 검색 쿼리도 저장 (디버깅/분석용)
        search_query = f"과목: {subject}"
        if additional_notes and additional_notes not in ["없음", ".", "-", ""]:
            search_query += f", 활동: {additional_notes}"
        state["search_query"] = search_query
        
        # 6. 검색 통계 저장
        state["search_metadata"] = {
            "num_examples": len(retrieved_examples),
            "subject": subject,
            "has_additional_notes": bool(additional_notes and additional_notes != "없음"),
            "has_custom_examples": bool(custom_examples)
        }
        
        logger.info(f"예시 검색 완료 - {len(retrieved_examples)}개 예시 검색됨")
        
        # 디버그: 검색된 예시 일부 출력
        if retrieved_examples:
            logger.debug(f"첫 번째 예시 (50자): {retrieved_examples[0][:50]}...")
        
    except Exception as e:
        logger.error(f"예시 검색 중 오류 발생: {e}")
        
        # 오류 발생 시 빈 리스트 설정
        state["retrieved_examples"] = []
        state["search_query"] = ""
        state["search_metadata"] = {
            "num_examples": 0,
            "error": str(e)
        }
        
        # 에러 정보 저장
        if "error_info" not in state:
            state["error_info"] = {}
        state["error_info"]["prepare_error"] = str(e)
    
    return state


def prepare_examples_for_fix(state: StudentState, config: Optional[RunnableConfig] = None) -> StudentState:
    """Fix 노드를 위한 다른 예시 검색
    
    Fix 노드에서 사용할 새로운 예시를 검색합니다.
    이전에 사용한 예시와 다른 예시를 가져오기 위해 
    다양성을 고려한 검색을 수행합니다.
    
    Args:
        state: 학생 상태
        config: 런타임 설정
        
    Returns:
        새로운 예시가 추가된 상태
    """
    try:
        teacher_input = state["teacher_input"]
        subject = teacher_input["subject"]
        
        logger.info(f"Fix를 위한 새로운 예시 검색 - 과목: {subject}")
        
        # 다양한 예시 획득 (중복 방지)
        new_examples = example_retriever.get_diverse_examples(
            subject=subject,
            k=2  # Fix에서는 2개만
        )
        
        # Fix용 예시를 별도 필드에 저장
        state["fix_examples"] = new_examples
        
        logger.info(f"Fix용 예시 검색 완료 - {len(new_examples)}개")
        
    except Exception as e:
        logger.error(f"Fix 예시 검색 중 오류: {e}")
        state["fix_examples"] = []
    
    return state