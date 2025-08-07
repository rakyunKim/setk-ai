#!/bin/bash

echo "🚀 세부능력 특기사항 생성 서비스 시작"
echo "=================================="

# LangGraph Server 시작 (백그라운드)
echo "1. LangGraph Server 시작 중..."
langgraph up &
LANGGRAPH_PID=$!

# LangGraph Server가 준비될 때까지 대기
echo "   LangGraph Server 초기화 대기 중..."
sleep 5

# 헬스 체크
until curl -s http://localhost:8123/health > /dev/null 2>&1; do
    sleep 2
done
echo "   ✅ LangGraph Server 준비 완료 (http://localhost:8123)"

# Proxy API 서버 시작
echo ""
echo "2. Proxy API Server 시작 중..."
cd /Users/rock/Desktop/대모산개발단/setk_ai
python -m uvicorn src.api.proxy_api:app --host 0.0.0.0 --port 8000 &
API_PID=$!

# API Server가 준비될 때까지 대기
sleep 3
until curl -s http://localhost:8000/health > /dev/null 2>&1; do
    sleep 2
done
echo "   ✅ API Server 준비 완료 (http://localhost:8000)"

echo ""
echo "=================================="
echo "✨ 모든 서비스가 시작되었습니다!"
echo ""
echo "📍 접속 정보:"
echo "   - API 문서: http://localhost:8000/docs"
echo "   - LangGraph Studio: http://localhost:8123"
echo ""
echo "종료하려면 Ctrl+C를 누르세요."

# 종료 시그널 처리
trap "kill $LANGGRAPH_PID $API_PID 2>/dev/null; exit" SIGINT SIGTERM

# 프로세스 대기
wait