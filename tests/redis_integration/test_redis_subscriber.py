"""Tests for Redis subscriber."""

import json
import pytest
import time
from unittest.mock import Mock, patch, MagicMock, call
from src.redis_integration.subscriber import AvatarRequestSubscriber
from src.redis_integration.config import RedisConfig


class TestAvatarRequestSubscriber:
    """Test Avatar Request Subscriber."""

    @patch('src.redis_integration.subscriber.RedisConnectionManager')
    def test_init(self, mock_connection_manager):
        """Test subscriber initialization."""
        mock_config = RedisConfig()
        mock_connection_manager.return_value.config = mock_config

        handler = Mock()
        subscriber = AvatarRequestSubscriber(handler)

        assert subscriber.request_handler == handler
        assert subscriber.config == mock_config
        assert subscriber._running is False
        assert subscriber._thread is None

    @patch('src.redis_integration.subscriber.RedisConnectionManager')
    def test_start_when_disabled(self, mock_connection_manager):
        """Test start when Redis is disabled."""
        mock_config = RedisConfig(enabled=False)
        mock_connection_manager.return_value.config = mock_config

        handler = Mock()
        subscriber = AvatarRequestSubscriber(handler)
        subscriber.start()

        assert subscriber._running is False
        assert subscriber._thread is None

    @patch('src.redis_integration.subscriber.threading.Thread')
    @patch('src.redis_integration.subscriber.RedisConnectionManager')
    def test_start_when_enabled(self, mock_connection_manager, mock_thread):
        """Test start when Redis is enabled."""
        mock_config = RedisConfig(enabled=True)
        mock_connection_manager.return_value.config = mock_config

        handler = Mock()
        subscriber = AvatarRequestSubscriber(handler)
        subscriber.start()

        assert subscriber._running is True
        mock_thread.assert_called_once()
        assert mock_thread.return_value.start.called

    @patch('src.redis_integration.subscriber.RedisConnectionManager')
    def test_start_when_already_running(self, mock_connection_manager):
        """Test start when subscriber is already running."""
        mock_config = RedisConfig(enabled=True)
        mock_connection_manager.return_value.config = mock_config

        handler = Mock()
        subscriber = AvatarRequestSubscriber(handler)
        subscriber._running = True

        with patch('src.redis_integration.subscriber.threading.Thread') as mock_thread:
            subscriber.start()
            # Thread should not be created again
            mock_thread.assert_not_called()

    @patch('src.redis_integration.subscriber.RedisConnectionManager')
    def test_stop(self, mock_connection_manager):
        """Test stopping subscriber."""
        mock_config = RedisConfig(enabled=True)
        mock_connection_manager.return_value.config = mock_config

        handler = Mock()
        subscriber = AvatarRequestSubscriber(handler)
        subscriber._running = True
        mock_thread = Mock()
        subscriber._thread = mock_thread

        subscriber.stop()

        assert subscriber._running is False
        mock_thread.join.assert_called_once_with(timeout=5)

    @patch('src.redis_integration.subscriber.RedisConnectionManager')
    def test_handle_message_success(self, mock_connection_manager):
        """Test handling valid message."""
        mock_config = RedisConfig(enabled=True)
        mock_connection_manager.return_value.config = mock_config

        handler = Mock()
        subscriber = AvatarRequestSubscriber(handler)

        message = {
            "message_id": "test-123",
            "payload": {"team1_id": "7557", "team2_id": "9590"},
        }
        message_json = json.dumps(message)

        subscriber._handle_message(message_json)

        handler.assert_called_once_with("test-123", {"team1_id": "7557", "team2_id": "9590"})
        assert subscriber._stats["total_received"] == 1
        assert subscriber._stats["successful_processed"] == 1
        assert subscriber._stats["failed_processed"] == 0

    @patch('src.redis_integration.subscriber.RedisConnectionManager')
    def test_handle_message_missing_team_ids(self, mock_connection_manager):
        """Test handling message with missing team IDs."""
        mock_config = RedisConfig(enabled=True)
        mock_connection_manager.return_value.config = mock_config

        handler = Mock()
        subscriber = AvatarRequestSubscriber(handler)

        message = {"message_id": "test-456", "payload": {"team1_id": "7557"}}
        message_json = json.dumps(message)

        subscriber._handle_message(message_json)

        handler.assert_not_called()
        assert subscriber._stats["failed_processed"] == 1

    @patch('src.redis_integration.subscriber.RedisConnectionManager')
    def test_handle_message_invalid_json(self, mock_connection_manager):
        """Test handling invalid JSON message."""
        mock_config = RedisConfig(enabled=True)
        mock_connection_manager.return_value.config = mock_config

        handler = Mock()
        subscriber = AvatarRequestSubscriber(handler)

        subscriber._handle_message("invalid json{")

        handler.assert_not_called()
        assert subscriber._stats["failed_processed"] == 1

    @patch('src.redis_integration.subscriber.RedisConnectionManager')
    def test_handle_message_handler_exception(self, mock_connection_manager):
        """Test handling message when handler raises exception."""
        mock_config = RedisConfig(enabled=True)
        mock_connection_manager.return_value.config = mock_config

        handler = Mock()
        handler.side_effect = Exception("Handler failed")
        subscriber = AvatarRequestSubscriber(handler)

        message = {
            "message_id": "test-789",
            "payload": {"team1_id": "1111", "team2_id": "2222"},
        }
        message_json = json.dumps(message)

        subscriber._handle_message(message_json)

        handler.assert_called_once()
        assert subscriber._stats["total_received"] == 1
        assert subscriber._stats["successful_processed"] == 0
        assert subscriber._stats["failed_processed"] == 1

    @patch('src.redis_integration.subscriber.RedisConnectionManager')
    def test_get_stats(self, mock_connection_manager):
        """Test getting subscriber statistics."""
        mock_config = RedisConfig(enabled=True)
        mock_connection_manager.return_value.config = mock_config

        handler = Mock()
        subscriber = AvatarRequestSubscriber(handler)
        subscriber._running = True
        subscriber._stats["total_received"] = 5
        subscriber._stats["successful_processed"] = 4
        subscriber._stats["failed_processed"] = 1

        stats = subscriber.get_stats()

        assert stats["running"] is True
        assert stats["stats"]["total_received"] == 5
        assert stats["stats"]["successful_processed"] == 4
        assert stats["stats"]["failed_processed"] == 1

