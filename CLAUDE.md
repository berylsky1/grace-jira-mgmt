# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

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
  - `_get_incomplete_issue_keys()`: Fetch keys of non-done issues from a sprint (paginated)
  - `_create_sprint()`: Create new sprint in future state with auto-calculated dates
  - `_move_issues_to_sprint()`: Bulk-move issue keys to a sprint (batches of 50)
  - `_close_sprint()`: Close a sprint
  - `_start_sprint()`: Transition a future sprint to active
  - `_generate_sprint_name()`: Generate name in `Postdoc.YYYY.MM.Xth` format

#### Sprint Rotation Flow

Mirrors the Jira UI "Move open work items to: New Sprint" behavior:
1. Collect incomplete (non-done) issues from active sprint
2. Create new sprint in **future** state
3. Move incomplete issues to new sprint
4. Close old sprint
5. Start new sprint → becomes active

#### Sprint Naming

Format: `Postdoc.YYYY.MM.Xth` (e.g., `Postdoc.2026.05.5th`)

Week-of-month calculation: `(day - 1 + weekday_of_month_start) // 7 + 1`
This counts partial weeks at the start of the month as week 1.

#### Sprint Dates

- Start: Monday of the current week
- End: Sunday of the same week (start + 6 days)
- Duration: 7 days

#### sprint-rotation.yml

- Runs on schedule: Every Monday at 17:00 UTC (09:00 PST)
- Manual trigger support via `workflow_dispatch`
- Python 3.11 environment with cached pip dependencies

### Configuration for GitHub Actions

Required Secrets:
1. `JIRA_BASE_URL` — Jira instance URL (e.g., https://company.atlassian.net)
2. `JIRA_EMAIL` — Jira account email
3. `JIRA_API_TOKEN` — API token from https://id.atlassian.com/manage-profile/security/api-tokens
4. `JIRA_BOARD_ID` — Scrum board ID (find in URL: /boards/{ID})

### Common Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Test with dry-run (no changes applied)
python scripts/sprint_manager.py --dry-run

# Run with environment variables
JIRA_BASE_URL=... JIRA_EMAIL=... JIRA_API_TOKEN=... JIRA_BOARD_ID=... \
  python scripts/sprint_manager.py

# Run with CLI arguments
python scripts/sprint_manager.py --base-url https://... --email ... --api-token ... --board-id 123
```

### Notes

- Cron schedule is in UTC; adjust in workflow if timezone changes needed
- To support multiple boards: create separate workflow files with different `JIRA_BOARD_ID` secrets
- To customize sprint name format: modify `_generate_sprint_name()`
- To change sprint duration: adjust `_get_sprint_dates()` and `SPRINT_DURATION_DAYS`
- Issue "done" status is determined by `statusCategory.key == "done"` in Jira's status model
