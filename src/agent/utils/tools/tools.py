from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

# Tavily 도구 제거 - 실제로 사용하지 않음
# from langchain_community.tools.tavily_search import TavilySearchResults
# tools = [TavilySearchResults(max_results=1)]

# 빈 도구 리스트 (필요시 다른 도구 추가 가능)
tools = []