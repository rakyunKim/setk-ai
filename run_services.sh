#!/bin/bash

echo "🚀 세부능력 특기사항 생성 서비스 시작"
echo "=================================="

# LangGraph Server 시작 (백그라운드)
echo "1. LangGraph Server 시작 중..."
langgraph up &
LANGGRAPH_PID=$!

# LangGraph Server가 준비될 때까지 대기
echo "   LangGraph Server 빌드 및 초기화 대기 중..."
sleep 10  # 빌드 시간을 고려해서 더 길게 대기

# 헬스 체크 (더 긴 간격으로 시도)
echo "   LangGraph Server 상태 확인 중..."
RETRY_COUNT=0
MAX_RETRIES=30  # 최대 1분 대기

until curl -s http://localhost:8123/health > /dev/null 2>&1; do
    RETRY_COUNT=$((RETRY_COUNT + 1))
    if [ $RETRY_COUNT -ge $MAX_RETRIES ]; then
        echo "   ❌ LangGraph Server 시작 실패 (시간 초과)"
        kill $LANGGRAPH_PID 2>/dev/null
        exit 1
    fi
    echo "   대기 중... ($RETRY_COUNT/$MAX_RETRIES)"
    sleep 3
done
echo "   ✅ LangGraph Server 준비 완료 (http://localhost:8123)"

# Proxy API 서버 시작
echo ""
echo "2. Proxy API Server 시작 중..."
cd /Users/rock/Desktop/대모산개발단/setk_ai
python -m uvicorn src.api.proxy_api:app --host 0.0.0.0 --port 8000 &
API_PID=$!

# API Server가 준비될 때까지 대기
echo "   API Server 초기화 대기 중..."
sleep 3

RETRY_COUNT=0
MAX_RETRIES=15  # 최대 30초 대기

until curl -s http://localhost:8000/health > /dev/null 2>&1; do
    RETRY_COUNT=$((RETRY_COUNT + 1))
    if [ $RETRY_COUNT -ge $MAX_RETRIES ]; then
        echo "   ❌ API Server 시작 실패 (시간 초과)"
        kill $LANGGRAPH_PID $API_PID 2>/dev/null
        exit 1
    fi
    echo "   대기 중... ($RETRY_COUNT/$MAX_RETRIES)"
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