from datetime import datetime
from typing import Optional

from typing_extensions import TypedDict


class TeacherInput(TypedDict):
    """선생님이 입력하는 정보"""
    student_number: int
    name: str
    subject_name: str
    midterm_score: int  # 2학기 중간 수행평가 결과
    final_score: int  # 2학기 기말 수행평가 결과
    additional_notes: Optional[str]  # 봉사활동, 특이사항


class AssessmentScore(TypedDict):
    """수행평가 성적 정보"""
    midterm_score: int  # 2학기 중간 수행평가
    final_score: int  # 2학기 기말 수행평가 


class StudentInfo(TypedDict):
    """학생 기본 정보"""
    student_number: int  # 번호
    name: str  # 이름
    subject_name: str  # 과목명


class DetailedRecord(TypedDict):
    """세부능력 및 특기사항"""
    subject: str
    content: str
    generated_at: datetime
    version: int


class ErrorInfo(TypedDict):
    """에러 정보 (ApiException과 동일한 형식)"""
    error_code: str
    message: Optional[str]