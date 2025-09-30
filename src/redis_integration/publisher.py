#!/usr/bin/env python3
"""
Redis Publisher for Team Logo Combiner

Provides Redis publishing functionality for avatar results and status messages.
"""

import json
import logging
from dataclasses import dataclass
from typing import Any, Dict, Optional

from .connection_manager import RedisConnectionManager
from .message_formatter import AvatarResultMessageFormatter

logger = logging.getLogger(__name__)


@dataclass
class PublishResult:
    """Result of a Redis publish operation."""

    success: bool
    subscribers_notified: int = 0
    error: Optional[str] = None


class AvatarResultPublisher:
    """Redis publisher for avatar creation results."""

    def __init__(self) -> None:
        """Initialize Redis publisher."""
        self.connection_manager = RedisConnectionManager()
        self.config = self.connection_manager.config
        self.stats: Dict[str, Any] = {
            "total_published": 0,
            "successful_publishes": 0,
            "failed_publishes": 0,
            "last_publish_time": None,
        }

    def _log_message_details(
        self, channel: str, message: str, subscribers: int, message_type: str = "avatar_result"
    ) -> None:
        """
        Log detailed information about a Redis message.

        Args:
            channel: Redis channel name
            message: JSON message string
            subscribers: Number of subscribers notified
            message_type: Type of message being published
        """
        try:
            # Parse message for logging
            message_data = json.loads(message)

            # Log message details at INFO level
            logger.info("📨 PUBLISHING MESSAGE:")
            logger.info(f"   Channel: {channel}")
            logger.info(f"   Message ID: {message_data.get('message_id', 'N/A')}")
            logger.info(f"   Type: {message_type}")

            # Log payload details
            payload = message_data.get("payload", {})
            if "status" in payload:
                logger.info(f"   Status: {payload['status']}")
            if "team1_id" in payload and "team2_id" in payload:
                logger.info(
                    f"   Teams: {payload['team1_id']} vs {payload['team2_id']}"
                )

            logger.info(f"   Subscribers: {subscribers}")

            # Log full message at debug level
            logger.debug(f"   Full Message: {json.dumps(message_data, indent=2)}")

        except json.JSONDecodeError as e:
            logger.warning(f"⚠️ Could not parse message for detailed logging: {e}")
        except Exception as e:
            logger.warning(f"⚠️ Error logging message details: {e}")

    def publish_avatar_result(
        self,
        request_id: str,
        team1_id: str,
        team2_id: str,
        status: str,
        avatar_url: Optional[str] = None,
        avatar_data: Optional[str] = None,
        error: Optional[Dict] = None,
        processing_time_ms: int = 0,
        metadata: Optional[Dict] = None,
    ) -> PublishResult:
        """
        Publish avatar creation result to Redis channel.

        Args:
            request_id: Original request message ID
            team1_id: First team ID
            team2_id: Second team ID
            status: Result status (success, error)
            avatar_url: URL to avatar image (optional)
            avatar_data: Base64-encoded avatar data (optional)
            error: Error details if status is error
            processing_time_ms: Processing time in milliseconds
            metadata: Additional metadata

        Returns:
            PublishResult: Publishing result
        """
        if not self.config.enabled:
            return PublishResult(success=True, subscribers_notified=0)

        client = self.connection_manager.get_client()
        if client is None:
            error_msg = "Redis client not available"
            logger.warning(f"⚠️ {error_msg}")
            self.stats["failed_publishes"] = self.stats.get("failed_publishes", 0) + 1
            return PublishResult(success=False, error=error_msg)

        try:
            message = AvatarResultMessageFormatter.format_avatar_result(
                request_id=request_id,
                team1_id=team1_id,
                team2_id=team2_id,
                status=status,
                avatar_url=avatar_url,
                avatar_data=avatar_data,
                error_type=error.get("type") if error else None,
                error_message=error.get("message") if error else None,
                processing_time_ms=processing_time_ms,
                metadata=metadata,
            )

            subscribers_result = client.publish(
                self.config.avatar_results_channel, message
            )
            # Handle both sync and async redis client return types
            subscribers = (
                int(subscribers_result)
                if not hasattr(subscribers_result, "__await__")
                else 0
            )

            # Log detailed message information
            self._log_message_details(
                self.config.avatar_results_channel, message, subscribers
            )

            self.stats["total_published"] = self.stats.get("total_published", 0) + 1
            self.stats["successful_publishes"] = (
                self.stats.get("successful_publishes", 0) + 1
            )
            self.stats["last_publish_time"] = message

            logger.info(f"✅ Published avatar result to {subscribers} subscribers")
            return PublishResult(success=True, subscribers_notified=subscribers)

        except Exception as e:
            error_msg = f"Failed to publish avatar result: {e}"
            logger.error(f"❌ {error_msg}")
            self.stats["failed_publishes"] = self.stats.get("failed_publishes", 0) + 1
            return PublishResult(success=False, error=error_msg)

    def publish_service_status(
        self, status: str, details: Optional[Dict] = None
    ) -> PublishResult:
        """
        Publish service status to Redis channel.

        Args:
            status: Service status (started, running, stopped, error)
            details: Additional status details

        Returns:
            PublishResult: Publishing result
        """
        if not self.config.enabled:
            return PublishResult(success=True, subscribers_notified=0)

        client = self.connection_manager.get_client()
        if client is None:
            error_msg = "Redis client not available"
            logger.warning(f"⚠️ {error_msg}")
            return PublishResult(success=False, error=error_msg)

        try:
            message = AvatarResultMessageFormatter.format_service_status(
                status, details
            )
            subscribers_result = client.publish(
                self.config.service_status_channel, message
            )
            subscribers = (
                int(subscribers_result)
                if not hasattr(subscribers_result, "__await__")
                else 0
            )

            # Log detailed message information
            self._log_message_details(
                self.config.service_status_channel,
                message,
                subscribers,
                "service_status",
            )

            logger.info(
                f"✅ Published service status '{status}' to {subscribers} subscribers"
            )
            return PublishResult(success=True, subscribers_notified=subscribers)

        except Exception as e:
            error_msg = f"Failed to publish service status: {e}"
            logger.error(f"❌ {error_msg}")
            return PublishResult(success=False, error=error_msg)

    def get_publishing_stats(self) -> Dict:
        """Get publishing statistics."""
        return {
            "redis_enabled": self.config.enabled,
            "redis_connected": self.connection_manager.is_connected(),
            "publishing_stats": self.stats.copy(),
        }

