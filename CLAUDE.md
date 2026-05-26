# CLAUDE.md

## Project: Jira Sprint Management Automation

`jira-sprint-mgmt` — Automated weekly Jira sprint lifecycle management tool.

### Technology Stack

- **Language**: Python 3.11+
- **Primary Library**: `requests` (HTTP client for Jira REST API)
- **Automation**: GitHub Actions (scheduled workflow)
- **API**: Jira REST API v1.0 (Agile endpoints)

### Architecture

```
jira-sprint-mgmt/
├── scripts/
│   └── sprint_manager.py     # Main automation script
├── .github/workflows/
│   └── sprint-rotation.yml   # GitHub Actions workflow (runs Monday 9 AM PST)
├── requirements.txt          # Python dependencies
└── README.md                 # Comprehensive setup & usage guide
```

### Key Components

#### sprint_manager.py

- **JiraConfig**: Loads configuration from environment variables (JIRA_BASE_URL, JIRA_EMAIL, JIRA_API_TOKEN, JIRA_BOARD_ID)
- **JiraSprintManager**: Core business logic
  - `_get_active_sprints()`: Fetch active sprints from board
  - `_close_sprint()`: Close a sprint (moves incomplete issues to backlog)
  - `_create_sprint()`: Create new sprint with auto-calculated dates
  - `_generate_sprint_name()`: Generate ISO week-based name (Sprint YYYY-WXX)
  
- Sprint naming: ISO week format (e.g., "Sprint 2026-W22")
- Sprint duration: 7 days (Monday to Sunday)
- CLI interface: Supports `--dry-run`, `--base-url`, `--email`, `--api-token`, `--board-id`

#### sprint-rotation.yml

- Runs on schedule: Every Monday at 17:00 UTC (09:00 PST)
- Manual trigger support via GitHub UI
- Python 3.11 environment with cached pip dependencies
- Optional Slack notifications on success/failure

### Development Notes

- **Error Handling**: Comprehensive try-catch with detailed logging
- **Logging**: Timestamped log messages with severity levels (INFO, WARN, SUCCESS, ERROR)
- **Authentication**: HTTP Basic Auth with Base64-encoded credentials
- **Date Handling**: Uses `datetime` module; all calculations in UTC
- **Dry Run Mode**: Preview changes without applying (`--dry-run` flag)

### Configuration for GitHub Actions

Required Secrets:
1. `JIRA_BASE_URL` — Jira instance URL (e.g., https://company.atlassian.net)
2. `JIRA_EMAIL` — Jira account email
3. `JIRA_API_TOKEN` — API token from https://id.atlassian.com/manage-profile/security/api-tokens
4. `JIRA_BOARD_ID` — Scrum board ID (find in URL: /boards/{ID})

Optional Secrets:
- `SLACK_WEBHOOK_URL` — For Slack notifications

### Common Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Test with dry-run (no changes)
python scripts/sprint_manager.py --dry-run

# Run with environment variables
JIRA_BASE_URL=... JIRA_EMAIL=... JIRA_API_TOKEN=... JIRA_BOARD_ID=... \
  python scripts/sprint_manager.py

# Run with CLI arguments
python scripts/sprint_manager.py --base-url https://... --email ... --api-token ... --board-id 123
```

### Notes for Future Work

- Cron schedule is in UTC; adjust in workflow if timezone changes needed
- To support multiple boards: create separate workflow files with different JIRA_BOARD_ID Secrets
- To customize sprint name format: modify `_generate_sprint_name()` method
- To change sprint duration: adjust `SPRINT_DURATION_DAYS` constant
