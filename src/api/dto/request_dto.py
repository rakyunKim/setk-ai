"""API 요청 DTO
"""
from typing import Optional

from pydantic import BaseModel

from agent.utils.dto.types import TeacherInput


class TeacherInputRequest(BaseModel):
    """API 요청용 Teacher Input 모델"""
    student_id: int
    name: str
    subject: str
    midterm_score: int
    final_score: int
    semester: int
    academic_year: int
    additional_notes: Optional[str] = None
    
    def to_dict(self) -> TeacherInput:
        """LangGraph용 딕셔너리로 변환"""
        return {
            "student_id": self.student_id,
            "name": self.name,
            "subject": self.subject,
            "midterm_score": self.midterm_score,
            "final_score": self.final_score,
            "additional_notes": self.additional_notes
        }