#!/usr/bin/env python3
"""
Message Formatter for Redis Integration

Provides message formatting utilities for Redis pub/sub integration.
"""

import json
import uuid
from datetime import datetime
from typing import Any, Dict, Optional


class AvatarRequestMessageFormatter:
    """Formats avatar request messages for Redis publishing."""

    @staticmethod
    def format_avatar_request(
        team1_id: str,
        team2_id: str,
        team1_organization_id: Optional[str] = None,
        team2_organization_id: Optional[str] = None,
        match_id: Optional[str] = None,
        priority: str = "normal",
        metadata: Optional[Dict] = None,
    ) -> str:
        """
        Format avatar request message for Redis publishing.

        Args:
            team1_id: First team ID
            team2_id: Second team ID
            team1_organization_id: First team organization ID (optional)
            team2_organization_id: Second team organization ID (optional)
            match_id: Match ID (optional)
            priority: Request priority (normal, high, critical)
            metadata: Additional metadata

        Returns:
            str: JSON formatted message
        """
        message = {
            "message_id": str(uuid.uuid4()),
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "source": "team-logo-combiner",
            "version": "1.0",
            "type": "avatar_request",
            "payload": {
                "team1_id": team1_id,
                "team2_id": team2_id,
                "priority": priority,
                "callback_channel": "fogis:avatars:results",
                "metadata": metadata or {},
            },
        }

        # Add optional fields
        if team1_organization_id:
            message["payload"]["team1_organization_id"] = team1_organization_id
        if team2_organization_id:
            message["payload"]["team2_organization_id"] = team2_organization_id
        if match_id:
            message["payload"]["match_id"] = match_id

        return json.dumps(message, ensure_ascii=False)

    @staticmethod
    def parse_avatar_request(message_data: str) -> Dict[str, Any]:
        """
        Parse avatar request message from Redis.

        Args:
            message_data: JSON message string

        Returns:
            Dict containing parsed message data

        Raises:
            ValueError: If message format is invalid
        """
        try:
            message = json.loads(message_data)

            # Validate required fields
            if "message_id" not in message:
                raise ValueError("Missing message_id field")
            if "payload" not in message:
                raise ValueError("Missing payload field")

            payload = message["payload"]
            if "team1_id" not in payload or "team2_id" not in payload:
                raise ValueError("Missing team IDs in payload")

            return message

        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON format: {e}")


class AvatarResultMessageFormatter:
    """Formats avatar result messages for Redis publishing."""

    @staticmethod
    def format_avatar_result(
        request_id: str,
        team1_id: str,
        team2_id: str,
        status: str,
        avatar_url: Optional[str] = None,
        avatar_data: Optional[str] = None,
        error_type: Optional[str] = None,
        error_message: Optional[str] = None,
        processing_time_ms: int = 0,
        metadata: Optional[Dict] = None,
    ) -> str:
        """
        Format avatar result message for Redis publishing.

        Args:
            request_id: Original request message ID
            team1_id: First team ID
            team2_id: Second team ID
            status: Result status (success, error)
            avatar_url: URL to avatar image (optional)
            avatar_data: Base64-encoded avatar data (optional)
            error_type: Error type if status is error
            error_message: Error message if status is error
            processing_time_ms: Processing time in milliseconds
            metadata: Additional metadata

        Returns:
            str: JSON formatted message
        """
        message = {
            "message_id": str(uuid.uuid4()),
            "request_id": request_id,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "source": "team-logo-combiner",
            "version": "1.0",
            "type": "avatar_result",
            "payload": {
                "status": status,
                "team1_id": team1_id,
                "team2_id": team2_id,
                "processing_time_ms": processing_time_ms,
                "metadata": metadata or {},
            },
        }

        # Add success-specific fields
        if status == "success":
            if avatar_url:
                message["payload"]["avatar_url"] = avatar_url
            if avatar_data:
                message["payload"]["avatar_data"] = avatar_data
        # Add error-specific fields
        else:
            message["payload"]["error_type"] = error_type or "Unknown"
            message["payload"]["error_message"] = error_message or "Unknown error"

        return json.dumps(message, ensure_ascii=False)

    @staticmethod
    def format_service_status(
        status: str, details: Optional[Dict] = None
    ) -> str:
        """
        Format service status message for Redis publishing.

        Args:
            status: Service status (started, running, stopped, error)
            details: Additional status details

        Returns:
            str: JSON formatted message
        """
        message = {
            "message_id": str(uuid.uuid4()),
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "source": "team-logo-combiner",
            "version": "1.0",
            "type": "service_status",
            "payload": {
                "status": status,
                "details": details or {},
            },
        }

        return json.dumps(message, ensure_ascii=False)

