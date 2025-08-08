from typing import Any, Dict, List, Literal, Optional

from typing_extensions import TypedDict

from agent.utils.dto.types import DetailedRecord, ErrorInfo, TeacherInput


class StudentState(TypedDict):
    """개별 학생의 세부능력 특기사항 생성을 위한 State (21개→9개 필드로 간소화)
    """
    # 핵심 데이터 (4개)
    teacher_input: TeacherInput
    detailed_record: Optional[DetailedRecord]
    semester: int  # Literal["2학기"] 대신 int 사용
    academic_year: int
    
    # 처리 상태 (2개)
    generation_status: Literal["pending", "in_progress", "completed", "failed"]
    error_info: Optional[ErrorInfo]
    
    # 통합된 결과들 (2개)
    validation_result: Optional[Dict[str, Any]]  # 검증 결과 + 상태 + 재생성 정보 통합
    grammar_result: Optional[Dict[str, Any]]     # 문법 결과 + 상태 + 수정 정보 통합
    
    # 최종 승인 (1개)
    final_approval: Optional[bool]