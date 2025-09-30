#!/usr/bin/env python3
"""
Redis Configuration for Team Logo Combiner

Provides essential Redis configuration for pub/sub integration.
"""

import os
from dataclasses import dataclass
from typing import Dict, Optional


@dataclass
class RedisConfig:
    """Redis configuration for team-logo-combiner."""

    # Connection settings
    url: str = "redis://fogis-redis:6379"
    enabled: bool = True

    # Channel configuration
    avatar_requests_channel: str = "fogis:avatars:requests"
    avatar_results_channel: str = "fogis:avatars:results"
    service_status_channel: str = "fogis:avatars:status"

    # Processing configuration
    result_storage: str = "base64"  # 'base64', 'google_drive', or 'url'
    processing_timeout: int = 30  # seconds

    @classmethod
    def from_environment(cls) -> "RedisConfig":
        """Create Redis configuration from environment variables."""
        return cls(
            url=os.getenv("REDIS_URL", "redis://fogis-redis:6379"),
            enabled=os.getenv("REDIS_PUBSUB_ENABLED", "true").lower()
            in ("true", "1", "yes"),
            avatar_requests_channel=os.getenv(
                "REDIS_AVATAR_REQUESTS_CHANNEL", "fogis:avatars:requests"
            ),
            avatar_results_channel=os.getenv(
                "REDIS_AVATAR_RESULTS_CHANNEL", "fogis:avatars:results"
            ),
            service_status_channel=os.getenv(
                "REDIS_SERVICE_STATUS_CHANNEL", "fogis:avatars:status"
            ),
            result_storage=os.getenv("AVATAR_RESULT_STORAGE", "base64"),
            processing_timeout=int(os.getenv("AVATAR_PROCESSING_TIMEOUT", "30")),
        )

    def get_channels(self) -> Dict[str, str]:
        """Get Redis channel configuration."""
        return {
            "avatar_requests": self.avatar_requests_channel,
            "avatar_results": self.avatar_results_channel,
            "service_status": self.service_status_channel,
        }


# Global configuration instance
_config: Optional[RedisConfig] = None


def get_redis_config() -> RedisConfig:
    """Get global Redis configuration."""
    global _config
    if _config is None:
        _config = RedisConfig.from_environment()
    return _config


def reload_redis_config() -> None:
    """Reload global Redis configuration from environment."""
    global _config
    _config = RedisConfig.from_environment()

