"""Tests for Redis configuration module."""

import os
import pytest
from src.redis_integration.config import RedisConfig, get_redis_config, reload_redis_config


class TestRedisConfig:
    """Test Redis configuration."""

    def test_default_config(self):
        """Test default configuration values."""
        config = RedisConfig()
        assert config.url == "redis://fogis-redis:6379"
        assert config.enabled is True
        assert config.avatar_requests_channel == "fogis:avatars:requests"
        assert config.avatar_results_channel == "fogis:avatars:results"
        assert config.service_status_channel == "fogis:avatars:status"
        assert config.result_storage == "base64"
        assert config.processing_timeout == 30

    def test_from_environment(self, monkeypatch):
        """Test configuration from environment variables."""
        monkeypatch.setenv("REDIS_URL", "redis://test:6379")
        monkeypatch.setenv("REDIS_PUBSUB_ENABLED", "false")
        monkeypatch.setenv("REDIS_AVATAR_REQUESTS_CHANNEL", "test:requests")
        monkeypatch.setenv("REDIS_AVATAR_RESULTS_CHANNEL", "test:results")
        monkeypatch.setenv("REDIS_SERVICE_STATUS_CHANNEL", "test:status")
        monkeypatch.setenv("AVATAR_RESULT_STORAGE", "google_drive")
        monkeypatch.setenv("AVATAR_PROCESSING_TIMEOUT", "60")

        config = RedisConfig.from_environment()
        assert config.url == "redis://test:6379"
        assert config.enabled is False
        assert config.avatar_requests_channel == "test:requests"
        assert config.avatar_results_channel == "test:results"
        assert config.service_status_channel == "test:status"
        assert config.result_storage == "google_drive"
        assert config.processing_timeout == 60

    def test_enabled_variations(self, monkeypatch):
        """Test various enabled flag values."""
        # Test true values
        for value in ["true", "True", "TRUE", "1", "yes", "Yes", "YES"]:
            monkeypatch.setenv("REDIS_PUBSUB_ENABLED", value)
            config = RedisConfig.from_environment()
            assert config.enabled is True, f"Failed for value: {value}"

        # Test false values
        for value in ["false", "False", "FALSE", "0", "no", "No", "NO"]:
            monkeypatch.setenv("REDIS_PUBSUB_ENABLED", value)
            config = RedisConfig.from_environment()
            assert config.enabled is False, f"Failed for value: {value}"

    def test_get_channels(self):
        """Test get_channels method."""
        config = RedisConfig()
        channels = config.get_channels()
        assert isinstance(channels, dict)
        assert "avatar_requests" in channels
        assert "avatar_results" in channels
        assert "service_status" in channels
        assert channels["avatar_requests"] == "fogis:avatars:requests"
        assert channels["avatar_results"] == "fogis:avatars:results"
        assert channels["service_status"] == "fogis:avatars:status"

    def test_get_redis_config_singleton(self, monkeypatch):
        """Test that get_redis_config returns singleton instance."""
        monkeypatch.setenv("REDIS_URL", "redis://singleton:6379")
        # Clear any existing config
        reload_redis_config()

        config1 = get_redis_config()
        config2 = get_redis_config()

        # Should be the same instance
        assert config1 is config2
        assert config1.url == "redis://singleton:6379"

    def test_reload_redis_config(self, monkeypatch):
        """Test reloading configuration."""
        monkeypatch.setenv("REDIS_URL", "redis://first:6379")
        reload_redis_config()
        config1 = get_redis_config()
        assert config1.url == "redis://first:6379"

        # Change environment and reload
        monkeypatch.setenv("REDIS_URL", "redis://second:6379")
        reload_redis_config()
        config2 = get_redis_config()

        # Should have new URL
        assert config2.url == "redis://second:6379"

