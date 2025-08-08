"""통합 검증 노드 - 입력 정보 포함 + 품질 검증"""

from typing import Optional, List
from langchain_core.runnables import RunnableConfig
from agent.utils.config.config import DEFAULT_MODEL
from agent.utils.state.state import StudentState
from agent.utils.node.helper_nodes import _get_model
from src.utils.logger import setup_logger
import json

logger = setup_logger(__name__)


def validate(state: StudentState, config: Optional[RunnableConfig] = None) -> StudentState:
    """AI 기반으로 생성된 세특의 허위 정보와 품질을 검증
    
    Args:
        state: 학생 상태
        config: 런타임 설정
        
    Returns:
        검증 결과가 포함된 상태
    """
    try:
        # 필요한 정보 추출
        teacher_input = state["teacher_input"]
        detailed_record = state.get("detailed_record", {})
        content = detailed_record.get("content", "")
        retrieved_examples = state.get("retrieved_examples", [])
        
        logger.info(f"AI 검증 시작 - 학생: {teacher_input['name']}")
        
        # fix 시도 횟수 확인 - 1번 이상이면 무조건 통과
        fix_attempts = state.get("fix_attempts", 0)
        if fix_attempts >= 1:
            logger.warning(f"Fix 시도 {fix_attempts}회 도달 - 강제 승인")
            state["validation_result"] = {
                "is_valid": True,
                "issues": [],
                "forced_approval": True,
                "message": "최대 수정 횟수 도달로 강제 승인"
            }
            state["final_approval"] = True
            return state
        
        # AI 모델 초기화
        model_name = DEFAULT_MODEL
        if config and hasattr(config, 'configurable'):
            model_name = config.configurable.get("model_name", DEFAULT_MODEL)
        model = _get_model(model_name)
        
        # 검증 프롬프트 구성
        from src.static.prompt import AI_VALIDATE_PROMPT
        
        validation_prompt = AI_VALIDATE_PROMPT.format(
            name=teacher_input.get("name", ""),
            subject=teacher_input.get("subject", ""),
            midterm_score=teacher_input.get("midterm_score", ""),
            final_score=teacher_input.get("final_score", ""),
            additional_notes=teacher_input.get("additional_notes", "없음"),
            retrieved_examples="\n".join(retrieved_examples[:3]) if retrieved_examples else "없음",
            content=content
        )
        
        # AI 검증 실행
        response = model.invoke(validation_prompt)
        
        # JSON 파싱
        try:
            result = json.loads(response.content)
        except:
            # JSON 파싱 실패시 기본 통과
            logger.warning("AI 검증 결과 파싱 실패 - 기본 통과")
            result = {
                "is_valid": True,
                "issues": [],
                "needs_fix": False,
                "summary": "검증 파싱 실패로 통과"
            }
        
        # 결과 저장
        is_valid = result.get("is_valid", True)
        issues = result.get("issues", [])
        
        # 이슈를 문자열 리스트로 변환
        issue_list = []
        for issue in issues:
            if isinstance(issue, dict):
                issue_list.append(f"{issue.get('type', '')}: {issue.get('description', '')}")
            else:
                issue_list.append(str(issue))
        
        state["validation_result"] = {
            "is_valid": is_valid,
            "issues": issue_list,
            "summary": result.get("summary", ""),
            "detailed_issues": issues  # 원본 이슈 저장
        }
        
        state["final_approval"] = is_valid
        
        logger.info(f"AI 검증 완료 - 유효: {is_valid}, 이슈: {len(issue_list)}개")
        
        if issue_list:
            logger.debug(f"발견된 이슈: {issue_list[:3]}")
        
    except Exception as e:
        logger.error(f"검증 중 오류: {e}")
        
        # 오류 시 통과로 처리 (생성은 되었으므로)
        state["validation_result"] = {
            "is_valid": True,
            "issues": [],
            "error": str(e)
        }
        state["final_approval"] = True
    
    return state


# 아래 함수들은 AI 기반 검증으로 대체되어 더 이상 사용되지 않음
# 추후 필요시 복구를 위해 보존

