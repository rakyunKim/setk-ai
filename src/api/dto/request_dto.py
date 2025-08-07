"""API 요청 DTO
"""
from typing import Optional

from pydantic import BaseModel

from agent.utils.dto.types import TeacherInput


class TeacherInputRequest(BaseModel):
    """API 요청용 Teacher Input 모델"""
    student_number: int
    name: str
    subject_name: str
    midterm_score: int
    final_score: int
    additional_notes: Optional[str] = None
    
    def to_dict(self) -> TeacherInput:
        """LangGraph용 딕셔너리로 변환"""
        return {
            "student_number": self.student_number,
            "name": self.name,
            "subject_name": self.subject_name,
            "midterm_score": self.midterm_score,
            "final_score": self.final_score,
            "additional_notes": self.additional_notes
        }