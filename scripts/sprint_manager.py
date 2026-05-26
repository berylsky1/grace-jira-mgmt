#!/usr/bin/env python3
"""
Jira Sprint Lifecycle Manager

Automates the weekly sprint rotation:
1. Closes the previous week's sprint
2. Creates a new sprint for the current week

Usage:
    python scripts/sprint_manager.py                 # Use environment variables
    python scripts/sprint_manager.py --dry-run       # Preview changes without applying
    python scripts/sprint_manager.py --help          # Show usage
"""

import os
import sys
import json
import base64
import argparse
import requests
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from dataclasses import dataclass


@dataclass
class JiraConfig:
    """Jira configuration from environment or arguments"""
    base_url: str
    email: str
    api_token: str
    board_id: int

    @classmethod
    def from_env(cls) -> "JiraConfig":
        """Load configuration from environment variables"""
        base_url = os.getenv("JIRA_BASE_URL")
        email = os.getenv("JIRA_EMAIL")
        api_token = os.getenv("JIRA_API_TOKEN")
        board_id = os.getenv("JIRA_BOARD_ID")

        if not all([base_url, email, api_token, board_id]):
            raise ValueError(
                "Missing required environment variables: "
                "JIRA_BASE_URL, JIRA_EMAIL, JIRA_API_TOKEN, JIRA_BOARD_ID"
            )

        return cls(
            base_url=base_url.rstrip("/"),
            email=email,
            api_token=api_token,
            board_id=int(board_id),
        )

    def get_auth_header(self) -> Dict[str, str]:
        """Generate Basic Auth header for Jira API"""
        credentials = base64.b64encode(
            f"{self.email}:{self.api_token}".encode()
        ).decode()
        return {"Authorization": f"Basic {credentials}"}


