"""검색 전략을 구현하는 Retriever 클래스"""

from typing import List, Optional, Tuple
from langchain.schema import Document
from .db_manager import vector_db
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class ExampleRetriever:
    """예시 세특 검색을 위한 Retriever
    
    과목명과 특이사항을 조합하여 가장 관련성 높은 예시를 검색합니다.
    """
    
    # 일반 과목 리스트 (이 과목들은 과목명을 검색에 포함)
    COMMON_SUBJECTS = [
        "수학", "영어", "국어", "과학", "물리", "화학", "생물", "지구과학",
        "역사", "한국사", "세계사", "지리", "한국지리", "세계지리",
        "정치", "경제", "사회", "윤리", "도덕", "철학",
        "음악", "미술", "체육", "기술", "가정", "정보", "컴퓨터"
    ]
    
    def __init__(self):
        """초기화"""
        self.db_manager = vector_db
    
    def search_examples(self, 
                       subject: str,
                       school_level: Optional[str] = None,
                       additional_notes: Optional[str] = None,
                       achievement_standards: Optional[str] = None,
                       k: int = 3) -> List[str]:
        """과목과 학교급, 특이사항, 성취기준을 조합하여 예시 검색
        
        Args:
            subject: 과목명
            school_level: 학교급 (초등학생, 중학생, 고등학생)
            additional_notes: 특이사항/추가 활동
            achievement_standards: 과목 성취기준
            k: 반환할 예시 개수
            
        Returns:
            검색된 예시 텍스트 리스트
        """
        # 1. 검색 쿼리 구성 (achievement_standards, school_level 포함)
        search_query = self._build_search_query(subject, additional_notes, achievement_standards, school_level)
        
        # 2. 벡터 DB에서 검색 수행 (school_level 전달)
        results = self._perform_search(search_query, subject, school_level, k)
        
        # 3. 결과 텍스트 추출
        example_texts = [doc.page_content for doc in results]
        
        logger.info(f"검색 완료: '{subject}' -> 벡터DB {len(results)}개")
        
        return example_texts
    
    def _build_search_query(self, subject: str, 
                           additional_notes: Optional[str] = None,
                           achievement_standards: Optional[str] = None,
                           school_level: Optional[str] = None) -> str:
        """검색 쿼리 구성
        
        Args:
            subject: 과목명
            additional_notes: 특이사항
            achievement_standards: 성취기준
            school_level: 학교급 (초등학생, 중학생, 고등학생)
            
        Returns:
            구성된 검색 쿼리
        """
        query_parts = []
        
        # 1. 학교급이 있으면 가장 먼저 포함 (중요한 필터링 기준)
        if school_level and school_level not in ["없음", ".", "-", ""]:
            query_parts.append(f"학교급: {school_level}")
        
        # 2. 일반 과목인 경우 과목명 포함
        if self._is_common_subject(subject):
            query_parts.append(f"과목: {subject}")
        
        # 3. 특이사항이 있고 유의미한 경우 포함
        if additional_notes and additional_notes not in ["없음", ".", "-", ""]:
            # 특이사항이 중요하므로 앞쪽에 배치
            if school_level:  # 학교급이 있으면 두 번째로
                query_parts.insert(1, f"추가사항: {additional_notes}")
            else:  # 학교급이 없으면 첫 번째로
                query_parts.insert(0, f"추가사항: {additional_notes}")
        
        # 4. 성취기준이 있으면 주요 키워드 추출하여 포함
        if achievement_standards and achievement_standards.strip():
            # 성취기준에서 핵심 키워드 추출 (첫 줄이나 주요 개념)
            standards_lines = [s.strip() for s in achievement_standards.split('\n') if s.strip()]
            if standards_lines:
                # 첫 번째 성취기준이나 짧은 키워드 추가
                key_concepts = standards_lines[0][:50] if standards_lines else ""
                if key_concepts:
                    query_parts.append(f"학습내용: {key_concepts}")
        
        # 5. 쿼리가 비어있으면 과목명만이라도 사용
        if not query_parts and subject:
            query_parts.append(subject)
        
        # 6. 그래도 비어있으면 기본 쿼리
        if not query_parts:
            query_parts.append("학생 세부능력 특기사항")
        
        search_query = " ".join(query_parts)
        logger.debug(f"검색 쿼리 구성: {search_query}")
        
        return search_query
    
    def _is_common_subject(self, subject: str) -> bool:
        """일반 과목인지 확인
        
        Args:
            subject: 과목명
            
        Returns:
            일반 과목 여부
        """
        # 과목명에 일반 과목이 포함되어 있는지 확인
        for common in self.COMMON_SUBJECTS:
            if common in subject:
                return True
        return False
    
    def _perform_search(self, query: str, subject: str, school_level: Optional[str], k: int) -> List[Document]:
        """실제 검색 수행
        
        Args:
            query: 검색 쿼리
            subject: 과목명 (필터링용)
            school_level: 학교급 (필터링용)
            k: 결과 개수
            
        Returns:
            검색 결과 Document 리스트
        """
        # 필터 구성
        filter_dict = {}
        
        # 일반 과목인 경우 과목 필터 추가
        if self._is_common_subject(subject):
            filter_dict["subject"] = subject
        
        # school_level이 있으면 필터에 추가
        if school_level:
            filter_dict["school_level"] = school_level
            logger.debug(f"school_level 필터 적용: {school_level}")
        
        # 필터가 있으면 필터 검색, 없으면 일반 검색
        if filter_dict:
            # 필터로 검색
            results = self.db_manager.similarity_search(
                query=query,
                k=k,
                filter=filter_dict
            )
            
            # 결과가 부족하면 필터 없이 추가 검색
            if len(results) < k:
                additional_results = self.db_manager.similarity_search(
                    query=query,
                    k=k - len(results)
                )
                # 중복 제거하고 추가
                existing_contents = {doc.page_content for doc in results}
                for doc in additional_results:
                    if doc.page_content not in existing_contents:
                        results.append(doc)
        else:
            # 특수 과목은 필터 없이 검색
            results = self.db_manager.similarity_search(
                query=query,
                k=k
            )
        
        return results
    
    def get_diverse_examples(self, subject: str, k: int = 3) -> List[str]:
        """다양한 예시 획득 (중복 방지)
        
        Args:
            subject: 과목명
            k: 결과 개수
            
        Returns:
            다양한 예시 리스트
        """
        # 더 많이 검색한 후 다양성 확보
        candidates = self.db_manager.similarity_search(
            query=f"과목: {subject}",
            k=k * 2  # 2배 검색
        )
        
        # 유사도가 너무 높은 것들은 제외
        selected = []
        selected_contents = set()
        
        for doc in candidates:
            content = doc.page_content
            # 이미 선택된 것과 너무 유사하지 않으면 추가
            if not self._is_too_similar(content, selected_contents):
                selected.append(content)
                selected_contents.add(content[:50])  # 앞부분만 저장
                
                if len(selected) >= k:
                    break
        
        return selected
    
    def _is_too_similar(self, content: str, existing: set) -> bool:
        """기존 예시와 너무 유사한지 확인
        
        Args:
            content: 확인할 내용
            existing: 기존 내용 집합
            
        Returns:
            너무 유사한지 여부
        """
        content_start = content[:50]
        for existing_start in existing:
            # 시작 부분이 80% 이상 일치하면 유사하다고 판단
            similarity = sum(1 for a, b in zip(content_start, existing_start) if a == b)
            if similarity / min(len(content_start), len(existing_start)) > 0.8:
                return True
        return False


# 전역 인스턴스
example_retriever = ExampleRetriever()