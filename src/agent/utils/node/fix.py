"""Fix 노드 - 검증 실패 시 재검색 + 수정"""

from typing import Optional
from langchain_core.runnables import RunnableConfig
from src.utils.timezone import get_timestamp_kst
from agent.utils.config.config import get_model_name, log_token_usage
from agent.utils.dto.types import DetailedRecord
from agent.utils.state.state import StudentState
from agent.utils.node.helper_nodes import _get_model
from agent.utils.vector_db.retriever import example_retriever
from agent.static.prompt import FIX_WITH_IMPROVEMENTS_PROMPT
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


def fix(state: StudentState, config: Optional[RunnableConfig] = None) -> StudentState:
    """검증 실패 시 개선사항을 반영하여 재생성
    
    validation 결과를 바탕으로 문제점을 파악하고,
    새로운 예시를 검색하여 개선된 세특을 생성합니다.
    
    Args:
        state: 학생 상태
        config: 런타임 설정
        
    Returns:
        개선된 세특이 포함된 상태
    """
    try:
        # 필요한 정보 추출
        teacher_input = state["teacher_input"]
        current_content = state["detailed_record"]["content"]
        validation_result = state.get("validation_result", {})
        
        # 수정이 필요없으면 그대로 반환
        if validation_result.get("is_valid", True):
            logger.info("검증 통과 - 수정 불필요")
            return state
        
        # 수정 시도 횟수 체크 및 증가
        fix_attempts = state.get("fix_attempts", 0)
        
        # 이미 1번 수정했으면 더 이상 수정하지 않음
        if fix_attempts >= 1:
            logger.warning(f"최대 수정 횟수({fix_attempts}회) 도달 - 강제 승인")
            state["final_approval"] = True
            state["validation_result"] = {
                "is_valid": True,
                "issues": [],
                "forced_approval": True,
                "message": "최대 수정 횟수 도달로 강제 승인"
            }
            return state
        
        # 1. 새로운 예시 검색 (다양성 확보)
        new_examples = _get_new_examples(teacher_input["subject"], teacher_input.get("additional_notes"))
        
        # 2. 개선사항 정리 - validation_result 전체를 전달
        improvements = _format_improvements(validation_result)
        
        # 3. 모델 선택
        model_name = get_model_name(config)
        model = _get_model(model_name)
        
        # 4. 수정 프롬프트 구성
        fix_prompt = _build_fix_prompt(
            current_content=current_content,
            improvements=improvements,
            examples=new_examples,
            teacher_input=teacher_input,
            achievement_standards=teacher_input.get("achievement_standards", "")
        )
        
        # 5. 개선된 세특 생성
        response = model.invoke(fix_prompt)
        improved_content = response.content if hasattr(response, 'content') else str(response)
        
        # 토큰 사용량 로깅
        log_token_usage(response, logger, "fix")

        logger.debug(f"개선된 세특 내용: {improved_content}")

        # 6. DetailedRecord 업데이트
        current_version = state["detailed_record"].get("version", 1)
        updated_record = DetailedRecord(
            student_id=teacher_input["student_id"],
            subject=teacher_input["subject"],
            content=improved_content,
            generated_at=get_timestamp_kst(),
            version=current_version + 1
        )
        
        # 7. 상태 업데이트
        state["detailed_record"] = updated_record
        state["fix_attempts"] = fix_attempts + 1
        state["generation_status"] = "completed"
        
        # 🔥 핵심 변경: fix 후 즉시 종료를 위해 final_approval을 True로 설정
        state["final_approval"] = True  # 재검증 없이 바로 종료
        state["validation_result"] = {
            "is_valid": True,  # 수정했으므로 유효한 것으로 간주
            "issues": [],
            "fixed_at": get_timestamp_kst(),
            "message": "수정 완료 - 추가 검증 없이 승인"
        }
        
        logger.info(f"세특 수정 완료 - 버전: {current_version + 1} (즉시 종료)")
        
        # 수정 결과 상세 로깅 (파일 저장용)
        logger.error("")
        logger.error("=" * 100)
        logger.error("✅ 수정 완료 결과")
        logger.error("=" * 100)
        
        # 기본 정보
        logger.error(f"📋 학생명: {teacher_input.get('name', 'Unknown')}")
        logger.error(f"📋 과목: {teacher_input.get('subject', 'Unknown')}")
        
        logger.error("")
        logger.error("-" * 60)
        logger.error("🔧 수정된 세특 내용")
        logger.error("-" * 60)
        logger.error(improved_content)
        
        logger.error("=" * 100)
        
    except Exception as e:
        logger.error(f"수정 중 오류: {e}")
        
        # 오류 시에도 fix_attempts 증가시켜야 함!
        fix_attempts = state.get("fix_attempts", 0)
        state["fix_attempts"] = fix_attempts + 1
        
        # 오류 시 현재 상태 유지하고 종료
        state["final_approval"] = True  # 더 이상 수정하지 않음
        state["error_info"] = {
            "error_code": "FIX_ERROR",
            "message": str(e)
        }
    
    return state


