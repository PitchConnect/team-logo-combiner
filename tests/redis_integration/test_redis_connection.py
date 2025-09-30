"""Tests for Redis connection manager."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from src.redis_integration.connection_manager import RedisConnectionManager
from src.redis_integration.config import RedisConfig


class TestRedisConnectionManager:
    """Test Redis connection manager."""

    @patch('src.redis_integration.connection_manager.get_redis_config')
    def test_init(self, mock_get_config):
        """Test connection manager initialization."""
        mock_config = RedisConfig()
        mock_get_config.return_value = mock_config

        manager = RedisConnectionManager()
        assert manager.config == mock_config
        assert manager._client is None
        assert manager._pubsub is None

    @patch('src.redis_integration.connection_manager.redis.from_url')
    @patch('src.redis_integration.connection_manager.get_redis_config')
    def test_get_client_success(self, mock_get_config, mock_from_url):
        """Test successful client connection."""
        mock_config = RedisConfig(enabled=True)
        mock_get_config.return_value = mock_config

        mock_client = Mock()
        mock_client.ping.return_value = True
        mock_from_url.return_value = mock_client

        manager = RedisConnectionManager()
        client = manager.get_client()

        assert client == mock_client
        mock_from_url.assert_called_once_with(
            mock_config.url,
            decode_responses=True,
            socket_connect_timeout=5,
            socket_keepalive=True,
        )
        mock_client.ping.assert_called_once()

    @patch('src.redis_integration.connection_manager.get_redis_config')
    def test_get_client_disabled(self, mock_get_config):
        """Test get_client when Redis is disabled."""
        mock_config = RedisConfig(enabled=False)
        mock_get_config.return_value = mock_config

        manager = RedisConnectionManager()
        client = manager.get_client()

        assert client is None

    @patch('src.redis_integration.connection_manager.redis.from_url')
    @patch('src.redis_integration.connection_manager.get_redis_config')
    def test_get_client_connection_failure(self, mock_get_config, mock_from_url):
        """Test get_client when connection fails."""
        mock_config = RedisConfig(enabled=True)
        mock_get_config.return_value = mock_config

        mock_from_url.side_effect = Exception("Connection failed")

        manager = RedisConnectionManager()
        client = manager.get_client()

        assert client is None

    @patch('src.redis_integration.connection_manager.redis.from_url')
    @patch('src.redis_integration.connection_manager.get_redis_config')
    def test_get_client_cached(self, mock_get_config, mock_from_url):
        """Test that client is cached after first connection."""
        mock_config = RedisConfig(enabled=True)
        mock_get_config.return_value = mock_config

        mock_client = Mock()
        mock_client.ping.return_value = True
        mock_from_url.return_value = mock_client

        manager = RedisConnectionManager()
        client1 = manager.get_client()
        client2 = manager.get_client()

        assert client1 == client2
        # from_url should only be called once
        assert mock_from_url.call_count == 1

    @patch('src.redis_integration.connection_manager.redis.from_url')
    @patch('src.redis_integration.connection_manager.get_redis_config')
    def test_get_pubsub_success(self, mock_get_config, mock_from_url):
        """Test successful pub/sub connection."""
        mock_config = RedisConfig(enabled=True)
        mock_get_config.return_value = mock_config

        mock_client = Mock()
        mock_client.ping.return_value = True
        mock_pubsub = Mock()
        mock_client.pubsub.return_value = mock_pubsub
        mock_from_url.return_value = mock_client

        manager = RedisConnectionManager()
        pubsub = manager.get_pubsub()

        assert pubsub == mock_pubsub
        mock_client.pubsub.assert_called_once()

    @patch('src.redis_integration.connection_manager.get_redis_config')
    def test_get_pubsub_disabled(self, mock_get_config):
        """Test get_pubsub when Redis is disabled."""
        mock_config = RedisConfig(enabled=False)
        mock_get_config.return_value = mock_config

        manager = RedisConnectionManager()
        pubsub = manager.get_pubsub()

        assert pubsub is None

    @patch('src.redis_integration.connection_manager.redis.from_url')
    @patch('src.redis_integration.connection_manager.get_redis_config')
    def test_is_connected_true(self, mock_get_config, mock_from_url):
        """Test is_connected when connected."""
        mock_config = RedisConfig(enabled=True)
        mock_get_config.return_value = mock_config

        mock_client = Mock()
        mock_client.ping.return_value = True
        mock_from_url.return_value = mock_client

        manager = RedisConnectionManager()
        assert manager.is_connected() is True

    @patch('src.redis_integration.connection_manager.get_redis_config')
    def test_is_connected_disabled(self, mock_get_config):
        """Test is_connected when Redis is disabled."""
        mock_config = RedisConfig(enabled=False)
        mock_get_config.return_value = mock_config

        manager = RedisConnectionManager()
        assert manager.is_connected() is False

    @patch('src.redis_integration.connection_manager.redis.from_url')
    @patch('src.redis_integration.connection_manager.get_redis_config')
    def test_is_connected_ping_fails(self, mock_get_config, mock_from_url):
        """Test is_connected when ping fails."""
        mock_config = RedisConfig(enabled=True)
        mock_get_config.return_value = mock_config

        mock_client = Mock()
        # First ping succeeds (for get_client), second fails (for is_connected)
        mock_client.ping.side_effect = [True, Exception("Connection lost")]
        mock_from_url.return_value = mock_client

        manager = RedisConnectionManager()
        manager.get_client()  # Establish connection
        assert manager.is_connected() is False
        # Client should be reset to None
        assert manager._client is None

    @patch('src.redis_integration.connection_manager.redis.from_url')
    @patch('src.redis_integration.connection_manager.get_redis_config')
    def test_close(self, mock_get_config, mock_from_url):
        """Test closing connection."""
        mock_config = RedisConfig(enabled=True)
        mock_get_config.return_value = mock_config

        mock_client = Mock()
        mock_client.ping.return_value = True
        mock_from_url.return_value = mock_client

        manager = RedisConnectionManager()
        manager.get_client()  # Establish connection
        manager.close()

        mock_client.close.assert_called_once()
        assert manager._client is None
        assert manager._pubsub is None

    @patch('src.redis_integration.connection_manager.redis.from_url')
    @patch('src.redis_integration.connection_manager.get_redis_config')
    def test_close_with_error(self, mock_get_config, mock_from_url):
        """Test closing connection when close() raises error."""
        mock_config = RedisConfig(enabled=True)
        mock_get_config.return_value = mock_config

        mock_client = Mock()
        mock_client.ping.return_value = True
        mock_client.close.side_effect = Exception("Close failed")
        mock_from_url.return_value = mock_client

        manager = RedisConnectionManager()
        manager.get_client()  # Establish connection
        manager.close()  # Should not raise exception

        # Client should still be reset
        assert manager._client is None
        assert manager._pubsub is None

