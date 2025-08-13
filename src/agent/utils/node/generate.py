"""RAG 기반 세부능력 특기사항 생성 노드"""

from typing import Optional
from langchain_core.runnables import RunnableConfig
from agent.utils.config.config import get_model_name, log_token_usage
from src.utils.timezone import get_timestamp_kst
from agent.utils.dto.types import DetailedRecord
from agent.utils.state.state import StudentState
from agent.utils.node.helper_nodes import _get_model
from src.utils.logger import setup_logger
from agent.static.prompt import GENERATE_WITH_EXAMPLES_PROMPT

logger = setup_logger(__name__)


def generate(state: StudentState, config: Optional[RunnableConfig] = None) -> StudentState:
    """RAG 검색된 예시를 활용하여 세부능력 특기사항 생성
    
    prepare_examples 노드에서 검색한 예시를 활용하여
    고품질의 세특을 생성합니다.
    
    Args:
        state: 학생 상태 (retrieved_examples 포함)
        config: 런타임 설정
        
    Returns:
        세특이 생성된 상태
    """
    try:
        # 1. 필요한 정보 추출
        teacher_input = state["teacher_input"]
        retrieved_examples = state.get("retrieved_examples", [])
        
        # 상태 업데이트
        state["generation_status"] = "in_progress"
        
        logger.info(f"세특 생성 시작 - 학생: {teacher_input['name']}, 과목: {teacher_input['subject']}")
        logger.info(f"검색된 예시 {len(retrieved_examples)}개 활용")
        
        # 2. 모델 선택
        model_name = get_model_name(config)
        model = _get_model(model_name)
        
        # 3. 프롬프트 구성 (Few-shot with RAG examples)
        prompt = _build_generation_prompt(teacher_input, retrieved_examples)
        
        # 4. 세특 생성
        response = model.invoke(prompt)
        generated_content = response.content if hasattr(response, 'content') else str(response)
        
        # 토큰 사용량 로깅
        log_token_usage(response, logger, "generate")
        
        logger.debug(f"생성된 세특 길이: {len(generated_content)}자")
        
        # 5. DetailedRecord 생성
        detailed_record = DetailedRecord(
            student_id=teacher_input['student_id'],
            subject=teacher_input['subject'],
            content=generated_content,
            generated_at=get_timestamp_kst(),
            version=1
        )
        
        # 6. 상태 업데이트
        state["detailed_record"] = detailed_record
        state["generation_status"] = "completed"
        state["error_info"] = None
        
        logger.info("세특 생성 완료")
        
    except Exception as e:
        logger.error(f"세특 생성 중 오류: {e}")
        
        state["generation_status"] = "failed"
        state["error_info"] = {
            "error_code": "GENERATION_ERROR",
            "message": str(e)
        }
    
    return state


def _build_generation_prompt(teacher_input: dict, retrieved_examples: list) -> str:
    """Few-shot 프롬프트 구성
    
    Args:
        teacher_input: 교사 입력 정보
        retrieved_examples: RAG로 검색된 예시들
        semester: 학기 (1 또는 2)
        
    Returns:
        완성된 프롬프트
    """
    # 예시 섹션 포맷팅
    if retrieved_examples:
        examples_section = "## 우수 세특 예시 (참고용)\n"
        for i, example in enumerate(retrieved_examples, 1):
            examples_section += f"\n### 예시 {i}\n{example}\n"
    else:
        # 예시가 없으면 기본 가이드라인만
        examples_section = "## 작성 가이드라인\n- 구체적인 활동과 탐구 과정 포함\n- 학생의 자발적 관심과 노력 강조\n- 성과와 결과물 명시\n"
    
    prompt = GENERATE_WITH_EXAMPLES_PROMPT.format(
        examples_section=examples_section,
        subject=teacher_input['subject'],
        midterm_score=teacher_input['midterm_score'],
        final_score=teacher_input['final_score'],
        additional_notes=teacher_input.get('additional_notes', '없음'),
        achievement_standards=teacher_input.get('achievement_standards', ''),
    )
    
    return prompt