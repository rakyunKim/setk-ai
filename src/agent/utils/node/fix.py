"""Fix 노드 - 검증 실패 시 재검색 + 수정"""

from typing import Optional
from langchain_core.runnables import RunnableConfig
from src.utils.timezone import get_timestamp_kst
from agent.utils.config.config import DEFAULT_MODEL
from agent.utils.dto.types import DetailedRecord
from agent.utils.state.state import StudentState
from agent.utils.node.helper_nodes import _get_model
from agent.utils.vector_db.retriever import example_retriever
from src.static.prompt import FIX_WITH_IMPROVEMENTS_PROMPT
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
        issues = validation_result.get("issues", [])
        
        # 수정이 필요없으면 그대로 반환
        if validation_result.get("is_valid", True):
            logger.info("검증 통과 - 수정 불필요")
            return state
        
        logger.info(f"세특 수정 시작 - 이슈: {len(issues)}개")
        
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
        
        # 2. 개선사항 정리 (AI 검증 결과 활용)
        detailed_issues = validation_result.get("detailed_issues", [])
        if detailed_issues:
            # AI 검증의 구체적 이슈 사용
            improvements = []
            for issue in detailed_issues:
                if isinstance(issue, dict):
                    improvements.append(f"- {issue.get('description', '')}")
                    if issue.get('problematic_text'):
                        improvements.append(f"  문제 텍스트: '{issue['problematic_text']}'")
                    if issue.get('suggestion'):
                        improvements.append(f"  수정 방법: {issue['suggestion']}")
            improvements = "\n".join(improvements)
        else:
            # 기존 이슈 사용
            improvements = _format_improvements(issues)
        
        # 3. 모델 선택
        model_name = DEFAULT_MODEL
        if config and hasattr(config, 'configurable'):
            model_name = config.configurable.get("model_name", DEFAULT_MODEL)
        model = _get_model(model_name)
        
        # 4. 수정 프롬프트 구성
        fix_prompt = _build_fix_prompt(
            current_content=current_content,
            improvements=improvements,
            examples=new_examples,
            teacher_input=teacher_input
        )
        
        # 5. 개선된 세특 생성
        response = model.invoke(fix_prompt)
        improved_content = response.content if hasattr(response, 'content') else str(response)
        
        logger.debug(f"개선된 세특 길이: {len(improved_content)}자")
        
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
        state["generation_status"] = "fixed"
        
        # validation_result 초기화 (재검증 필요)
        state["validation_result"] = {
            "is_valid": False,  # 재검증 필요
            "issues": [],
            "fixed_at": get_timestamp_kst()
        }
        
        logger.info(f"세특 수정 완료 - 버전: {current_version + 1}")
        
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


def _format_improvements(issues: list) -> str:
    """개선사항을 읽기 쉬운 형태로 포맷팅
    
    Args:
        issues: 검증에서 발견된 이슈 리스트
        
    Returns:
        포맷팅된 개선사항 문자열
    """
    if not issues:
        return "전반적인 품질 개선 필요"
    
    # 이슈를 카테고리별로 분류
    info_issues = []
    quality_issues = []
    other_issues = []
    
    for issue in issues:
        if "누락" in issue or "점수" in issue:
            info_issues.append(issue)
        elif "활동" in issue or "표현" in issue:
            quality_issues.append(issue)
        else:
            other_issues.append(issue)
    
    improvements = []
    
    if info_issues:
        improvements.append("### 필수 정보 포함")
        improvements.extend([f"- {issue}" for issue in info_issues])
    
    if quality_issues:
        improvements.append("\n### 품질 개선")
        improvements.extend([f"- {issue}" for issue in quality_issues])
    
    if other_issues:
        improvements.append("\n### 기타 수정사항")
        improvements.extend([f"- {issue}" for issue in other_issues])
    
    return "\n".join(improvements)


def _build_fix_prompt(current_content: str, 
                      improvements: str, 
                      examples: list,
                      teacher_input: dict) -> str:
    """Fix 프롬프트 구성
    
    Args:
        current_content: 현재 세특 내용
        improvements: 개선사항
        examples: 참고 예시
        teacher_input: 교사 입력 정보
        
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
        name=teacher_input["name"],
        subject=teacher_input["subject"],
        midterm_score=teacher_input["midterm_score"],
        final_score=teacher_input["final_score"],
        additional_notes=teacher_input.get("additional_notes", "없음")
    )
    
    return prompt


def simple_fix(state: StudentState, config: Optional[RunnableConfig] = None) -> StudentState:
    """간단한 수정 (정보 누락만 처리)
    
    필수 정보가 누락된 경우만 빠르게 수정
    
    Args:
        state: 학생 상태
        config: 런타임 설정
        
    Returns:
        수정된 상태
    """
    teacher_input = state["teacher_input"]
    current_content = state["detailed_record"]["content"]
    
    # 누락된 정보 추가
    if teacher_input["name"] not in current_content:
        current_content = f"{teacher_input['name']} 학생은 " + current_content
    
    if str(teacher_input["midterm_score"]) not in current_content:
        current_content = current_content.replace(
            "수행평가", 
            f"중간 수행평가 {teacher_input['midterm_score']}점, 기말 수행평가"
        )
    
    if str(teacher_input["final_score"]) not in current_content:
        current_content = current_content.replace(
            "기말 수행평가", 
            f"기말 수행평가 {teacher_input['final_score']}점"
        )
    
    # 업데이트
    state["detailed_record"]["content"] = current_content
    state["detailed_record"]["version"] = state["detailed_record"].get("version", 1) + 1
    
    return state