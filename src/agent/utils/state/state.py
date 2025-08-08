from typing import Any, Dict, List, Literal, Optional

from typing_extensions import TypedDict

from agent.utils.dto.types import DetailedRecord, ErrorInfo, TeacherInput


class StudentState(TypedDict):
    """개별 학생의 세부능력 특기사항 생성을 위한 State
    """
    # 핵심 데이터
    teacher_input: TeacherInput
    detailed_record: Optional[DetailedRecord]
    semester: int
    academic_year: int
    
    # RAG 관련 필드 (새로 추가)
    retrieved_examples: Optional[List[str]]      # RAG로 검색된 예시들
    custom_examples: Optional[List[str]]         # 사용자가 제공한 예시들
    search_query: Optional[str]                  # 검색에 사용된 쿼리
    search_metadata: Optional[Dict[str, Any]]    # 검색 메타데이터
    
    # 처리 상태
    generation_status: Literal["pending", "in_progress", "completed", "failed", "fixed"]
    error_info: Optional[ErrorInfo]
    
    # 검증 결과 (통합)
    validation_result: Optional[Dict[str, Any]]  # 입력 정보 + 품질 검증 통합
    
    # 수정 관련
    fix_attempts: Optional[int]                  # 수정 시도 횟수
    fix_examples: Optional[List[str]]            # Fix용 추가 예시
    
    # 최종 승인
    final_approval: Optional[bool]