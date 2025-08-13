"""API 요청 DTO
"""
from typing import Optional

from pydantic import BaseModel, Field

from agent.utils.dto.types import TeacherInput


class TeacherInputRequest(BaseModel):
    """API 요청용 Teacher Input 모델"""
    student_id: int
    name: str
    subject: str
    school_level: str = Field(
        default="고등학생",
        description="학교급 (초등학생, 중학생, 고등학생)"
    )
    midterm_score: int
    final_score: int
    semester: int
    academic_year: int
    additional_notes: Optional[str] = None
    achievement_standards: Optional[str] = Field(
        default=None,
        description="과목별 성취기준 (줄바꿈으로 구분된 문자열)"
    )
    
    def to_dict(self) -> TeacherInput:
        """LangGraph용 딕셔너리로 변환"""
        return {
            "student_id": self.student_id,
            "name": self.name,
            "subject": self.subject,
            "school_level": self.school_level,
            "midterm_score": self.midterm_score,
            "final_score": self.final_score,
            "additional_notes": self.additional_notes,
            "achievement_standards": self.achievement_standards
        }