class JiraSprintManager:
    """Manages Jira sprints: closing and creating"""

    API_VERSION = "1.0"
    SPRINT_DURATION_DAYS = 7  # Monday to Sunday

    def __init__(self, config: JiraConfig, dry_run: bool = False):
        self.config = config
        self.dry_run = dry_run
        self.base_api_url = f"{config.base_url}/rest/agile/{self.API_VERSION}"
        self.session = self._create_session()

    def _create_session(self) -> requests.Session:
        """Create requests session with auth headers"""
        session = requests.Session()
        auth_header = self.config.get_auth_header()
        session.headers.update(auth_header)
        session.headers.update({"Content-Type": "application/json"})
        return session

    def log(self, message: str, level: str = "INFO") -> None:
        """Print formatted log message"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] {level}: {message}")

    def _get_active_sprints(self) -> list[Dict[str, Any]]:
        """Fetch active sprints from the board"""
        url = f"{self.base_api_url}/board/{self.config.board_id}/sprint"
        params = {"state": "active"}

        try:
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            sprints = response.json().get("values", [])
            self.log(f"Found {len(sprints)} active sprint(s)")
            return sprints
        except requests.RequestException as e:
            raise RuntimeError(f"Failed to fetch active sprints: {e}")

    def _get_board_info(self) -> Dict[str, Any]:
        """Fetch board information"""
        url = f"{self.base_api_url}/board/{self.config.board_id}"

        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            raise RuntimeError(f"Failed to fetch board info: {e}")

    def _close_sprint(self, sprint_id: int, sprint_name: str) -> bool:
        """Close an active sprint"""
        url = f"{self.base_api_url}/sprint/{sprint_id}"
        payload = {"state": "closed"}

        self.log(f"Closing sprint: {sprint_name} (ID: {sprint_id})")

        if self.dry_run:
            self.log("DRY RUN: Would close sprint", "WARN")
            return True

        try:
            response = self.session.post(url, json=payload, timeout=10)
            response.raise_for_status()
            self.log(f"Successfully closed sprint: {sprint_name}", "SUCCESS")
            return True
        except requests.RequestException as e:
            self.log(f"Failed to close sprint {sprint_name}: {e}", "ERROR")
            return False

    def _get_iso_week_number(self, date: datetime) -> int:
        """Get ISO week number from date"""
        return date.isocalendar()[1]

    def _get_sprint_dates(self) -> tuple[datetime, datetime]:
        """Calculate sprint start (Monday) and end (Sunday) dates"""
        today = datetime.now()
        # Find Monday of current week
        monday = today - timedelta(days=today.weekday())
        # Sunday is 6 days after Monday
        sunday = monday + timedelta(days=6)
        return monday, sunday

    def _generate_sprint_name(self, start_date: datetime) -> str:
        """Generate sprint name: Postdoc.YYYY.MM.Xth"""
        year = start_date.year
        month = start_date.month
        first_of_month = start_date.replace(day=1)
        week_of_month = (start_date.day - 1 + first_of_month.weekday()) // 7 + 1
        ordinals = {1: "1st", 2: "2nd", 3: "3rd", 4: "4th", 5: "5th"}
        week_str = ordinals.get(week_of_month, f"{week_of_month}th")
        return f"Postdoc.{year}.{month:02d}.{week_str}"

    def _create_sprint(self, sprint_name: str, start_date: datetime, end_date: datetime) -> Optional[Dict[str, Any]]:
        """Create a new sprint"""
        url = f"{self.base_api_url}/sprint"

        # Format dates as ISO 8601 (YYYY-MM-DD)
        start_str = start_date.strftime("%Y-%m-%d")
        end_str = end_date.strftime("%Y-%m-%d")

        payload = {
            "name": sprint_name,
            "startDate": start_str,
            "endDate": end_str,
            "originBoardId": self.config.board_id,
            "goal": f"Weekly sprint for week {self._get_iso_week_number(start_date)}, {start_date.year}",
        }

        self.log(f"Creating new sprint: {sprint_name}")
        self.log(f"  Start: {start_str}, End: {end_str}")

        if self.dry_run:
            self.log("DRY RUN: Would create sprint with payload:", "WARN")
            self.log(json.dumps(payload, indent=2), "WARN")
            return {
                "id": 99999,
                "name": sprint_name,
                "startDate": start_str,
                "endDate": end_str,
            }

        try:
            response = self.session.post(url, json=payload, timeout=10)
            response.raise_for_status()
            sprint = response.json()
            self.log(f"Successfully created sprint: {sprint_name} (ID: {sprint['id']})", "SUCCESS")
            return sprint
        except requests.RequestException as e:
            self.log(f"Failed to create sprint: {e}", "ERROR")
            return None

    def _get_incomplete_issue_keys(self, sprint_id: int) -> list[str]:
        """Fetch keys of all incomplete (not done) issues in a sprint"""
        url = f"{self.base_api_url}/sprint/{sprint_id}/issue"
        issue_keys = []
        start_at = 0

        while True:
            try:
                response = self.session.get(url, params={"startAt": start_at, "maxResults": 100}, timeout=10)
                response.raise_for_status()
                data = response.json()
                issues = data.get("issues", [])
                for issue in issues:
                    status_category = issue.get("fields", {}).get("status", {}).get("statusCategory", {}).get("key", "")
                    if status_category != "done":
                        issue_keys.append(issue["key"])
                total = data.get("total", 0)
                start_at += len(issues)
                if start_at >= total or not issues:
                    break
            except requests.RequestException as e:
                raise RuntimeError(f"Failed to fetch sprint issues: {e}")

        return issue_keys

    def _move_issues_to_sprint(self, sprint_id: int, issue_keys: list[str]) -> bool:
        """Move a list of issues to a sprint"""
        if not issue_keys:
            return True

        url = f"{self.base_api_url}/sprint/{sprint_id}/issue"

        if self.dry_run:
            self.log(f"DRY RUN: Would move {len(issue_keys)} issue(s): {issue_keys}", "WARN")
            return True

        for i in range(0, len(issue_keys), 50):
            batch = issue_keys[i:i + 50]
            try:
                response = self.session.post(url, json={"issues": batch}, timeout=10)
                response.raise_for_status()
            except requests.RequestException as e:
                self.log(f"Failed to move issues {batch}: {e}", "ERROR")
                return False

        return True

    def _start_sprint(self, sprint_id: int, sprint_name: str, start_date: datetime, end_date: datetime) -> bool:
        """Transition a future sprint to active"""
        url = f"{self.base_api_url}/sprint/{sprint_id}"
        payload = {
            "state": "active",
            "startDate": start_date.strftime("%Y-%m-%dT00:00:00.000+0000"),
            "endDate": end_date.strftime("%Y-%m-%dT00:00:00.000+0000"),
        }

        self.log(f"Starting sprint: {sprint_name} (ID: {sprint_id})")

        if self.dry_run:
            self.log("DRY RUN: Would start sprint", "WARN")
            return True

        try:
            response = self.session.post(url, json=payload, timeout=10)
            response.raise_for_status()
            self.log(f"Successfully started sprint: {sprint_name}", "SUCCESS")
            return True
        except requests.RequestException as e:
            self.log(f"Failed to start sprint {sprint_name}: {e}", "ERROR")
            return False

    def run(self) -> bool:
        """Sprint rotation flow (mirrors Jira UI 'Move open work items to: New Sprint'):
        1. Create new sprint (future)
        2. Move incomplete issues to new sprint
        3. Close old sprint
        4. Start new sprint
        """
        try:
            self.log("Starting sprint rotation")
            self.log("=" * 70)

            board_info = self._get_board_info()
            self.log(f"Board: {board_info.get('name')} (ID: {self.config.board_id})")

            active_sprints = self._get_active_sprints()

            # Collect incomplete issues from active sprint(s)
            incomplete_issue_keys = []
            if active_sprints:
                for sprint in active_sprints:
                    keys = self._get_incomplete_issue_keys(sprint["id"])
                    incomplete_issue_keys.extend(keys)
                    self.log(f"Found {len(keys)} incomplete issue(s) in '{sprint['name']}' to carry over")

            # Step 1: Create new sprint (future state)
            start_date, end_date = self._get_sprint_dates()
            sprint_name = self._generate_sprint_name(start_date)
            new_sprint = self._create_sprint(sprint_name, start_date, end_date)
            if not new_sprint:
                return False

            # Step 2: Move incomplete issues to new sprint
            if incomplete_issue_keys:
                self.log(f"Moving {len(incomplete_issue_keys)} incomplete issue(s) to '{sprint_name}'...")
                if self._move_issues_to_sprint(new_sprint["id"], incomplete_issue_keys):
                    self.log(f"Successfully moved {len(incomplete_issue_keys)} issue(s) to new sprint", "SUCCESS")
                else:
                    self.log("Some issues could not be moved — check manually", "WARN")

            # Step 3: Close old sprint(s)
            if not active_sprints:
                self.log("No active sprints found. Skipping close step.", "WARN")
            elif len(active_sprints) > 1:
                self.log(f"WARNING: Found {len(active_sprints)} active sprints. Closing all.", "WARN")
                for sprint in active_sprints:
                    if not self._close_sprint(sprint["id"], sprint["name"]):
                        return False
            else:
                if not self._close_sprint(active_sprints[0]["id"], active_sprints[0]["name"]):
                    return False

            # Step 4: Start new sprint
            if not self._start_sprint(new_sprint["id"], sprint_name, start_date, end_date):
                return False

            self.log("=" * 70)
            self.log("Sprint rotation completed successfully!", "SUCCESS")

            print("\n" + "=" * 70)
            print("SUMMARY")
            print("=" * 70)
            if active_sprints:
                print(f"Closed Sprint:    {active_sprints[0]['name']}")
            print(f"New Sprint:       {sprint_name}")
            print(f"Sprint Duration:  {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
            print(f"Carried Over:     {len(incomplete_issue_keys)} issue(s)")
            print("=" * 70 + "\n")

            return True

        except Exception as e:
            self.log(f"Unexpected error: {e}", "ERROR")
            return False


def main():
    """CLI entry point"""
    parser = argparse.ArgumentParser(
        description="Jira Sprint Lifecycle Manager - Weekly sprint rotation"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without applying them",
    )
    parser.add_argument(
        "--base-url",
        help="Jira base URL (or use JIRA_BASE_URL env var)",
    )
    parser.add_argument(
        "--email",
        help="Jira account email (or use JIRA_EMAIL env var)",
    )
    parser.add_argument(
        "--api-token",
        help="Jira API token (or use JIRA_API_TOKEN env var)",
    )
    parser.add_argument(
        "--board-id",
        type=int,
        help="Jira board ID (or use JIRA_BOARD_ID env var)",
    )

    args = parser.parse_args()

    # Override environment variables with CLI arguments if provided
    if args.base_url:
        os.environ["JIRA_BASE_URL"] = args.base_url
    if args.email:
        os.environ["JIRA_EMAIL"] = args.email
    if args.api_token:
        os.environ["JIRA_API_TOKEN"] = args.api_token
    if args.board_id:
        os.environ["JIRA_BOARD_ID"] = str(args.board_id)

    try:
        config = JiraConfig.from_env()
        manager = JiraSprintManager(config, dry_run=args.dry_run)
        success = manager.run()
        sys.exit(0 if success else 1)
    except ValueError as e:
        print(f"Configuration Error: {e}", file=sys.stderr)
        print("\nRequired environment variables:", file=sys.stderr)
        print("  - JIRA_BASE_URL: https://your-instance.atlassian.net", file=sys.stderr)
        print("  - JIRA_EMAIL: your-email@company.com", file=sys.stderr)
        print("  - JIRA_API_TOKEN: your-api-token", file=sys.stderr)
        print("  - JIRA_BOARD_ID: 123", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
