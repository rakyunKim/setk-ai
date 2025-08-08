"""예시 세특 데이터 로더 및 전처리"""

import json
import os
from typing import List, Dict, Optional
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class ExampleLoader:
    """예시 세특 데이터를 로드하고 전처리하는 클래스"""
    
    def __init__(self):
        """초기화"""
        self.data_dir = "src/agent/data"
        self.default_examples = self._get_default_examples()
    
    def load_all_examples(self) -> List[Dict]:
        """모든 예시 데이터 로드
        
        Returns:
            예시 데이터 리스트 [{content, subject, keywords, ...}, ...]
        """
        all_examples = []
        
        # 1. 파일에서 로드 시도
        file_examples = self._load_from_files()
        if file_examples:
            all_examples.extend(file_examples)
            logger.info(f"파일에서 {len(file_examples)}개 예시 로드")
        
        # 2. 파일이 없으면 기본 예시 사용
        if not all_examples:
            all_examples = self.default_examples
            logger.info(f"기본 예시 {len(all_examples)}개 사용")
        
        # 3. 전처리 (청킹 등)
        processed_examples = self._process_examples(all_examples)
        
        return processed_examples
    
    def _load_from_files(self) -> List[Dict]:
        """파일에서 예시 로드"""
        examples = []
        
        # examples.json 파일 경로
        json_path = os.path.join(self.data_dir, "examples.json")
        
        if os.path.exists(json_path):
            try:
                with open(json_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    
                # JSON 구조에 따라 파싱
                if isinstance(data, dict) and "examples" in data:
                    examples = data["examples"]
                elif isinstance(data, list):
                    examples = data
                    
                logger.info(f"{json_path}에서 {len(examples)}개 예시 로드")
                
            except Exception as e:
                logger.error(f"JSON 로드 실패: {e}")
        
        return examples
    
    def _process_examples(self, examples: List[Dict]) -> List[Dict]:
        """예시 데이터 전처리 및 청킹
        
        Args:
            examples: 원본 예시 리스트
            
        Returns:
            처리된 예시 리스트
        """
        processed = []
        
        for example in examples:
            # Dict 형태가 아니면 변환
            if isinstance(example, str):
                example = {"content": example}
            
            content = example.get("content", "")
            
            # 긴 텍스트는 청킹 (300자 기준)
            if len(content) > 300:
                chunks = self._chunk_text(content)
                for i, chunk in enumerate(chunks):
                    processed_example = {
                        "content": chunk,
                        "subject": example.get("subject", "general"),
                        "keywords": example.get("keywords", []),
                        "activity_type": example.get("activity_type", ""),
                        "grade": example.get("grade", ""),
                        "chunk_index": i
                    }
                    processed.append(processed_example)
            else:
                # 짧은 텍스트는 그대로
                processed_example = {
                    "content": content,
                    "subject": example.get("subject", "general"),
                    "keywords": example.get("keywords", []),
                    "activity_type": example.get("activity_type", ""),
                    "grade": example.get("grade", ""),
                    "chunk_index": 0
                }
                processed.append(processed_example)
        
        return processed
    
    def _chunk_text(self, text: str, chunk_size: int = 250) -> List[str]:
        """텍스트를 의미 있는 단위로 분할
        
        Args:
            text: 분할할 텍스트
            chunk_size: 청크 크기
            
        Returns:
            분할된 텍스트 리스트
        """
        # 문장 단위로 분할
        sentences = text.split('.')
        chunks = []
        current_chunk = ""
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
                
            # 현재 청크에 추가해도 크기를 넘지 않으면 추가
            if len(current_chunk) + len(sentence) + 1 < chunk_size:
                if current_chunk:
                    current_chunk += ". " + sentence
                else:
                    current_chunk = sentence
            else:
                # 현재 청크 저장하고 새 청크 시작
                if current_chunk:
                    chunks.append(current_chunk + ".")
                current_chunk = sentence
        
        # 마지막 청크 저장
        if current_chunk:
            chunks.append(current_chunk + ".")
        
        return chunks
    
    def _get_default_examples(self) -> List[Dict]:
        """기본 예시 데이터 (하드코딩)"""
        return [
            {
                "subject": "수학",
                "content": "쌍곡선에 대해 배우면서 교과서에 쌍곡면의 구조가 풍압에 잘 견뎌 냉각로 등에 사용된다는 것을 보고 '왜 그럴까?'에 대해 관심을 가지게 되어 관련된 탐구를 진행함. 실험조건에 맞는 쌍곡면을 만드는 쌍곡선의 식을 세우고, 지오지브라, 스케치업 등을 이용하여 정확한 실험물을 수학적으로 제작함. 또한 실험결과를 해석할 때도 벡터의 개념을 도입하여 원기둥이 사각기둥보다 풍압에 잘 견딜 수 있었던 이유를 설명함.",
                "keywords": ["쌍곡선", "탐구", "실험", "지오지브라", "벡터"],
                "activity_type": "탐구",
                "grade": "고2"
            },
            {
                "subject": "수학",
                "content": "수학탐구시간에 자신이 가장 좋아하는 수열인 피보나치 수열에 대해 조사하여 피보나치 수열의 개념과 일반항을 구하는 방법을 탐구하고 정보시간에 배우는 플레이봇을 통해 피보나치 수열을 구하는 프로그램을 직접 만들어 수학을 탐구하고 보고서를 작성함.",
                "keywords": ["피보나치", "수열", "프로그래밍", "융합", "보고서"],
                "activity_type": "탐구",
                "grade": "고2"
            },
            {
                "subject": "수학",
                "content": "교내 수학체험전에서 큐브의 경우의 수에 대해 관심을 가져 222큐브와 333큐브에서 엣지 조각의 개수는 짝수개이며 코너조각의 돌아간 각도의 합은 360도가 되어야한다는 규칙을 알게 되었고 각 경우의 수를 직접 계산함. 또한, 큐브의 모든 섞인 상태를 집합으로 하고 돌리는 회전을 연산으로 구성하여 군(Group)이 됨을 확인하고 자료를 제작하여 전시하고 친구들에게 실생활의 여러 부분에서 수학을 발견할 수 있다는 사실을 알려줌.",
                "keywords": ["큐브", "경우의수", "군론", "수학체험전", "전시"],
                "activity_type": "대회",
                "grade": "고2"
            },
            {
                "subject": "수학",
                "content": "논리적인 사고력과 사회현상에 대한 이해, 끊임없이 노력하는 열정적인 학업태도가 돋보이는 학생으로 함수의 극한, 미적분 등 전 영역에 걸쳐 개념별로 본질을 파악하여 전체적인 맥을 연결할 수 있는 능력이 있음.",
                "keywords": ["논리적사고", "미적분", "극한", "개념이해"],
                "activity_type": "평가",
                "grade": "고3"
            },
            {
                "subject": "수학",
                "content": "조세의 과다 징수에 대한 기사를 읽던 중 재정 정책의 효과가 무한등비급수로 나타나는 것을 보고 이를 수학 시간에 적용해보고자 함. 승수 효과를 주제로 선정하여 다양한 서적들을 통해 자료를 수집함. 이를 바탕으로 조세 감소와 이로 인해 발생하는 국민소득, 소비 증가분을 계산하고 더욱 나아가 통화정책의 투자 승수와 통화승수를 조사함.",
                "keywords": ["무한등비급수", "경제", "승수효과", "융합"],
                "activity_type": "탐구",
                "grade": "고2"
            },
            {
                "subject": "물리",
                "content": "수업 시간에 배운 운동량 보존 법칙을 실생활에 적용하여 자동차 충돌 실험을 설계함. 다양한 질량의 모형 자동차를 제작하고 충돌 전후의 속도를 측정하여 운동량이 보존됨을 실험적으로 증명함. 실험 데이터를 그래프로 나타내고 오차 원인을 분석하는 과정에서 과학적 탐구 능력을 보여줌.",
                "keywords": ["운동량보존", "실험", "충돌", "데이터분석"],
                "activity_type": "실험",
                "grade": "고2"
            },
            {
                "subject": "화학",
                "content": "산화환원 반응에 대해 학습한 후 과일 전지 만들기 프로젝트를 진행함. 레몬, 오렌지, 감자 등 다양한 과일과 채소를 이용하여 전지를 만들고 전압을 측정함. pH와 전압의 관계를 탐구하고 최적의 전해질 농도를 찾기 위한 실험을 설계하여 수행함.",
                "keywords": ["산화환원", "전지", "실험", "pH"],
                "activity_type": "프로젝트",
                "grade": "고2"
            },
            {
                "subject": "생물",
                "content": "DNA 복제 과정에 대해 학습한 후 PCR(중합효소 연쇄 반응) 기술의 원리와 응용에 대해 심화 탐구함. COVID-19 진단에 사용되는 RT-PCR의 원리를 이해하고, 이를 바탕으로 감염병 진단 기술의 발전 방향에 대한 보고서를 작성함.",
                "keywords": ["DNA", "PCR", "생명공학", "COVID-19"],
                "activity_type": "탐구",
                "grade": "고3"
            }
        ]
    
    def add_runtime_examples(self, examples: List[Dict]):
        """런타임에 예시 추가 (메모리에만)
        
        Args:
            examples: 추가할 예시 리스트
        """
        # 전처리 후 추가
        processed = self._process_examples(examples)
        self.default_examples.extend(processed)
        logger.info(f"런타임에 {len(processed)}개 예시 추가")