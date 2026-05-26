# Jira Sprint Management Automation

자동으로 매주 Jira 스프린트를 관리합니다:
1. 지난주 스프린트 종료 (close)
2. 이번 주 새 스프린트 생성

## 기능

- **자동 스프린트 순환**: 매주 월요일 09:00 PST (17:00 UTC)에 자동 실행
- **명확한 로깅**: 각 단계별 상세한 실행 로그
- **에러 핸들링**: API 실패 시 상세한 에러 메시지
- **드라이런 모드**: 실제 변경 없이 미리 확인 가능
- **CLI 지원**: 로컬에서도 수동 실행 가능
- **Slack 알림**: 성공/실패 시 Slack 채널에 알림 (선택사항)

## 설치

### 1. 리포지토리 클론 또는 코드 복사

```bash
git clone https://github.com/your-org/jira-sprint-mgmt.git
cd jira-sprint-mgmt
```

### 2. Python 의존성 설치

```bash
python -m pip install -r requirements.txt
```

### 3. 로컬 환경변수 설정 (선택사항)

`.env` 파일을 생성하여 개발/테스트할 때 사용:

```bash
export JIRA_BASE_URL="https://your-instance.atlassian.net"
export JIRA_EMAIL="your-email@company.com"
export JIRA_API_TOKEN="your-api-token"
export JIRA_BOARD_ID="123"
```

## GitHub Actions 설정

### Step 1: GitHub Secrets 추가

리포지토리의 Settings → Secrets and variables → Actions에서 다음 4개의 Secrets를 추가합니다:

| Secret 이름 | 설명 | 예시 |
|-----------|------|------|
| `JIRA_BASE_URL` | Jira 인스턴스의 기본 URL | `https://company.atlassian.net` |
| `JIRA_EMAIL` | Jira 계정의 이메일 | `your-email@company.com` |
| `JIRA_API_TOKEN` | Jira API 토큰 | (아래 참조) |
| `JIRA_BOARD_ID` | Scrum 보드 ID | `123` |

### Step 2: Jira API 토큰 생성

