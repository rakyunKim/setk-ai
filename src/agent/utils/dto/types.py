from datetime import datetime
from typing import Optional

from typing_extensions import TypedDict


class TeacherInput(TypedDict):
    """선생님 입력 정보 (모든 필드 통합)"""
    student_id: int
    name: str
    subject: str
    midterm_score: int  # 2학기 중간 수행평가 결과
    final_score: int  # 2학기 기말 수행평가 결과
    additional_notes: Optional[str]  # 봉사활동, 특이사항


class DetailedRecord(TypedDict):
    """세부능력 및 특기사항"""
    student_id: int
    subject: str
    content: str
    generated_at: datetime
    version: int


class ErrorInfo(TypedDict):
    """에러 정보 (ApiException과 동일한 형식)"""
    error_code: str
    message: Optional[str]