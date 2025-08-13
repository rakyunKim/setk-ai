"""Vector Database 관리자 - 싱글톤 패턴으로 구현"""

import os
from typing import List, Dict, Optional, Any
from langchain_community.vectorstores import FAISS  # 새로운 import 경로
from langchain_google_genai import GoogleGenerativeAIEmbeddings
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
            
            # Google 임베딩 모델 초기화 (무료, 성능 우수)
            # GEMINI_API_KEY는 이미 .env.local에 있음
            api_key = os.getenv("GEMINI_API_KEY")
            if not api_key:
                raise ValueError("GEMINI_API_KEY가 설정되지 않았습니다.")
            
            self.embeddings = GoogleGenerativeAIEmbeddings(
                model="models/text-embedding-004",  # 최신 구글 임베딩 모델
                google_api_key=api_key
            )
            
            # 통합 벡터스토어 (과목 구분 없이 하나로)
            self.vectorstore = None
            
            # FAISS 저장 경로 설정
            self.db_path = "data/vector_db"
            self.faiss_index_path = os.path.join(self.db_path, "faiss_index")
            
            # 디렉토리 생성
            os.makedirs(self.db_path, exist_ok=True)
            
            # 벡터 DB 초기화
            self.initialize_vectorstore()
            
            self._initialized = True
            logger.info("VectorDBManager 초기화 완료")
    
    def initialize_vectorstore(self):
        """벡터스토어 초기화 - 기존 저장된 것 로드 또는 새로 생성"""
        # 1. 기존 벡터스토어가 있는지 확인
        if os.path.exists(self.faiss_index_path + ".faiss"):
            try:
                logger.info("기존 벡터스토어 로드 중...")
                self.vectorstore = FAISS.load_local(
                    self.faiss_index_path,
                    self.embeddings,
                    allow_dangerous_deserialization=True
                )
                logger.info("기존 벡터스토어 로드 완료")
                return
            except Exception as e:
                logger.warning(f"기존 벡터스토어 로드 실패: {e}. 새로 생성합니다.")
        
        # 2. 새로 생성
        logger.info("벡터스토어 새로 생성 중...")
        from .example_loader import ExampleLoader
        
        loader = ExampleLoader()
        examples = loader.load_all_examples()
        
        logger.info(f"총 {len(examples)}개 예시에 대해 임베딩 생성 시작...")
        
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
                        "school_level": example.get("school_level", "")
                    }
                )
                documents.append(doc)
            
            # FAISS 벡터스토어 생성 (배치 처리)
            logger.info("임베딩 생성 중... (배치 처리로 안전하게 처리)")
            try:
                # 배치 크기 설정 (50개씩)
                batch_size = 50
                total_batches = (len(documents) + batch_size - 1) // batch_size
                
                # 첫 번째 배치로 벡터스토어 초기화
                first_batch = documents[:batch_size]
                logger.info(f"첫 번째 배치 처리 중: {len(first_batch)}개")
                
                self.vectorstore = FAISS.from_documents(
                    documents=first_batch,
                    embedding=self.embeddings
                )
                logger.info(f"첫 번째 배치 완료 (1/{total_batches})")
                
                # 나머지 배치들 추가
                for i in range(1, total_batches):
                    start_idx = i * batch_size
                    end_idx = min(start_idx + batch_size, len(documents))
                    batch = documents[start_idx:end_idx]
                    
                    logger.info(f"배치 {i+1}/{total_batches} 처리 중: {len(batch)}개")
                    self.vectorstore.add_documents(batch)
                    logger.info(f"배치 {i+1}/{total_batches} 완료")
                
                logger.info(f"전체 {len(documents)}개 예시로 벡터스토어 생성 완료")
                
            except Exception as e:
                logger.error(f"벡터스토어 생성 실패: {e}")
                # 실패 시 빈 벡터스토어 생성
                logger.info("빈 벡터스토어 생성으로 대체...")
                self.vectorstore = FAISS.from_texts(
                    texts=["초기화"],
                    embedding=self.embeddings,
                    metadatas=[{"type": "init"}]
                )
                logger.info("빈 벡터스토어로 대체 생성 완료")
        
        # 3. 디스크에 저장
        try:
            self.vectorstore.save_local(self.faiss_index_path)
            logger.info(f"벡터스토어 저장 완료: {self.faiss_index_path}")
        except Exception as e:
            logger.error(f"벡터스토어 저장 실패: {e}")
    
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
                # fetch_k를 크게 설정해서 충분한 후보를 가져온 후 필터링
                logger.debug(f"필터 검색 - filter: {filter}, query: {query}, k: {k}")
                results = self.vectorstore.similarity_search(
                    query=query,
                    k=k,
                    filter=filter,
                    fetch_k=200  # 더 많은 후보를 가져온 후 필터링
                )
                logger.debug(f"필터 검색 완료: '{query[:50]}...' -> {len(results)}개 결과")
            else:
                # 일반 검색
                results = self.vectorstore.similarity_search(
                    query=query,
                    k=k
                )
                logger.debug(f"일반 검색 완료: '{query[:50]}...' -> {len(results)}개 결과")
            
            return results
            
        except Exception as e:
            logger.error(f"검색 중 오류: {e}")
            return []
    
    def clear_cache(self):
        """저장된 벡터스토어 삭제"""
        try:
            import shutil
            if os.path.exists(self.db_path):
                shutil.rmtree(self.db_path)
            else:
                logger.info("삭제할 캐시가 없음")
        except Exception as e:
            logger.error(f"캐시 삭제 중 오류: {e}")


# 전역 싱글톤 인스턴스
vector_db = VectorDBManager()