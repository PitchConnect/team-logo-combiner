"""Tests for Redis publisher."""

import json
import pytest
from unittest.mock import Mock, patch, MagicMock
from src.redis_integration.publisher import AvatarResultPublisher, PublishResult
from src.redis_integration.config import RedisConfig


class TestAvatarResultPublisher:
    """Test Avatar Result Publisher."""

    @patch('src.redis_integration.publisher.RedisConnectionManager')
    def test_init(self, mock_connection_manager):
        """Test publisher initialization."""
        mock_config = RedisConfig()
        mock_connection_manager.return_value.config = mock_config

        publisher = AvatarResultPublisher()
        assert publisher.config == mock_config
        assert publisher.stats["total_published"] == 0
        assert publisher.stats["successful_publishes"] == 0
        assert publisher.stats["failed_publishes"] == 0

    @patch('src.redis_integration.publisher.RedisConnectionManager')
    def test_publish_avatar_result_success(self, mock_connection_manager):
        """Test successful avatar result publishing."""
        # Mock Redis client
        mock_client = Mock()
        mock_client.publish.return_value = 2  # 2 subscribers
        mock_connection_manager.return_value.get_client.return_value = mock_client
        mock_connection_manager.return_value.config = RedisConfig()

        publisher = AvatarResultPublisher()
        result = publisher.publish_avatar_result(
            request_id="test-123",
            team1_id="7557",
            team2_id="9590",
            status="success",
            avatar_url="https://example.com/avatar.png",
            processing_time_ms=1234,
        )

        assert result.success is True
        assert result.subscribers_notified == 2
        assert result.error is None
        assert mock_client.publish.called

        # Verify message format
        call_args = mock_client.publish.call_args
        channel = call_args[0][0]
        message_json = call_args[0][1]

        assert channel == "fogis:avatars:results"
        message = json.loads(message_json)
        assert message["request_id"] == "test-123"
        assert message["payload"]["status"] == "success"
        assert message["payload"]["team1_id"] == "7557"
        assert message["payload"]["team2_id"] == "9590"
        assert message["payload"]["avatar_url"] == "https://example.com/avatar.png"
        assert message["payload"]["processing_time_ms"] == 1234

    @patch('src.redis_integration.publisher.RedisConnectionManager')
    def test_publish_avatar_result_with_base64(self, mock_connection_manager):
        """Test publishing avatar result with base64 data."""
        mock_client = Mock()
        mock_client.publish.return_value = 1
        mock_connection_manager.return_value.get_client.return_value = mock_client
        mock_connection_manager.return_value.config = RedisConfig()

        publisher = AvatarResultPublisher()
        result = publisher.publish_avatar_result(
            request_id="test-456",
            team1_id="1111",
            team2_id="2222",
            status="success",
            avatar_data="base64encodeddata==",
            processing_time_ms=5678,
        )

        assert result.success is True
        call_args = mock_client.publish.call_args
        message_json = call_args[0][1]
        message = json.loads(message_json)
        assert message["payload"]["avatar_data"] == "base64encodeddata=="

    @patch('src.redis_integration.publisher.RedisConnectionManager')
    def test_publish_avatar_result_error(self, mock_connection_manager):
        """Test publishing error result."""
        mock_client = Mock()
        mock_client.publish.return_value = 1
        mock_connection_manager.return_value.get_client.return_value = mock_client
        mock_connection_manager.return_value.config = RedisConfig()

        publisher = AvatarResultPublisher()
        result = publisher.publish_avatar_result(
            request_id="test-789",
            team1_id="3333",
            team2_id="4444",
            status="error",
            error={"type": "ImageDownloadError", "message": "Failed to download logo"},
            processing_time_ms=999,
        )

        assert result.success is True
        call_args = mock_client.publish.call_args
        message_json = call_args[0][1]
        message = json.loads(message_json)
        assert message["payload"]["status"] == "error"
        assert message["payload"]["error_type"] == "ImageDownloadError"
        assert message["payload"]["error_message"] == "Failed to download logo"

    @patch('src.redis_integration.publisher.RedisConnectionManager')
    def test_publish_when_disabled(self, mock_connection_manager):
        """Test publishing when Redis is disabled."""
        mock_config = RedisConfig(enabled=False)
        mock_connection_manager.return_value.config = mock_config

        publisher = AvatarResultPublisher()
        result = publisher.publish_avatar_result(
            request_id="test-disabled",
            team1_id="5555",
            team2_id="6666",
            status="success",
        )

        assert result.success is True
        assert result.subscribers_notified == 0

    @patch('src.redis_integration.publisher.RedisConnectionManager')
    def test_publish_when_client_unavailable(self, mock_connection_manager):
        """Test publishing when Redis client is unavailable."""
        mock_connection_manager.return_value.get_client.return_value = None
        mock_connection_manager.return_value.config = RedisConfig()

        publisher = AvatarResultPublisher()
        result = publisher.publish_avatar_result(
            request_id="test-unavailable",
            team1_id="7777",
            team2_id="8888",
            status="success",
        )

        assert result.success is False
        assert result.error == "Redis client not available"

    @patch('src.redis_integration.publisher.RedisConnectionManager')
    def test_publish_with_exception(self, mock_connection_manager):
        """Test publishing when publish() raises exception."""
        mock_client = Mock()
        mock_client.publish.side_effect = Exception("Publish failed")
        mock_connection_manager.return_value.get_client.return_value = mock_client
        mock_connection_manager.return_value.config = RedisConfig()

        publisher = AvatarResultPublisher()
        result = publisher.publish_avatar_result(
            request_id="test-exception",
            team1_id="9999",
            team2_id="0000",
            status="success",
        )

        assert result.success is False
        assert "Publish failed" in result.error

    @patch('src.redis_integration.publisher.RedisConnectionManager')
    def test_publish_service_status(self, mock_connection_manager):
        """Test publishing service status."""
        mock_client = Mock()
        mock_client.publish.return_value = 3
        mock_connection_manager.return_value.get_client.return_value = mock_client
        mock_connection_manager.return_value.config = RedisConfig()

        publisher = AvatarResultPublisher()
        result = publisher.publish_service_status(
            status="started", details={"version": "1.0.0"}
        )

        assert result.success is True
        assert result.subscribers_notified == 3

        call_args = mock_client.publish.call_args
        channel = call_args[0][0]
        message_json = call_args[0][1]

        assert channel == "fogis:avatars:status"
        message = json.loads(message_json)
        assert message["payload"]["status"] == "started"
        assert message["payload"]["details"]["version"] == "1.0.0"

    @patch('src.redis_integration.publisher.RedisConnectionManager')
    def test_get_publishing_stats(self, mock_connection_manager):
        """Test getting publishing statistics."""
        mock_connection_manager.return_value.is_connected.return_value = True
        mock_connection_manager.return_value.config = RedisConfig()

        publisher = AvatarResultPublisher()
        publisher.stats["total_published"] = 10
        publisher.stats["successful_publishes"] = 8
        publisher.stats["failed_publishes"] = 2

        stats = publisher.get_publishing_stats()

        assert stats["redis_enabled"] is True
        assert stats["redis_connected"] is True
        assert stats["publishing_stats"]["total_published"] == 10
        assert stats["publishing_stats"]["successful_publishes"] == 8
        assert stats["publishing_stats"]["failed_publishes"] == 2

