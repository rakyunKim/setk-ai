#!/bin/bash

# ================= 설정 변수 =================
# 테스트할 API의 전체 URL
URL="http://localhost:8000/api/v1/generate"
# 총 요청 횟수
REQUEST_COUNT=50
# 요청 시 보낼 JSON 데이터
JSON_DATA=$(cat <<EOF
{
    "student_id": 10,
    "name": "강감찬",
    "subject": "화학",
    "midterm_score": 0,
    "final_score": 0,
    "additional_notes": "수업에 좀 더 집중할 필요가 있어 보임",
    "semester": 1,
    "academic_year": 2025
}
EOF
)
# ===========================================

echo "🚀 API 성능 측정을 시작합니다..."
echo " - 대상 URL: $URL"
echo " - 총 요청 횟수: $REQUEST_COUNT"
echo "------------------------------------------"

# 변수 초기화
max_time=0.0
slowest_request_number=0
total_time=0.0 # [추가] 전체 시간을 더해갈 변수

# 지정된 횟수만큼 반복 실행
for ((i=1; i<=REQUEST_COUNT; i++))
do
    time_taken=$(curl -s -o /dev/null -w '%{time_total}' \
        -X POST \
        -H "Content-Type: application/json" \
        -d "$JSON_DATA" \
        "$URL")

    echo "[$i/$REQUEST_COUNT] 요청 완료. 소요 시간: ${time_taken}s"

    # [추가] 현재 요청 시간을 전체 시간에 더함
    # 쉘은 소수점 계산을 못하므로 bc 계산기 사용
    total_time=$(echo "$total_time + $time_taken" | bc)

    # 현재 소요 시간이 기록된 최대 시간보다 긴지 비교
    is_slower=$(awk -v t1="$time_taken" -v t2="$max_time" 'BEGIN{print (t1>t2)}')
    if [ "$is_slower" -eq 1 ]; then
        max_time=$time_taken
        slowest_request_number=$i
    fi
done

# [추가] 평균 시간 계산
# bc 계산기에서 나눗셈을 위해 소수점 자릿수(scale) 설정
average_time=$(echo "scale=4; $total_time / $REQUEST_COUNT" | bc)

echo "------------------------------------------"
echo "✅ 성능 측정이 완료되었습니다."
echo ""
echo "🏆 가장 오래 걸린 요청:"
echo " - 요청 번호: $slowest_request_number"
echo " - 소요 시간: ${max_time}s"
echo ""
echo "📊 전체 요청 요약:" # [추가] 평균 시간 출력
echo " - 평균 소요 시간: ${average_time}s"
echo ""
