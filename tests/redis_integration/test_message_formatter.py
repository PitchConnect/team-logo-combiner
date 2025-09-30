"""Tests for message formatters."""

import json
import pytest
from src.redis_integration.message_formatter import (
    AvatarRequestMessageFormatter,
    AvatarResultMessageFormatter,
)


class TestAvatarRequestMessageFormatter:
    """Test Avatar Request Message Formatter."""

    def test_format_avatar_request_basic(self):
        """Test formatting basic avatar request."""
        message_json = AvatarRequestMessageFormatter.format_avatar_request(
            team1_id="7557", team2_id="9590"
        )

        message = json.loads(message_json)
        assert "message_id" in message
        assert "timestamp" in message
        assert message["source"] == "team-logo-combiner"
        assert message["version"] == "1.0"
        assert message["type"] == "avatar_request"
        assert message["payload"]["team1_id"] == "7557"
        assert message["payload"]["team2_id"] == "9590"
        assert message["payload"]["priority"] == "normal"
        assert message["payload"]["callback_channel"] == "fogis:avatars:results"

    def test_format_avatar_request_with_optional_fields(self):
        """Test formatting avatar request with optional fields."""
        message_json = AvatarRequestMessageFormatter.format_avatar_request(
            team1_id="1111",
            team2_id="2222",
            team1_organization_id="org1",
            team2_organization_id="org2",
            match_id="match-123",
            priority="high",
            metadata={"requester": "test"},
        )

        message = json.loads(message_json)
        assert message["payload"]["team1_organization_id"] == "org1"
        assert message["payload"]["team2_organization_id"] == "org2"
        assert message["payload"]["match_id"] == "match-123"
        assert message["payload"]["priority"] == "high"
        assert message["payload"]["metadata"]["requester"] == "test"

    def test_parse_avatar_request_valid(self):
        """Test parsing valid avatar request."""
        message = {
            "message_id": "test-123",
            "timestamp": "2025-09-30T12:00:00Z",
            "source": "test",
            "version": "1.0",
            "type": "avatar_request",
            "payload": {"team1_id": "7557", "team2_id": "9590"},
        }
        message_json = json.dumps(message)

        parsed = AvatarRequestMessageFormatter.parse_avatar_request(message_json)

        assert parsed["message_id"] == "test-123"
        assert parsed["payload"]["team1_id"] == "7557"
        assert parsed["payload"]["team2_id"] == "9590"

    def test_parse_avatar_request_missing_message_id(self):
        """Test parsing request with missing message_id."""
        message = {"payload": {"team1_id": "7557", "team2_id": "9590"}}
        message_json = json.dumps(message)

        with pytest.raises(ValueError, match="Missing message_id field"):
            AvatarRequestMessageFormatter.parse_avatar_request(message_json)

    def test_parse_avatar_request_missing_payload(self):
        """Test parsing request with missing payload."""
        message = {"message_id": "test-123"}
        message_json = json.dumps(message)

        with pytest.raises(ValueError, match="Missing payload field"):
            AvatarRequestMessageFormatter.parse_avatar_request(message_json)

    def test_parse_avatar_request_missing_team_ids(self):
        """Test parsing request with missing team IDs."""
        message = {"message_id": "test-123", "payload": {"team1_id": "7557"}}
        message_json = json.dumps(message)

        with pytest.raises(ValueError, match="Missing team IDs in payload"):
            AvatarRequestMessageFormatter.parse_avatar_request(message_json)

    def test_parse_avatar_request_invalid_json(self):
        """Test parsing invalid JSON."""
        with pytest.raises(ValueError, match="Invalid JSON format"):
            AvatarRequestMessageFormatter.parse_avatar_request("invalid json{")


class TestAvatarResultMessageFormatter:
    """Test Avatar Result Message Formatter."""

    def test_format_avatar_result_success(self):
        """Test formatting successful avatar result."""
        message_json = AvatarResultMessageFormatter.format_avatar_result(
            request_id="test-123",
            team1_id="7557",
            team2_id="9590",
            status="success",
            avatar_url="https://example.com/avatar.png",
            processing_time_ms=1234,
        )

        message = json.loads(message_json)
        assert "message_id" in message
        assert message["request_id"] == "test-123"
        assert "timestamp" in message
        assert message["source"] == "team-logo-combiner"
        assert message["version"] == "1.0"
        assert message["type"] == "avatar_result"
        assert message["payload"]["status"] == "success"
        assert message["payload"]["team1_id"] == "7557"
        assert message["payload"]["team2_id"] == "9590"
        assert message["payload"]["avatar_url"] == "https://example.com/avatar.png"
        assert message["payload"]["processing_time_ms"] == 1234

    def test_format_avatar_result_with_base64(self):
        """Test formatting result with base64 data."""
        message_json = AvatarResultMessageFormatter.format_avatar_result(
            request_id="test-456",
            team1_id="1111",
            team2_id="2222",
            status="success",
            avatar_data="base64encodeddata==",
            processing_time_ms=5678,
            metadata={"format": "PNG", "size": "512x512"},
        )

        message = json.loads(message_json)
        assert message["payload"]["avatar_data"] == "base64encodeddata=="
        assert message["payload"]["metadata"]["format"] == "PNG"
        assert message["payload"]["metadata"]["size"] == "512x512"

    def test_format_avatar_result_error(self):
        """Test formatting error result."""
        message_json = AvatarResultMessageFormatter.format_avatar_result(
            request_id="test-789",
            team1_id="3333",
            team2_id="4444",
            status="error",
            error_type="ImageDownloadError",
            error_message="Failed to download team logo",
            processing_time_ms=999,
        )

        message = json.loads(message_json)
        assert message["payload"]["status"] == "error"
        assert message["payload"]["error_type"] == "ImageDownloadError"
        assert message["payload"]["error_message"] == "Failed to download team logo"
        assert "avatar_url" not in message["payload"]
        assert "avatar_data" not in message["payload"]

    def test_format_avatar_result_error_with_defaults(self):
        """Test formatting error result with default error values."""
        message_json = AvatarResultMessageFormatter.format_avatar_result(
            request_id="test-000",
            team1_id="5555",
            team2_id="6666",
            status="error",
            processing_time_ms=111,
        )

        message = json.loads(message_json)
        assert message["payload"]["error_type"] == "Unknown"
        assert message["payload"]["error_message"] == "Unknown error"

    def test_format_service_status(self):
        """Test formatting service status message."""
        message_json = AvatarResultMessageFormatter.format_service_status(
            status="started", details={"version": "1.0.0", "mode": "dual"}
        )

        message = json.loads(message_json)
        assert "message_id" in message
        assert "timestamp" in message
        assert message["source"] == "team-logo-combiner"
        assert message["version"] == "1.0"
        assert message["type"] == "service_status"
        assert message["payload"]["status"] == "started"
        assert message["payload"]["details"]["version"] == "1.0.0"
        assert message["payload"]["details"]["mode"] == "dual"

    def test_format_service_status_no_details(self):
        """Test formatting service status without details."""
        message_json = AvatarResultMessageFormatter.format_service_status(
            status="running"
        )

        message = json.loads(message_json)
        assert message["payload"]["status"] == "running"
        assert message["payload"]["details"] == {}