1. [Atlassian 계정 관리](https://id.atlassian.com/manage-profile/security/api-tokens)에 로그인
2. **Create API token** 클릭
3. 토큰 이름 입력 (예: "GitHub Actions Sprint Manager")
4. **Create** 클릭
5. 생성된 토큰을 복사해 GitHub Secret에 저장

> ⚠️ **주의**: API 토큰은 비밀이므로 다시 확인할 수 없습니다. 안전한 곳에 저장해두세요.

### Step 3: Slack 알림 (선택사항)

Slack 채널로 성공/실패 알림을 받으려면:

1. Slack 워크스페이스의 설정에서 Incoming Webhooks 생성
2. 리포지토리 Secrets에 `SLACK_WEBHOOK_URL` 추가
3. GitHub Actions workflow에서 자동으로 알림이 발송됩니다

## Jira 보드 ID 찾는 방법

### 방법 1: Jira URL에서 확인
1. Jira 인스턴스에서 Scrum 보드 열기
2. URL 확인: `https://your-instance.atlassian.net/software/c/projects/PROJ/boards/123`
3. `boards/` 뒤의 숫자가 보드 ID (예: `123`)

### 방법 2: Jira REST API 사용
```bash
curl -u "email@example.com:api_token" \
  "https://your-instance.atlassian.net/rest/agile/1.0/board" \
  | jq '.values[] | {id, name}'
```

## 로컬 실행

### 드라이런 (변경 없이 미리보기)

```bash
python scripts/sprint_manager.py --dry-run
```

출력 예시:
```
[2026-05-26 09:00:00] INFO: Starting sprint rotation
[2026-05-26 09:00:00] INFO: ======================================================================
[2026-05-26 09:00:00] INFO: Board: Engineering (ID: 123)
[2026-05-26 09:00:00] INFO: Found 1 active sprint(s)
[2026-05-26 09:00:00] INFO: Closing sprint: Sprint 2026-W20 (ID: 456)
[2026-05-26 09:00:00] WARN: DRY RUN: Would close sprint
[2026-05-26 09:00:00] INFO: Creating new sprint: Sprint 2026-W21
[2026-05-26 09:00:00] INFO:   Start: 2026-05-26, End: 2026-06-01
[2026-05-26 09:00:00] WARN: DRY RUN: Would create sprint with payload:
```

### 실제 실행

환경변수 설정 후:

```bash
python scripts/sprint_manager.py
```

또는 CLI 인자로 전달:

```bash
python scripts/sprint_manager.py \
  --base-url "https://your-instance.atlassian.net" \
  --email "your-email@company.com" \
  --api-token "your-api-token" \
  --board-id 123
```

## 스프린트 이름 형식

기본적으로 **ISO 주차 번호** 형식을 사용합니다:

```
Sprint YYYY-WXX
```

예시:
- `Sprint 2026-W22` (2026년 22주)
- `Sprint 2026-W01` (2026년 첫 주)

이 형식은 다음과 같은 장점이 있습니다:
- **국제 표준**: ISO 8601 준수
- **정렬 용이**: 알파벳순 정렬 = 시간 순서
- **간결함**: 한눈에 주차 파악

## 스프린트 설정

### 스프린트 기간

- **시작일**: 월요일 (주의 첫날)
- **종료일**: 일요일 (주의 마지막날)
- **기간**: 7일 (월요일~일요일)

> 기간을 변경하려면 `sprint_manager.py`에서 `SPRINT_DURATION_DAYS` 값을 수정하세요.

### 미완료 이슈 처리

현재 설정:
- **미완료 이슈**: 스프린트 종료 시 백로그로 자동 이동
- Jira 기본 설정에 따라 동작합니다

설정 변경이 필요하면 이슈를 생성해 주세요.

## 트러블슈팅

### 1. "Missing required environment variables"

**원인**: 필요한 환경변수가 설정되지 않았습니다.

**해결**:
```bash
# 모든 필수 환경변수 확인
echo $JIRA_BASE_URL
echo $JIRA_EMAIL
echo $JIRA_API_TOKEN
echo $JIRA_BOARD_ID

# GitHub Actions에서는 Settings → Secrets에서 확인
```

### 2. "Failed to fetch active sprints: 401"

**원인**: API 인증 실패 (토큰 오류)

**해결**:
1. API 토큰이 올바른지 확인
2. API 토큰이 만료되지 않았는지 확인
3. 새 토큰 생성 후 GitHub Secret 업데이트

### 3. "Failed to fetch board info: 403"

**원인**: 권한 부족

**해결**:
1. Jira 계정이 해당 보드에 대한 관리자 권한이 있는지 확인
2. 프로젝트 설정에서 권한 검토

### 4. "No active sprints found"

**원인**: 현재 활성 스프린트가 없습니다.

**상황**:
- 모든 스프린트가 이미 종료됨
- 새 스프린트가 아직 시작되지 않음

**해결**: 스크립트가 자동으로 새 스프린트를 생성합니다.

### 5. GitHub Actions 스케줄이 실행되지 않음

**원인**: GitHub Actions가 비활성화되어 있거나 스케줄이 잘못됨

**해결**:
1. 리포지토리 Settings → Actions → General에서 "Allow all actions and reusable workflows" 확인
2. Workflow 파일의 cron 표현식 검증
3. 테스트: GitHub UI에서 "Run workflow" → "Run workflow"로 수동 실행

## 개발 및 기여

### 로컬 테스트

```bash
# 가상환경 생성 (선택사항)
python -m venv venv
source venv/bin/activate  # macOS/Linux
# venv\Scripts\activate  # Windows

# 의존성 설치
pip install -r requirements.txt

# 드라이런으로 테스트
python scripts/sprint_manager.py --dry-run
```

### 코드 개선

이슈나 PR을 통해 다음 개선사항을 제안해주세요:
- 추가 스프린트 이름 형식 지원
- 커스텀 스프린트 기간 설정
- 이슈 이동 방식 선택 옵션
- 추가 알림 채널 지원

## FAQ

**Q: 스프린트를 수동으로 실행하고 싶습니다.**

A: GitHub Actions에서 "Run workflow" 버튼을 클릭하거나 로컬에서 `python scripts/sprint_manager.py`를 실행하세요.

**Q: 다른 시간에 실행하고 싶습니다.**

A: `.github/workflows/sprint-rotation.yml`에서 `cron` 값을 변경하세요. UTC 기준입니다.

```yaml
schedule:
  - cron: '0 13 * * 1'  # 월요일 13:00 UTC (동부 표준시 08:00)
```

**Q: 여러 보드를 관리하고 싶습니다.**

A: 각 보드별로 다른 `JIRA_BOARD_ID` Secrets를 사용하는 workflow를 별도로 생성하세요.

**Q: 스프린트 이름 형식을 바꾸고 싶습니다.**

A: `scripts/sprint_manager.py`에서 `_generate_sprint_name()` 메서드를 수정하세요.

예시 (날짜 범위 형식):
```python
def _generate_sprint_name(self, start_date: datetime) -> str:
    """Generate sprint name using date range: Sprint YYYY-MM-DD ~ YYYY-MM-DD"""
    end_date = start_date + timedelta(days=self.SPRINT_DURATION_DAYS - 1)
    return f"Sprint {start_date.strftime('%Y-%m-%d')} ~ {end_date.strftime('%Y-%m-%d')}"
```

## 라이센스

MIT License

## 지원

질문이나 문제가 있으면 이슈를 생성하세요.