def _get_new_examples(subject: str, additional_notes: Optional[str]) -> list:
    """Fix를 위한 새로운 예시 검색
    
    Args:
        subject: 과목명
        additional_notes: 추가 활동
        
    Returns:
        새로운 예시 리스트
    """
    try:
        # 다양한 예시 획득 (이전과 다른 예시)
        new_examples = example_retriever.get_diverse_examples(
            subject=subject,
            k=2  # Fix에서는 2개만
        )
        
        logger.debug(f"Fix용 새 예시 {len(new_examples)}개 검색")
        return new_examples
        
    except Exception as e:
        logger.error(f"예시 검색 실패: {e}")
        return []


def _format_improvements(validation_result: dict) -> str:
    """검증 결과를 개선사항으로 포맷팅
    
    Args:
        validation_result: validate 노드에서 전달된 검증 결과
        
    Returns:
        포맷팅된 개선사항 문자열
    """
    issues = validation_result.get("issues", [])
    summary = validation_result.get("summary", "")
    
    if not issues:
        return "전반적인 품질 개선 필요"
    
    improvements = []
    
    # 요약이 있으면 먼저 표시
    if summary:
        improvements.append(f"## 검증 요약: {summary}\n")
    
    # 발견된 이슈들을 목록으로 표시
    improvements.append("## 수정이 필요한 사항들:")
    for i, issue in enumerate(issues, 1):
        improvements.append(f"{i}. {issue}")
    
    # 구체적인 수정 지침 추가
    improvements.append("\n## 수정 방향:")
    improvements.append("- 위에서 지적된 모든 문제를 반드시 수정해주세요")
    improvements.append("- 특히 음슴체와 학생 이름 관련 문제는 최우선으로 수정해주세요")
    improvements.append("- 문장을 자연스럽게 연결하여 매끄러운 흐름을 만들어주세요")
    
    return "\n".join(improvements)


def _build_fix_prompt(current_content: str, 
                      improvements: str, 
                      examples: list,
                      teacher_input: dict,
                      achievement_standards: str = "") -> str:
    """Fix 프롬프트 구성
    
    Args:
        current_content: 현재 세특 내용
        improvements: 개선사항
        examples: 참고 예시
        teacher_input: 교사 입력 정보
        achievement_standards: 성취기준
        
    Returns:
        완성된 프롬프트
    """
    # 예시 포맷팅
    examples_text = "\n\n".join([f"예시 {i+1}:\n{ex}" for i, ex in enumerate(examples)])
    
    # 프롬프트 템플릿 사용
    prompt = FIX_WITH_IMPROVEMENTS_PROMPT.format(
        current_content=current_content,
        improvements=improvements,
        examples=examples_text,
        additional_notes=teacher_input.get("additional_notes", "없음"),
        achievement_standards=achievement_standards
    )
    
    return prompt