#!/bin/bash

# ================= 설정 변수 =================
URL="http://localhost:8000/api/v1/generate-batch"
REQUEST_COUNT=50
JSON_DATA=$(cat <<EOF
[
    { "student_id": 1, "name": "유관순", "subject": "국어", "midterm_score": 100, "final_score": 100, "additional_notes": "책임감이 강하고 참을성이 좋음", "semester": 1, "academic_year": 2025 },
    { "student_id": 2, "name": "이순신", "subject": "국어", "midterm_score": 20, "final_score": 30, "additional_notes": "앉아서 공부하는 것을 잘 못함", "semester": 1, "academic_year": 2025 },
    { "student_id": 3, "name": "세종대왕", "subject": "국어", "midterm_score": 100, "final_score": 100, "additional_notes": "국어에 대한 이해가 완벽하고 학생이 아니라 교수님이라고 착각할 정도로 국어를 잘함", "semester": 1, "academic_year": 2025 },
    { "student_id": 4, "name": "김구", "subject": "국어", "midterm_score": 30, "final_score": 49, "additional_notes": "공부를 열심히 함", "semester": 1, "academic_year": 2025 },
    { "student_id": 5, "name": "바다", "subject": "영어", "midterm_score": 20, "final_score": 30, "additional_notes": "수업 시간에 자주 졸음", "semester": 1, "academic_year": 2025 },
    { "student_id": 6, "name": "산", "subject": "영어", "midterm_score": 30, "final_score": 40, "additional_notes": "하고 싶은 것만 하고 하기 싫은 것은 안 하는 경향이 있음", "semester": 1, "academic_year": 2025 },
    { "student_id": 7, "name": "강", "subject": "체육", "midterm_score": 0, "final_score": 0, "additional_notes": "움직임에 대한 이해가 많이 낮음", "semester": 1, "academic_year": 2025 },
    { "student_id": 8, "name": "태양", "subject": "생활과 윤리", "midterm_score": 12, "final_score": 41, "additional_notes": "열정이 가득함, 열정에 비해 실력은 더 키워야 할 필요가 있음", "semester": 1, "academic_year": 2025 },
    { "student_id": 9, "name": "우주", "subject": "과학", "midterm_score": 100, "final_score": 100, "additional_notes": "우주 과학에 대한 이해가 뛰어남", "semester": 1, "academic_year": 2025 },
    { "student_id": 10, "name": "강감찬", "subject": "화학", "midterm_score": 0, "final_score": 0, "additional_notes": "수업에 좀 더 집중할 필요가 있어 보임", "semester": 1, "academic_year": 2025 }
]
EOF
)
# ===========================================

echo "🚀 API 배치(Batch) 성능 및 유효성 검증을 시작합니다..."
echo " - 대상 URL: $URL"
echo " - 총 요청 횟수: $REQUEST_COUNT"
echo "------------------------------------------"

# 변수 초기화
max_time=0.0
slowest_request_number=0
total_time=0.0
success_count=0 # [고도화] 성공 카운트
failure_count=0 # [고도화] 실패 카운트

# 지정된 횟수만큼 반복 실행
for ((i=1; i<=REQUEST_COUNT; i++))
do
    # [고도화] curl 응답에서 body와 time을 분리하기 위해 개행문자와 함께 출력
    response_with_time=$(curl -s -w "\n%{time_total}" \
        -X POST \
        -H "Content-Type: application/json" \
        -d "$JSON_DATA" \
        "$URL")

    # [고도화] 응답에서 body와 time 분리
    response_body=$(echo "$response_with_time" | sed '$d') # 마지막 줄(시간) 제외
    time_taken=$(echo "$response_with_time" | tail -n 1)   # 마지막 줄(시간)만 가져오기

    # [고도화] 응답 body(JSON 배열)의 요소 개수 확인
    # jq를 사용하고, JSON 파싱 실패 시 에러를 숨기기 위해 2>/dev/null 추가
    item_count=$(echo "$response_body" | jq 'length' 2>/dev/null)

    # 유효성 검증 및 결과 출력
    if [[ "$item_count" -eq 10 ]]; then
        echo "[$i/$REQUEST_COUNT] ✅ 성공. 소요 시간: ${time_taken}s (항목: 10개)"
        success_count=$((success_count + 1))
    else
        # item_count가 숫자가 아닐 경우 (예: JSON 파싱 실패) 0으로 처리
        if ! [[ "$item_count" =~ ^[0-9]+$ ]]; then
            item_count=0
        fi
        echo "[$i/$REQUEST_COUNT] ❌ 실패. 소요 시간: ${time_taken}s (항목: ${item_count}개)"
        failure_count=$((failure_count + 1))
    fi

    # 시간 통계 계산
    total_time=$(echo "$total_time + $time_taken" | bc)
    is_slower=$(awk -v t1="$time_taken" -v t2="$max_time" 'BEGIN{print (t1>t2)}')
    if [ "$is_slower" -eq 1 ]; then
        max_time=$time_taken
        slowest_request_number=$i
    fi
done

# 평균 시간 계산
average_time=$(echo "scale=4; $total_time / $REQUEST_COUNT" | bc)

echo "------------------------------------------"
echo "✅ 성능 및 유효성 검증이 완료되었습니다."
echo ""
echo "📝 검증 결과 요약:"
echo " - 성공 (10개 항목 반환): $success_count 회"
echo " - 실패 (10개 항목 미만): $failure_count 회"
echo ""
echo "🏆 가장 오래 걸린 요청:"
echo " - 요청 번호: $slowest_request_number"
echo " - 소요 시간: ${max_time}s"
echo ""
echo "📊 전체 요청 시간 요약:"
echo " - 평균 소요 시간: ${average_time}s"
echo ""
