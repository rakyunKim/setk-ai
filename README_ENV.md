# 환경 설정 가이드

## 환경 변수 설정 방식

이 프로젝트는 시스템 환경변수 `ENVIRONMENT`를 통해 실행 환경을 결정합니다.

### 실행 방법

#### 1. 로컬 개발 환경 (기본값)
```bash
# 방법 1: 기본값 사용 (ENVIRONMENT 미지정 시 자동으로 local)
python src/api/proxy_api.py

# 방법 2: 명시적으로 지정
ENVIRONMENT=local python src/api/proxy_api.py

# 방법 3: export 사용
export ENVIRONMENT=local
python src/api/proxy_api.py
```

#### 2. 프로덕션 환경
```bash
# 방법 1: 인라인으로 지정
ENVIRONMENT=production python src/api/proxy_api.py

# 방법 2: export 사용
export ENVIRONMENT=production
python src/api/proxy_api.py
```

### 환경별 설정 파일

- **`.env.local`**: 로컬 개발 환경 설정
  - CORS: 모든 도메인 허용 (`*`)
  - 디버그 모드: 활성화
  - 포트: 8000

- **`.env.production`**: 프로덕션 환경 설정
  - CORS: 특정 도메인만 허용
  - 디버그 모드: 비활성화
  - 포트: 8080

### 주의사항

- `ENVIRONMENT` 변수는 **시스템 환경변수**로만 설정해야 합니다
- `.env` 파일 내부에 `ENVIRONMENT` 변수를 넣지 마세요 (순환 의존성 발생)
- 기본값은 `local`이므로, 개발 시에는 별도 설정 없이 실행 가능합니다

### venv 사용 시 영구 설정

venv를 사용하는 경우, activate 스크립트에 환경변수를 추가할 수 있습니다:

```bash
# venv/bin/activate 파일에 추가
echo 'export ENVIRONMENT=local' >> venv/bin/activate

# venv 재활성화
deactivate
source venv/bin/activate
```