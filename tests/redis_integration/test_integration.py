"""Integration tests for Redis pub/sub functionality."""

import json
import pytest
import time
from unittest.mock import Mock, patch, MagicMock
from src.redis_integration import (
    AvatarRequestSubscriber,
    AvatarResultPublisher,
    RedisConfig,
)


class TestRedisIntegration:
    """Test Redis pub/sub integration."""

    @patch('src.redis_integration.subscriber.RedisConnectionManager')
    @patch('src.redis_integration.publisher.RedisConnectionManager')
    def test_end_to_end_message_flow(
        self, mock_pub_connection_manager, mock_sub_connection_manager
    ):
        """Test complete message flow from request to result."""
        # Mock Redis clients
        mock_pub_client = Mock()
        mock_pub_client.publish.return_value = 1
        mock_pub_connection_manager.return_value.get_client.return_value = mock_pub_client
        mock_pub_connection_manager.return_value.config = RedisConfig()
        mock_pub_connection_manager.return_value.is_connected.return_value = True

        mock_sub_pubsub = Mock()
        mock_sub_connection_manager.return_value.get_pubsub.return_value = mock_sub_pubsub
        mock_sub_connection_manager.return_value.config = RedisConfig()

        # Track published results
        published_results = []

        def capture_publish(channel, message):
            published_results.append({"channel": channel, "message": json.loads(message)})
            return 1

        mock_pub_client.publish.side_effect = capture_publish

        # Create publisher and subscriber
        publisher = AvatarResultPublisher()
        
        received_requests = []

        def handle_request(request_id, payload):
            received_requests.append({"request_id": request_id, "payload": payload})
            # Simulate processing and publish result
            publisher.publish_avatar_result(
                request_id=request_id,
                team1_id=payload["team1_id"],
                team2_id=payload["team2_id"],
                status="success",
                avatar_data="base64data==",
                processing_time_ms=100,
            )

        subscriber = AvatarRequestSubscriber(handle_request)

        # Simulate receiving a request message
        request_message = {
            "message_id": "test-123",
            "payload": {"team1_id": "7557", "team2_id": "9590"},
        }
        subscriber._handle_message(json.dumps(request_message))

        # Verify request was received
        assert len(received_requests) == 1
        assert received_requests[0]["request_id"] == "test-123"
        assert received_requests[0]["payload"]["team1_id"] == "7557"

        # Verify result was published
        assert len(published_results) == 1
        result = published_results[0]
        assert result["channel"] == "fogis:avatars:results"
        assert result["message"]["request_id"] == "test-123"
        assert result["message"]["payload"]["status"] == "success"
        assert result["message"]["payload"]["team1_id"] == "7557"
        assert result["message"]["payload"]["team2_id"] == "9590"

    @patch('src.redis_integration.subscriber.RedisConnectionManager')
    @patch('src.redis_integration.publisher.RedisConnectionManager')
    def test_error_handling_in_message_flow(
        self, mock_pub_connection_manager, mock_sub_connection_manager
    ):
        """Test error handling in message flow."""
        # Mock Redis clients
        mock_pub_client = Mock()
        mock_pub_client.publish.return_value = 1
        mock_pub_connection_manager.return_value.get_client.return_value = mock_pub_client
        mock_pub_connection_manager.return_value.config = RedisConfig()
        mock_pub_connection_manager.return_value.is_connected.return_value = True

        mock_sub_connection_manager.return_value.config = RedisConfig()

        # Track published results
        published_results = []

        def capture_publish(channel, message):
            published_results.append({"channel": channel, "message": json.loads(message)})
            return 1

        mock_pub_client.publish.side_effect = capture_publish

        # Create publisher and subscriber
        publisher = AvatarResultPublisher()

        def handle_request_with_error(request_id, payload):
            # Simulate processing error
            publisher.publish_avatar_result(
                request_id=request_id,
                team1_id=payload["team1_id"],
                team2_id=payload["team2_id"],
                status="error",
                error={"type": "ImageProcessingError", "message": "Failed to process"},
                processing_time_ms=50,
            )

        subscriber = AvatarRequestSubscriber(handle_request_with_error)

        # Simulate receiving a request message
        request_message = {
            "message_id": "test-error",
            "payload": {"team1_id": "1111", "team2_id": "2222"},
        }
        subscriber._handle_message(json.dumps(request_message))

        # Verify error result was published
        assert len(published_results) == 1
        result = published_results[0]
        assert result["message"]["payload"]["status"] == "error"
        assert result["message"]["payload"]["error_type"] == "ImageProcessingError"
        assert result["message"]["payload"]["error_message"] == "Failed to process"

    @patch('src.redis_integration.publisher.RedisConnectionManager')
    def test_publisher_stats_tracking(self, mock_connection_manager):
        """Test that publisher tracks statistics correctly."""
        mock_client = Mock()
        mock_client.publish.return_value = 2
        mock_connection_manager.return_value.get_client.return_value = mock_client
        mock_connection_manager.return_value.config = RedisConfig()
        mock_connection_manager.return_value.is_connected.return_value = True

        publisher = AvatarResultPublisher()

        # Publish multiple results
        for i in range(3):
            publisher.publish_avatar_result(
                request_id=f"test-{i}",
                team1_id="7557",
                team2_id="9590",
                status="success",
                avatar_data="data",
                processing_time_ms=100,
            )

        stats = publisher.get_publishing_stats()
        assert stats["redis_enabled"] is True
        assert stats["redis_connected"] is True
        assert stats["publishing_stats"]["total_published"] == 3
        assert stats["publishing_stats"]["successful_publishes"] == 3
        assert stats["publishing_stats"]["failed_publishes"] == 0

    @patch('src.redis_integration.subscriber.RedisConnectionManager')
    def test_subscriber_stats_tracking(self, mock_connection_manager):
        """Test that subscriber tracks statistics correctly."""
        mock_connection_manager.return_value.config = RedisConfig()

        handler = Mock()
        subscriber = AvatarRequestSubscriber(handler)

        # Process multiple messages
        for i in range(5):
            message = {
                "message_id": f"test-{i}",
                "payload": {"team1_id": "7557", "team2_id": "9590"},
            }
            subscriber._handle_message(json.dumps(message))

        stats = subscriber.get_stats()
        assert stats["stats"]["total_received"] == 5
        assert stats["stats"]["successful_processed"] == 5
        assert stats["stats"]["failed_processed"] == 0

    @patch('src.redis_integration.subscriber.RedisConnectionManager')
    def test_subscriber_handles_invalid_messages(self, mock_connection_manager):
        """Test that subscriber handles invalid messages gracefully."""
        mock_connection_manager.return_value.config = RedisConfig()

        handler = Mock()
        subscriber = AvatarRequestSubscriber(handler)

        # Send invalid JSON
        subscriber._handle_message("invalid json{")

        # Send message missing required fields
        subscriber._handle_message(json.dumps({"message_id": "test"}))

        # Send message missing team IDs
        subscriber._handle_message(
            json.dumps({"message_id": "test", "payload": {"team1_id": "7557"}})
        )

        # Handler should not have been called
        handler.assert_not_called()

        # All should be counted as failed
        stats = subscriber.get_stats()
        assert stats["stats"]["failed_processed"] == 3
        assert stats["stats"]["successful_processed"] == 0

    @patch('src.redis_integration.publisher.RedisConnectionManager')
    def test_publisher_graceful_degradation(self, mock_connection_manager):
        """Test publisher graceful degradation when Redis is unavailable."""
        # Simulate Redis unavailable
        mock_connection_manager.return_value.get_client.return_value = None
        mock_connection_manager.return_value.config = RedisConfig()

        publisher = AvatarResultPublisher()
        result = publisher.publish_avatar_result(
            request_id="test-123",
            team1_id="7557",
            team2_id="9590",
            status="success",
            avatar_data="data",
            processing_time_ms=100,
        )

        # Should fail gracefully
        assert result.success is False
        assert result.error == "Redis client not available"

    @patch('src.redis_integration.publisher.RedisConnectionManager')
    def test_publisher_when_disabled(self, mock_connection_manager):
        """Test publisher when Redis is disabled."""
        mock_config = RedisConfig(enabled=False)
        mock_connection_manager.return_value.config = mock_config

        publisher = AvatarResultPublisher()
        result = publisher.publish_avatar_result(
            request_id="test-123",
            team1_id="7557",
            team2_id="9590",
            status="success",
            avatar_data="data",
            processing_time_ms=100,
        )

        # Should succeed but not actually publish
        assert result.success is True
        assert result.subscribers_notified == 0

    @patch('src.redis_integration.subscriber.RedisConnectionManager')
    def test_subscriber_when_disabled(self, mock_connection_manager):
        """Test subscriber when Redis is disabled."""
        mock_config = RedisConfig(enabled=False)
        mock_connection_manager.return_value.config = mock_config

        handler = Mock()
        subscriber = AvatarRequestSubscriber(handler)
        subscriber.start()

        # Should not start
        assert subscriber._running is False
        assert subscriber._thread is None

