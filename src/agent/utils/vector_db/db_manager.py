"""Vector Database 관리자 - 싱글톤 패턴으로 구현"""

from typing import List, Dict, Optional, Any
from langchain.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings
from langchain.schema import Document
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class VectorDBManager:
    """벡터 데이터베이스를 관리하는 싱글톤 클래스
    
    서버 시작 시 한 번만 초기화되며, 모든 예시 세특을 벡터화하여 저장합니다.
    """
    
    _instance = None
    _initialized = False
    
    def __new__(cls):
        """싱글톤 인스턴스 생성"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """초기화 - 한 번만 실행됨"""
        if not self._initialized:
            logger.info("VectorDBManager 초기화 시작")
            
            # OpenAI 임베딩 모델 초기화
            self.embeddings = OpenAIEmbeddings(
                model="text-embedding-3-small"  # 빠르고 저렴한 모델
            )
            
            # 통합 벡터스토어 (과목 구분 없이 하나로)
            self.vectorstore = None
            
            # 캐시는 사용하지 않음 - 매번 새로 생성
            
            # 벡터 DB 초기화
            self.initialize_vectorstore()
            
            self._initialized = True
            logger.info("VectorDBManager 초기화 완료")
    
    def initialize_vectorstore(self):
        """벡터스토어 초기화 - 매번 새로 생성"""
        logger.info("벡터스토어 생성 중...")
        from .example_loader import ExampleLoader
        
        loader = ExampleLoader()
        examples = loader.load_all_examples()
        
        if not examples:
            logger.warning("로드된 예시가 없음, 빈 벡터스토어 생성")
            # 빈 벡터스토어 생성
            self.vectorstore = FAISS.from_texts(
                texts=["초기화"],
                embedding=self.embeddings,
                metadatas=[{"type": "init"}]
            )
        else:
            # 예시들을 Document 객체로 변환
            documents = []
            for example in examples:
                doc = Document(
                    page_content=example["content"],
                    metadata={
                        "subject": example.get("subject", "general"),
                        "keywords": example.get("keywords", []),
                        "activity_type": example.get("activity_type", ""),
                        "grade": example.get("grade", "")
                    }
                )
                documents.append(doc)
            
            # FAISS 벡터스토어 생성
            self.vectorstore = FAISS.from_documents(
                documents=documents,
                embedding=self.embeddings
            )
            
            logger.info(f"{len(documents)}개 예시로 벡터스토어 생성 완료")
    
    def similarity_search(self, 
                         query: str, 
                         k: int = 3,
                         filter: Optional[Dict[str, Any]] = None) -> List[Document]:
        """유사도 검색
        
        Args:
            query: 검색 쿼리
            k: 반환할 결과 개수
            filter: 메타데이터 필터 (선택)
            
        Returns:
            유사한 Document 리스트
        """
        if not self.vectorstore:
            logger.error("벡터스토어가 초기화되지 않음")
            return []
        
        try:
            if filter:
                # 필터가 있으면 필터링된 검색
                results = self.vectorstore.similarity_search(
                    query=query,
                    k=k,
                    filter=filter
                )
            else:
                # 일반 검색
                results = self.vectorstore.similarity_search(
                    query=query,
                    k=k
                )
            
            logger.debug(f"검색 완료: '{query[:50]}...' -> {len(results)}개 결과")
            return results
            
        except Exception as e:
            logger.error(f"검색 중 오류: {e}")
            return []
    
    def similarity_search_with_score(self,
                                    query: str,
                                    k: int = 3) -> List[tuple[Document, float]]:
        """유사도 점수와 함께 검색
        
        Args:
            query: 검색 쿼리
            k: 반환할 결과 개수
            
        Returns:
            (Document, 점수) 튜플 리스트
        """
        if not self.vectorstore:
            logger.error("벡터스토어가 초기화되지 않음")
            return []
        
        try:
            results = self.vectorstore.similarity_search_with_score(
                query=query,
                k=k
            )
            logger.debug(f"점수 포함 검색 완료: {len(results)}개 결과")
            return results
            
        except Exception as e:
            logger.error(f"검색 중 오류: {e}")
            return []
    
    def add_texts(self, 
                  texts: List[str], 
                  metadatas: Optional[List[Dict]] = None):
        """런타임에 새로운 텍스트 추가
        
        Args:
            texts: 추가할 텍스트 리스트
            metadatas: 메타데이터 리스트
        """
        if not self.vectorstore:
            logger.error("벡터스토어가 초기화되지 않음")
            return
        
        try:
            self.vectorstore.add_texts(
                texts=texts,
                metadatas=metadatas or [{}] * len(texts)
            )
            logger.info(f"{len(texts)}개 텍스트 추가 완료")
            
            # 캐시 사용하지 않음
            
        except Exception as e:
            logger.error(f"텍스트 추가 중 오류: {e}")
    
    def add_documents(self, documents: List[Document]):
        """런타임에 새로운 문서 추가
        
        Args:
            documents: Document 객체 리스트
        """
        if not self.vectorstore:
            logger.error("벡터스토어가 초기화되지 않음")
            return
        
        try:
            self.vectorstore.add_documents(documents)
            logger.info(f"{len(documents)}개 문서 추가 완료")
            
            # 캐시 사용하지 않음
            
        except Exception as e:
            logger.error(f"문서 추가 중 오류: {e}")
    
    def clear_cache(self):
        """캐시 사용하지 않으므로 빈 메서드"""
        logger.info("캐시를 사용하지 않음 - 작업 없음")


# 전역 싱글톤 인스턴스
vector_db = VectorDBManager()