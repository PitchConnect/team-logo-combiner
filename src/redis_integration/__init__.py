"""
Redis Integration Module for Team Logo Combiner

This module provides Redis pub/sub integration for the team logo combiner service,
enabling real-time communication with other services through Redis channels.

Author: Team Logo Combiner Development Team
Date: 2025-09-30
Issue: #15 - Migrate from HTTP calls to Redis pub/sub architecture
"""

from .config import RedisConfig, get_redis_config, reload_redis_config
from .connection_manager import RedisConnectionManager
from .message_formatter import (
    AvatarRequestMessageFormatter,
    AvatarResultMessageFormatter,
)
from .publisher import AvatarResultPublisher, PublishResult
from .subscriber import AvatarRequestSubscriber

__all__ = [
    "RedisConfig",
    "get_redis_config",
    "reload_redis_config",
    "RedisConnectionManager",
    "AvatarRequestMessageFormatter",
    "AvatarResultMessageFormatter",
    "AvatarResultPublisher",
    "PublishResult",
    "AvatarRequestSubscriber",
]

__version__ = "1.0.0"
__author__ = "Team Logo Combiner Development Team"

