#!/usr/bin/env python3
"""
Redis Subscriber for Team Logo Combiner

Provides Redis subscription functionality for avatar creation requests.
"""

import json
import logging
import threading
import time
from typing import Callable, Optional

from .connection_manager import RedisConnectionManager
from .message_formatter import AvatarRequestMessageFormatter

logger = logging.getLogger(__name__)


class AvatarRequestSubscriber:
    """Subscribes to avatar creation requests from Redis."""

    def __init__(self, request_handler: Callable) -> None:
        """
        Initialize Redis subscriber.

        Args:
            request_handler: Callable that handles avatar requests.
                            Should accept (request_id: str, payload: Dict)
        """
        self.connection_manager = RedisConnectionManager()
        self.config = self.connection_manager.config
        self.request_handler = request_handler
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._stats = {
            "total_received": 0,
            "successful_processed": 0,
            "failed_processed": 0,
            "last_message_time": None,
        }

    def start(self) -> None:
        """Start listening for avatar requests."""
        if not self.config.enabled:
            logger.info("📡 Redis pub/sub disabled - not starting subscriber")
            return

        if self._running:
            logger.warning("⚠️ Subscriber already running")
            return

        self._running = True
        self._thread = threading.Thread(target=self._listen, daemon=True)
        self._thread.start()
        logger.info(
            f"✅ Started listening on {self.config.avatar_requests_channel}"
        )

    def stop(self) -> None:
        """Stop listening for avatar requests."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        logger.info("🛑 Stopped avatar request subscriber")

    def _listen(self) -> None:
        """Listen for messages on the avatar requests channel."""
        while self._running:
            try:
                pubsub = self.connection_manager.get_pubsub()
                if pubsub is None:
                    logger.warning(
                        "⚠️ Redis pub/sub not available, retrying in 5s..."
                    )
                    time.sleep(5)
                    continue

                pubsub.subscribe(self.config.avatar_requests_channel)
                logger.info(
                    f"📡 Subscribed to {self.config.avatar_requests_channel}"
                )

                for message in pubsub.listen():
                    if not self._running:
                        break

                    if message["type"] == "message":
                        self._handle_message(message["data"])

            except Exception as e:
                logger.error(f"❌ Error in subscriber loop: {e}")
                time.sleep(5)  # Wait before reconnecting

    def _handle_message(self, message_data: str) -> None:
        """
        Handle incoming avatar request message.

        Args:
            message_data: JSON message string
        """
        try:
            # Parse and validate message
            message = AvatarRequestMessageFormatter.parse_avatar_request(
                message_data
            )
            request_id = message.get("message_id")
            payload = message.get("payload", {})

            logger.info(f"📨 Received avatar request: {request_id}")
            logger.debug(f"   Payload: {json.dumps(payload, indent=2)}")

            # Extract request details
            team1_id = payload.get("team1_id")
            team2_id = payload.get("team2_id")

            if not team1_id or not team2_id:
                logger.error("❌ Invalid request: missing team IDs")
                self._stats["failed_processed"] = (
                    self._stats.get("failed_processed", 0) + 1
                )
                return

            # Update stats
            self._stats["total_received"] = (
                self._stats.get("total_received", 0) + 1
            )
            self._stats["last_message_time"] = time.time()

            # Call the request handler (avatar creation logic)
            try:
                self.request_handler(request_id, payload)
                self._stats["successful_processed"] = (
                    self._stats.get("successful_processed", 0) + 1
                )
                logger.info(f"✅ Successfully processed request: {request_id}")
            except Exception as handler_error:
                logger.error(
                    f"❌ Error in request handler for {request_id}: {handler_error}"
                )
                self._stats["failed_processed"] = (
                    self._stats.get("failed_processed", 0) + 1
                )

        except ValueError as e:
            logger.error(f"❌ Invalid message format: {e}")
            self._stats["failed_processed"] = (
                self._stats.get("failed_processed", 0) + 1
            )
        except json.JSONDecodeError as e:
            logger.error(f"❌ Failed to parse message: {e}")
            self._stats["failed_processed"] = (
                self._stats.get("failed_processed", 0) + 1
            )
        except Exception as e:
            logger.error(f"❌ Error handling message: {e}")
            self._stats["failed_processed"] = (
                self._stats.get("failed_processed", 0) + 1
            )

    def get_stats(self) -> dict:
        """Get subscriber statistics."""
        return {
            "running": self._running,
            "stats": self._stats.copy(),
        }

