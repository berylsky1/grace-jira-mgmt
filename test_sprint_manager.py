#!/usr/bin/env python3
"""
Unit tests for Jira Sprint Manager

Run with: python -m pytest test_sprint_manager.py -v
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
from scripts.sprint_manager import JiraConfig, JiraSprintManager


class TestJiraConfig:
    """Test JiraConfig class"""

    def test_from_env_valid(self, monkeypatch):
        """Test valid environment variable loading"""
        monkeypatch.setenv("JIRA_BASE_URL", "https://test.atlassian.net")
        monkeypatch.setenv("JIRA_EMAIL", "test@example.com")
        monkeypatch.setenv("JIRA_API_TOKEN", "token123")
        monkeypatch.setenv("JIRA_BOARD_ID", "42")

        config = JiraConfig.from_env()

        assert config.base_url == "https://test.atlassian.net"
        assert config.email == "test@example.com"
        assert config.api_token == "token123"
        assert config.board_id == 42

    def test_from_env_missing_variables(self, monkeypatch):
        """Test error when required variables are missing"""
        monkeypatch.setenv("JIRA_BASE_URL", "https://test.atlassian.net")
        monkeypatch.delenv("JIRA_EMAIL", raising=False)
        monkeypatch.delenv("JIRA_API_TOKEN", raising=False)
        monkeypatch.delenv("JIRA_BOARD_ID", raising=False)

        with pytest.raises(ValueError):
            JiraConfig.from_env()

    def test_get_auth_header(self):
        """Test Basic Auth header generation"""
        config = JiraConfig(
            base_url="https://test.atlassian.net",
            email="test@example.com",
            api_token="token123",
            board_id=42,
        )

        headers = config.get_auth_header()

        assert "Authorization" in headers
        assert headers["Authorization"].startswith("Basic ")


class TestJiraSprintManager:
    """Test JiraSprintManager class"""

    @pytest.fixture
    def config(self):
        """Create test config"""
        return JiraConfig(
            base_url="https://test.atlassian.net",
            email="test@example.com",
            api_token="token123",
            board_id=42,
        )

    @pytest.fixture
    def manager(self, config):
        """Create test manager"""
        return JiraSprintManager(config, dry_run=False)

    def test_get_iso_week_number(self, manager):
        """Test ISO week number calculation"""
        # 2026-05-25 (today) is in week 21
        date = datetime(2026, 5, 25)
        week = manager._get_iso_week_number(date)
        assert week == 21

    def test_get_sprint_dates(self, manager):
        """Test sprint date calculation"""
        # Mock datetime to 2026-05-25 (Monday)
        with patch('scripts.sprint_manager.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime(2026, 5, 25)
            mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)

            start, end = manager._get_sprint_dates()

            # 2026-05-25 is Monday, so start should be 2026-05-25
            # End should be 2026-05-31 (Sunday)
            assert start.weekday() == 0  # Monday
            assert end.weekday() == 6    # Sunday
            assert (end - start).days == 6  # 7-day sprint

    def test_generate_sprint_name(self, manager):
        """Test sprint name generation"""
        date = datetime(2026, 5, 25)
        name = manager._generate_sprint_name(date)

        assert name == "Sprint 2026-W21"

    def test_generate_sprint_name_week_01(self, manager):
        """Test sprint name generation for first week"""
        date = datetime(2026, 1, 5)  # Week 1
        name = manager._generate_sprint_name(date)

        assert name == "Sprint 2026-W01"

    @patch('scripts.sprint_manager.requests.Session.get')
    def test_get_active_sprints(self, mock_get, manager):
        """Test fetching active sprints"""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "values": [
                {"id": 1, "name": "Sprint 2026-W20"},
                {"id": 2, "name": "Sprint 2026-W21"},
            ]
        }
        mock_get.return_value = mock_response

        sprints = manager._get_active_sprints()

        assert len(sprints) == 2
        assert sprints[0]["id"] == 1
        assert sprints[1]["name"] == "Sprint 2026-W21"

    @patch('scripts.sprint_manager.requests.Session.get')
    def test_get_active_sprints_error(self, mock_get, manager):
        """Test error handling when fetching sprints fails"""
        mock_get.side_effect = Exception("Connection error")

        with pytest.raises(RuntimeError):
            manager._get_active_sprints()

    @patch('scripts.sprint_manager.requests.Session.post')
    def test_close_sprint(self, mock_post, manager):
        """Test closing a sprint"""
        mock_response = MagicMock()
        mock_response.json.return_value = {"id": 1, "state": "closed"}
        mock_post.return_value = mock_response

        result = manager._close_sprint(1, "Sprint 2026-W20")

        assert result is True
        mock_post.assert_called_once()

    @patch('scripts.sprint_manager.requests.Session.post')
    def test_close_sprint_dry_run(self, mock_post, config):
        """Test closing a sprint in dry-run mode"""
        manager = JiraSprintManager(config, dry_run=True)
        result = manager._close_sprint(1, "Sprint 2026-W20")

        assert result is True
        # Should not make any API call
        mock_post.assert_not_called()

    @patch('scripts.sprint_manager.requests.Session.post')
    def test_create_sprint(self, mock_post, manager):
        """Test creating a new sprint"""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "id": 2,
            "name": "Sprint 2026-W21",
            "state": "future",
        }
        mock_post.return_value = mock_response

        start = datetime(2026, 5, 25)
        end = datetime(2026, 5, 31)

        sprint = manager._create_sprint("Sprint 2026-W21", start, end)

        assert sprint["id"] == 2
        assert sprint["name"] == "Sprint 2026-W21"

    @patch('scripts.sprint_manager.requests.Session.post')
    def test_create_sprint_dry_run(self, mock_post, config):
        """Test creating a sprint in dry-run mode"""
        manager = JiraSprintManager(config, dry_run=True)

        start = datetime(2026, 5, 25)
        end = datetime(2026, 5, 31)

        sprint = manager._create_sprint("Sprint 2026-W21", start, end)

        assert sprint["id"] == 99999  # Dummy ID
        # Should not make any API call
        mock_post.assert_not_called()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
