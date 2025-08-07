"""프롬프트 템플릿 모음
"""

# 시스템 프롬프트
SYSTEM_PROMPT = """Be a helpful assistant"""

# 세부능력 특기사항 생성 프롬프트
GENERATE_DETAILED_RECORD_PROMPT = """
다음 학생의 2학기 세부능력 및 특기사항을 작성해주세요.

학생 정보:
- 이름: {name}
- 번호: {student_number}
- 과목: {subject_name}
- 2학기 중간 수행평가: {midterm_score}점
- 2학기 기말 수행평가: {final_score}점

추가사항:
{additional_notes}

작성 지침:
1. 학생의 성취도와 수행평가 결과를 구체적으로 언급하세요
2. 학습 태도와 발전 가능성을 포함하세요
3. 추가사항이 있다면 반드시 포함하세요
4. 300-500자 내외로 작성하세요
5. 교육적이고 긍정적인 톤으로 작성하세요
"""

# 입력 정보 검증 프롬프트
VALIDATE_INPUT_PROMPT = """
생성된 세부능력 특기사항을 검토하여 선생님이 입력한 정보가 포함되어 있는지 확인해주세요.

선생님 입력 정보:
- 학생 이름: {name}
- 학생 번호: {student_number} 
- 과목명: {subject_name}
- 2학기 중간 수행평가: {midterm_score}점
- 2학기 기말 수행평가: {final_score}점
- 추가사항: {additional_notes}

생성된 세특:
{generated_content}

검증 규칙:
1. 학생 이름과 과목명은 반드시 포함되어야 함
2. 학생 번호는 포함되지 않아도 됨 (항상 true로 반환)
3. 중간/기말 점수는 반드시 포함되어야 함
4. 추가사항이 "없음"이 아닌 경우에만 확인, "없음"이면 항상 true로 반환
5. 점수는 "50점", "50점을 기록", "50점 획득", "모두 50점" 등 다양한 표현 모두 인정

다음 형식의 JSON만 응답하세요 (설명 없이):
{{
    "is_valid": true/false,
    "missing_items": [],
    "validation_details": {{
        "name_included": true/false,
        "student_number_included": true,
        "subject_included": true/false,
        "midterm_score_included": true/false,
        "final_score_included": true/false,
        "additional_notes_included": true/false
    }}
}}
"""

# 문법 및 어휘 검증 프롬프트
GRAMMAR_AND_VOCABULARY_CHECK_PROMPT = """
다음 세부능력 특기사항의 문법과 어휘를 검토해주세요.

생성된 세특:
{generated_content}

점검 기준:
1. 문법: 문장 구조, 조사, 어미가 올바른지
2. 어휘: 교육 문서에 적절한 어휘 사용 여부
3. 맞춤법: 철자 오류가 없는지
4. 가독성: 문장이 자연스럽고 이해하기 쉬운지
5. 톤: 교육적이고 전문적인 톤 유지 여부
6. 부적절한 표현: 비속어, 은어, 부정적 표현 등이 없는지

**중요: 반드시 아래 JSON 형식으로만 응답하세요. 다른 설명이나 텍스트는 포함하지 마세요.**
**중요: 문제가 없으면 is_valid를 true로 반환하세요.**
**중요: 확실한 문제가 아니라면 문제가 없다고 판단하세요.**

{{
    "is_valid": true 또는 false,
    "issues": [
        {{
            "type": "grammar 또는 vocabulary 또는 spelling 또는 inappropriate",
            "text": "문제가 있는 부분",
            "suggestion": "수정 제안",
            "severity": "high 또는 medium 또는 low"
        }}
    ],
    "check_details": {{
        "grammar_correct": true 또는 false,
        "vocabulary_appropriate": true 또는 false,
        "spelling_correct": true 또는 false,
        "readability_good": true 또는 false,
        "tone_appropriate": true 또는 false,
        "no_inappropriate_words": true 또는 false
    }},
    "overall_quality": "excellent 또는 good 또는 fair 또는 poor",
    "suggestions": "전체적인 개선 제안사항"
}}
"""

# 문법 수정 재생성 프롬프트
FIX_GRAMMAR_PROMPT = """
다음 세부능력 특기사항의 문법과 어휘 문제를 수정해주세요.

현재 세특:
{current_content}

발견된 문제들:
{grammar_issues}

수정 지침:
1. 위에 나열된 문법 문제들을 모두 수정하세요
2. 원본 내용의 의미는 최대한 유지하세요
3. 교육 문서에 적절한 어휘와 톤을 사용하세요
4. 자연스럽고 읽기 쉬운 문장으로 수정하세요
5. 전체적인 구조와 길이는 유지하세요

수정된 세특을 작성해주세요:
"""