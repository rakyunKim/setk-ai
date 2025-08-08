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
                       additional_notes: Optional[str] = None,
                       custom_examples: Optional[List[str]] = None,
                       k: int = 3) -> List[str]:
        """과목과 특이사항을 조합하여 예시 검색
        
        Args:
            subject: 과목명
            additional_notes: 특이사항/추가 활동
            custom_examples: 사용자가 제공한 커스텀 예시
            k: 반환할 예시 개수
            
        Returns:
            검색된 예시 텍스트 리스트
        """
        # 1. 사용자가 제공한 예시가 있으면 우선 추가
        if custom_examples:
            self._add_custom_examples(custom_examples, subject)
        
        # 2. 검색 쿼리 구성
        search_query = self._build_search_query(subject, additional_notes)
        
        # 3. 검색 수행
        results = self._perform_search(search_query, subject, k)
        
        # 4. 결과 텍스트 추출
        example_texts = [doc.page_content for doc in results]
        
        logger.info(f"검색 완료: '{subject}' -> {len(example_texts)}개 예시")
        
        return example_texts
    
    def search_examples_with_score(self,
                                   subject: str,
                                   additional_notes: Optional[str] = None,
                                   k: int = 3) -> List[Tuple[str, float]]:
        """점수와 함께 예시 검색
        
        Args:
            subject: 과목명
            additional_notes: 특이사항
            k: 반환할 예시 개수
            
        Returns:
            (예시 텍스트, 유사도 점수) 튜플 리스트
        """
        # 검색 쿼리 구성
        search_query = self._build_search_query(subject, additional_notes)
        
        # 점수와 함께 검색
        results = self.db_manager.similarity_search_with_score(search_query, k)
        
        # 결과 포맷팅
        examples_with_scores = [
            (doc.page_content, score) 
            for doc, score in results
        ]
        
        return examples_with_scores
    
    def _build_search_query(self, subject: str, additional_notes: Optional[str]) -> str:
        """검색 쿼리 구성
        
        Args:
            subject: 과목명
            additional_notes: 특이사항
            
        Returns:
            구성된 검색 쿼리
        """
        query_parts = []
        
        # 1. 일반 과목인 경우 과목명 포함
        if self._is_common_subject(subject):
            query_parts.append(f"과목: {subject}")
        
        # 2. 특이사항이 있고 유의미한 경우 포함
        if additional_notes and additional_notes not in ["없음", ".", "-", ""]:
            # 특이사항이 더 중요하므로 앞에 배치
            query_parts.insert(0, f"활동: {additional_notes}")
        
        # 3. 쿼리가 비어있으면 과목명만이라도 사용
        if not query_parts and subject:
            query_parts.append(subject)
        
        # 4. 그래도 비어있으면 기본 쿼리
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
    
    def _perform_search(self, query: str, subject: str, k: int) -> List[Document]:
        """실제 검색 수행
        
        Args:
            query: 검색 쿼리
            subject: 과목명 (필터링용)
            k: 결과 개수
            
        Returns:
            검색 결과 Document 리스트
        """
        # 일반 과목인 경우 메타데이터 필터 적용
        if self._is_common_subject(subject):
            # 먼저 과목 필터로 검색
            filter_dict = {"subject": subject}
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
    
    def _add_custom_examples(self, examples: List[str], subject: str):
        """사용자 제공 예시를 벡터 DB에 추가
        
        Args:
            examples: 예시 텍스트 리스트
            subject: 과목명
        """
        try:
            metadatas = [
                {
                    "subject": subject,
                    "source": "user_provided",
                    "runtime": True
                }
                for _ in examples
            ]
            
            self.db_manager.add_texts(
                texts=examples,
                metadatas=metadatas
            )
            
            logger.info(f"사용자 제공 예시 {len(examples)}개 추가")
            
        except Exception as e:
            logger.error(f"커스텀 예시 추가 실패: {e}")
    
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