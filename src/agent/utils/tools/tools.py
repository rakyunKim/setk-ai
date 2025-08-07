from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

from langchain_community.tools.tavily_search import TavilySearchResults

tools = [TavilySearchResults(max_results=1)]