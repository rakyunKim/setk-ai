from typing import Any, Dict, List, Literal, Optional

from typing_extensions import TypedDict

from agent.utils.dto.types import DetailedRecord, ErrorInfo, TeacherInput


class StudentState(TypedDict):
    """개별 학생의 세부능력 특기사항 생성을 위한 State
    """
    # 선생님 입력 정보
    teacher_input: TeacherInput
    
    # 생성된 세부능력 특기사항
    detailed_record: Optional[DetailedRecord]
    
    # 컨텍스트
    semester: Literal["2학기"]  # 현재는 2학기만
    academic_year: int
    
    # 처리 상태
    generation_status: Literal["pending", "in_progress", "completed", "failed"]
    error_info: Optional[ErrorInfo]
    
    # 검증 관련
    validation_status: Optional[Literal["pending", "completed", "failed"]]
    validation_result: Optional[Dict[str, Any]]
    needs_regeneration: Optional[bool]
    regeneration_reason: Optional[str]
    missing_items: Optional[List[str]]
    regeneration_attempts: Optional[int]  # 재생성 시도 횟수
    regeneration_history: Optional[List[Dict[str, Any]]]  # 재생성 기록
    
    # 문법 검증 관련
    grammar_check_status: Optional[Literal["pending", "completed", "failed"]]
    grammar_check_result: Optional[Dict[str, Any]]
    needs_grammar_fix: Optional[bool]
    grammar_issues: Optional[List[Dict[str, Any]]]
    grammar_fix_attempts: Optional[int]  # 문법 수정 시도 횟수
    grammar_fix_history: Optional[List[Dict[str, Any]]]  # 문법 수정 기록
    grammar_fix_note: Optional[str]  # 문법 수정 관련 메모
    
    # 최종 승인
    final_approval: Optional[bool]