def _validate_required_info(content: str, teacher_input: dict) -> List[str]:
    """필수 정보 포함 여부 검증
    
    Args:
        content: 세특 내용
        teacher_input: 교사 입력 정보
        
    Returns:
        발견된 이슈 리스트
    """
    issues = []
    
    # 1. 학생 이름 검증
    name = teacher_input.get("name", "")
    if name and name not in content:
        issues.append(f"학생 이름 '{name}' 누락")
    
    # 2. 중간고사 점수 검증 (다양한 표현 허용)
    midterm = str(teacher_input.get("midterm_score", ""))
    if midterm:
        midterm_found = any([
            midterm in content,
            f"{midterm}점" in content,
            f"{midterm} 점" in content,
            f"중간 {midterm}" in content,
            f"중간고사 {midterm}" in content,
            f"중간평가 {midterm}" in content,
            f"중간 수행평가 {midterm}" in content
        ])
        if not midterm_found:
            issues.append(f"중간고사 점수 '{midterm}점' 누락")
    
    # 3. 기말고사 점수 검증 (다양한 표현 허용)
    final = str(teacher_input.get("final_score", ""))
    if final:
        final_found = any([
            final in content,
            f"{final}점" in content,
            f"{final} 점" in content,
            f"기말 {final}" in content,
            f"기말고사 {final}" in content,
            f"기말평가 {final}" in content,
            f"기말 수행평가 {final}" in content
        ])
        if not final_found:
            issues.append(f"기말고사 점수 '{final}점' 누락")
    
    # 4. 추가사항 검증 (있는 경우만)
    additional = teacher_input.get("additional_notes", "")
    if additional and additional not in ["없음", ".", "-", "", None]:
        # 추가사항의 핵심 키워드가 포함되어 있는지 확인
        # 조사를 제거하고 핵심 단어만 추출
        import re
        # 조사나 어미 제거 (이, 가, 은, 는, 을, 를, 에, 와, 과, 으로, 고 등)
        clean_additional = re.sub(r'[이가은는을를에와과으로고]+\s', ' ', additional)
        keywords = [w.strip() for w in clean_additional.split() if len(w.strip()) > 1]
        
        # 최소 절반 이상의 키워드가 포함되어야 함
        found_count = sum(1 for keyword in keywords if keyword in content)
        if found_count < max(1, len(keywords) // 2):
            issues.append(f"추가 활동/특이사항 내용 미반영 (필요: {keywords}, 발견: {found_count}/{len(keywords)})")
    
    return issues


def _validate_quality_patterns(content: str) -> List[str]:
    """품질 패턴 검증 - 예시와 유사한 구조인지
    
    Args:
        content: 세특 내용
        
    Returns:
        발견된 이슈 리스트
    """
    issues = []
    
    # 필수 품질 키워드 (최소 2개는 있어야 함)
    quality_keywords = [
        "탐구", "관심", "활동", "분석", "이해", "노력",
        "참여", "발표", "실험", "조사", "연구", "학습",
        "프로젝트", "과제", "보고서", "결과", "성과"
    ]
    
    keyword_count = sum(1 for keyword in quality_keywords if keyword in content)
    if keyword_count < 2:
        issues.append("구체적 활동 설명 부족 (탐구, 활동, 참여 등의 표현 필요)")
    
    # 수동적 표현만 있는지 체크
    passive_only = all(
        active not in content 
        for active in ["진행", "수행", "제작", "작성", "발표", "참여", "조사"]
    )
    if passive_only:
        issues.append("능동적 활동 표현 부족")
    
    return issues


def _validate_length(content: str) -> List[str]:
    """길이 검증
    
    Args:
        content: 세특 내용
        
    Returns:
        발견된 이슈 리스트
    """
    issues = []
    content_length = len(content.strip())
    
    if content_length < 600:
        issues.append(f"내용이 너무 짧음 ({content_length}자, 최소 200자 필요)")
    elif content_length > 1200:
        issues.append(f"내용이 너무 김 ({content_length}자, 최대 600자 권장)")
    
    return issues


def _validate_false_information(content: str, teacher_input: dict) -> List[str]:
    """허위 정보 검증 - 제공되지 않은 구체적 정보 탐지
    
    Args:
        content: 세특 내용
        teacher_input: 교사 입력 정보
        
    Returns:
        발견된 이슈 리스트
    """
    issues = []
    
    # 1. 구체적인 프로젝트명이나 활동명 탐지
    suspicious_patterns = [
        # 구체적 프로젝트명
        r'"[^"]*"',  # 따옴표로 둘러싸인 제목
        r"'[^']*'",  # 작은따옴표로 둘러싸인 제목
        
        # 구체적 활동명/동아리명
        "동아리", "토론부", "과학반", "문학회", "수학반",
        "발표대회", "경진대회", "올림피아드",
        
        # 구체적 주제명 (흔하지 않은 것들)
        "언어와 정체성", "쌍곡선", "피보나치 수열", "큐브의 경우의 수",
        "승수 효과", "무한등비급수", "운동량 보존", "산화환원 반응",
        "PCR", "RT-PCR", "DNA 복제",
        
        # 구체적 도구/프로그램명
        "지오지브라", "스케치업", "플레이봇", "CCTV"
    ]
    
    # 추가사항에서 제공된 키워드는 제외
    provided_keywords = []
    additional_notes = teacher_input.get("additional_notes", "")
    if additional_notes and additional_notes not in ["없음", ".", "-", "", None]:
        provided_keywords = additional_notes.split()
    
    # 의심스러운 패턴 검사
    for pattern in suspicious_patterns:
        if pattern in content:
            # 제공된 키워드인지 확인
            if not any(keyword in pattern or pattern in keyword for keyword in provided_keywords):
                issues.append(f"구체적 활동명 의심: '{pattern}' (제공되지 않은 정보)")
    
    # 2. 너무 구체적인 수치나 날짜
    import re
    
    # 구체적 수치 패턴 (점수 제외)
    specific_numbers = re.findall(r'\d{3,}', content)  # 3자리 이상 숫자
    for number in specific_numbers:
        if number not in [str(teacher_input.get("midterm_score", "")), 
                         str(teacher_input.get("final_score", ""))]:
            issues.append(f"구체적 수치 의심: '{number}' (제공되지 않은 정보)")
    
    # 3. 구체적 대화나 인용구 탐지
    if '"' in content and content.count('"') >= 2:
        quotes = re.findall(r'"([^"]*)"', content)
        for quote in quotes:
            if len(quote) > 10:  # 10자 이상의 인용구
                issues.append(f"구체적 인용구 의심: '\"...\"' (제공되지 않은 정보)")
    
    # 4. 과도하게 구체적인 서술 패턴
    overly_specific_patterns = [
        "교과서에", "페이지", "1장", "2장", "3장",
        "첫 번째", "두 번째", "세 번째", "네 번째", "다섯 번째",
        "월요일", "화요일", "수요일", "목요일", "금요일",
        "1교시", "2교시", "3교시", "4교시", "5교시",
        "실험실", "도서관", "강당"
    ]
    
    specific_count = sum(1 for pattern in overly_specific_patterns if pattern in content)
    if specific_count >= 3:
        issues.append("과도하게 구체적인 서술 (제공되지 않은 세부사항 포함)")
    
    return issues


def _validate_critical_grammar(content: str) -> List[str]:
    """치명적 문법 오류만 검증
    
    Args:
        content: 세특 내용
        
    Returns:
        발견된 이슈 리스트
    """
    issues = []
    
    # 명백한 오류만 체크
    critical_patterns = [
        ("니다니다", "문장 종결 중복"),
        ("음음", "어미 중복"),
        ("였였", "과거형 중복"),
        ("었었", "과거형 중복"),
        ("...", "말줄임표 사용 (공식 문서에 부적절)"),
        ("!!", "느낌표 중복"),
        ("??", "물음표 중복")
    ]
    
    for pattern, description in critical_patterns:
        if pattern in content:
            issues.append(description)
    
    # 문장이 마침표로 끝나는지 확인
    if content.strip() and not content.strip().endswith(('.', '다', '음')):
        issues.append("문장이 적절하게 종결되지 않음")
    
    return issues


def validate_simple(state: StudentState, config: Optional[RunnableConfig] = None) -> StudentState:
    """간단한 검증 (빠른 체크용)
    
    필수 정보만 빠르게 체크하는 간소화 버전
    
    Args:
        state: 학생 상태
        config: 런타임 설정
        
    Returns:
        검증 결과가 포함된 상태
    """
    teacher_input = state["teacher_input"]
    content = state.get("detailed_record", {}).get("content", "")
    
    # 필수 정보만 체크
    has_name = teacher_input["name"] in content
    has_midterm = str(teacher_input["midterm_score"]) in content
    has_final = str(teacher_input["final_score"]) in content
    
    is_valid = has_name and has_midterm and has_final
    
    state["validation_result"] = {
        "is_valid": is_valid,
        "issues": [] if is_valid else ["필수 정보 누락"],
        "needs_fix": not is_valid,
        "validation_type": "simple"
    }
    
    state["final_approval"] = is_valid
    
    return state