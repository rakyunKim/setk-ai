from typing import List, Optional, TypedDict

from agent.utils.dto.types import DetailedRecord, ErrorInfo


class BatchProcessingState(TypedDict):
    """배치 처리를 위한 상위 State"""
    total_students: int
    processed_students: int
    failed_students: List[str]  # student_id list
    batch_id: str
    
    
class StudentProcessingResult(TypedDict):
    """개별 학생 처리 결과"""
    student_id: str
    status: str  # "success", "failed"
    detailed_record: Optional[DetailedRecord]
    error_info: Optional[ErrorInfo]