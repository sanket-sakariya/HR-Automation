"""
Universal RabbitMQ Helper for Queue Management and Message Publishing

This helper provides a reusable interface for managing RabbitMQ connections,
queue operations, and message publishing. It can be easily copied to other
projects by just configuring queue names in the config file.

Usage:
    from app.helper.rabbitmq_helper import RabbitMQHelper
    
    # Initialize helper
    rabbitmq_helper = RabbitMQHelper()
    
    # Ensure queue exists (creates if doesn't exist)
    await rabbitmq_helper.ensure_queue_exists("my_queue_name")
    
    # Publish a message
    await rabbitmq_helper.publish_message(
        queue_name="my_queue",
        message={"key": "value"}
    )
    
    # Close connection when done
    await rabbitmq_helper.close()
"""
from __future__ import annotations
from typing import Optional, Dict, Any, Union
import json
import asyncio
import aio_pika
from aio_pika import Connection, Channel, Queue, DeliveryMode
from aio_pika.exceptions import AMQPException
import sys

from app.config.baseapp_config import get_base_config
from app.config.logger_config import logger


class RabbitMQHelper:
    """
    Universal RabbitMQ helper for managing connections and queues.
    
    This class provides a reusable interface for RabbitMQ operations that can
    be easily ported to other projects by just updating the config.
    """
    
    def __init__(self, rabbitmq_url: Optional[str] = None):
        """
        Initialize RabbitMQ helper.
        
        Args:
            rabbitmq_url: Optional RabbitMQ URL. If not provided, uses config.RABBITMQ_URL
        """
        self.config = get_base_config()
        self.rabbitmq_url = rabbitmq_url or self.config.RABBITMQ_URL
        self._connection: Optional[Connection] = None
        self._channel: Optional[Channel] = None
        self._queues: Dict[str, Queue] = {}
    
    async def _ensure_connection(self) -> Connection:
        """
        Ensure RabbitMQ connection exists and is open.
        
        Returns:
            Active RabbitMQ connection
            
        Raises:
            ConnectionError: If connection cannot be established
        """
        if self._connection is None or self._connection.is_closed:
            try:
                self._connection = await aio_pika.connect_robust(self.rabbitmq_url)
                logger.info("RabbitMQ connection established")
            except (AMQPException, ConnectionError) as e:
                error_msg = f"Failed to connect to RabbitMQ: {e}"
                logger.error(error_msg)
                print(error_msg, file=sys.stderr)
                self._connection = None
                raise ConnectionError(error_msg) from e
        
        return self._connection
    
    async def _ensure_channel(self) -> Channel:
        """
        Ensure RabbitMQ channel exists and is open.
        
        Returns:
            Active RabbitMQ channel
            
        Raises:
            ConnectionError: If connection or channel cannot be established
        """
        await self._ensure_connection()
        
        if self._channel is None or self._channel.is_closed:
            try:
                self._channel = await self._connection.channel()
                logger.debug("RabbitMQ channel created")
            except (AMQPException, ConnectionError) as e:
                error_msg = f"Failed to create RabbitMQ channel: {e}"
                logger.error(error_msg)
                print(error_msg, file=sys.stderr)
                self._channel = None
                raise ConnectionError(error_msg) from e
        
        return self._channel
    
    async def ensure_queue_exists(
        self,
        queue_name: str,
        durable: bool = True,
        exclusive: bool = False,
        auto_delete: bool = False,
        arguments: Optional[Dict[str, Any]] = None
    ) -> Queue:
        """
        Ensure a queue exists, connecting to existing queue if available, creating it if necessary.
        
        By default, queues are created as DURABLE (permanent storage) to ensure
        they survive RabbitMQ broker restarts. This is the recommended setting
        for production use.
        
        This method first checks if the queue already exists in RabbitMQ. If it does,
        it connects directly to the existing queue. If not, it creates a new queue
        with the specified parameters.
        
        Args:
            queue_name: Name of the queue
            durable: If True, queue survives broker restart (default: True for permanent storage)
            exclusive: If True, queue is only accessible by the current connection (default: False)
            auto_delete: If True, queue is deleted when no longer used (default: False for permanent storage)
            arguments: Optional queue arguments
            
        Returns:
            Queue object
            
        Raises:
            ConnectionError: If connection cannot be established
            AMQPException: If queue creation fails or queue exists with incompatible arguments
        """
        # Check if queue already exists in cache
        if queue_name in self._queues:
            queue = self._queues[queue_name]
            if not queue.channel.is_closed:
                logger.debug(f"Using cached queue '{queue_name}'")
                return queue
        
        try:
            channel = await self._ensure_channel()
            
            # First, try to connect to existing queue (passive=True means don't create, just check)
            try:
                existing_queue = await channel.declare_queue(queue_name, passive=True)
                # Queue exists, use it directly
                self._queues[queue_name] = existing_queue
                logger.info(f"Connected to existing queue '{queue_name}' (durable={existing_queue.durable}, exclusive={existing_queue.exclusive}, auto_delete={existing_queue.auto_delete}, arguments={existing_queue.arguments})")
                return existing_queue
            except AMQPException:
                # Queue doesn't exist, will create it below
                pass
            
            # Queue doesn't exist, create it with specified parameters
            queue = await channel.declare_queue(
                queue_name,
                durable=durable,
                exclusive=exclusive,
                auto_delete=auto_delete,
                arguments=arguments or {}
            )
            
            # Cache the queue
            self._queues[queue_name] = queue
            
            logger.info(f"Created new queue '{queue_name}' (durable={durable}, exclusive={exclusive}, auto_delete={auto_delete}, arguments={arguments})")
            
            return queue
            
        except AMQPException as e:
            error_str = str(e)
            # Handle case where queue exists with different arguments
            if "PRECONDITION_FAILED" in error_str and "inequivalent arg" in error_str:
                # Try to get existing queue info to provide better error message
                try:
                    queue_info = await self.get_queue_info(queue_name)
                    if queue_info:
                        error_msg = (
                            f"Queue '{queue_name}' already exists with different arguments. "
                            f"Existing queue arguments: {queue_info.get('arguments', {})}. "
                            f"Requested arguments: {arguments or {}}. "
                            f"Please delete the existing queue or use matching arguments."
                        )
                        logger.error(error_msg)
                        raise AMQPException(error_msg) from e
                except Exception:
                    pass  # Fall through to original error
            
            error_msg = f"Failed to ensure queue '{queue_name}': {e}"
            logger.error(error_msg)
            raise AMQPException(error_msg) from e
        except ConnectionError as e:
            error_msg = f"Failed to ensure queue '{queue_name}': {e}"
            logger.error(error_msg)
            raise ConnectionError(error_msg) from e
    
    async def delete_queue(self, queue_name: str, if_unused: bool = False, if_empty: bool = False) -> None:
        """
        Delete a queue.
        
        Args:
            queue_name: Name of the queue to delete
            if_unused: Only delete if queue has no consumers
            if_empty: Only delete if queue is empty
            
        Raises:
            ConnectionError: If connection cannot be established
            AMQPException: If queue deletion fails
        """
        try:
            channel = await self._ensure_channel()
            await channel.queue_delete(queue_name, if_unused=if_unused, if_empty=if_empty)
            
            # Remove from cache
            if queue_name in self._queues:
                del self._queues[queue_name]
            
            logger.info(f"Queue '{queue_name}' deleted")
            
        except (AMQPException, ConnectionError) as e:
            error_msg = f"Failed to delete queue '{queue_name}': {e}"
            logger.error(error_msg)
            raise AMQPException(error_msg) from e
    
    async def get_queue_info(self, queue_name: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a queue.
        
        Args:
            queue_name: Name of the queue
            
        Returns:
            Dictionary with queue information or None if queue doesn't exist
            
        Raises:
            ConnectionError: If connection cannot be established
        """
        try:
            channel = await self._ensure_channel()
            queue = await channel.declare_queue(queue_name, passive=True)
            
            return {
                "name": queue.name,
                "durable": queue.durable,
                "exclusive": queue.exclusive,
                "auto_delete": queue.auto_delete,
                "arguments": queue.arguments
            }
            
        except AMQPException:
            # Queue doesn't exist
            return None
        except ConnectionError as e:
            error_msg = f"Failed to get queue info for '{queue_name}': {e}"
            logger.error(error_msg)
            raise
    
    def is_connected(self) -> bool:
        """
        Check if RabbitMQ connection is active.
        
        Returns:
            True if connected, False otherwise
        """
        return self._connection is not None and not self._connection.is_closed
    
    async def close(self) -> None:
        """
        Close RabbitMQ connection and channel.
        
        This should be called when the helper is no longer needed,
        typically during application shutdown.
        """
        try:
            # Clear queue cache first to prevent new operations
            self._queues.clear()
            
            # Close channel first (channel must be closed before connection)
            if self._channel and not self._channel.is_closed:
                try:
                    # Close the channel and wait for it to complete
                    await self._channel.close()
                    # Give time for internal cleanup coroutines to complete
                    await asyncio.sleep(0.2)
                except Exception as e:
                    logger.warning(f"Error closing channel: {e}")
                finally:
                    self._channel = None
                    logger.debug("RabbitMQ channel closed")
            
            # Close connection (must be closed after channel)
            if self._connection and not self._connection.is_closed:
                try:
                    # Close the connection and wait for it to complete
                    await self._connection.close()
                    # Give time for internal cleanup coroutines to complete
                    await asyncio.sleep(0.2)
                except Exception as e:
                    logger.warning(f"Error closing connection: {e}")
                finally:
                    self._connection = None
                    logger.info("RabbitMQ connection closed")
            
        except Exception as e:
            error_msg = f"Error closing RabbitMQ connection: {e}"
            logger.error(error_msg)
            print(error_msg, file=sys.stderr)
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self._ensure_connection()
        return self
    
    async def initialize_queues_from_config(self) -> Dict[str, Queue]:
        """
        Initialize queues from config.RABBITMQ_QUEUE_NAMES.
        
        Parses comma-separated queue names from config and ensures they all exist.
        All queues are created as DURABLE (permanent storage) to survive broker restarts.
        
        Returns:
            Dictionary mapping queue names to Queue objects
            
        Raises:
            ConnectionError: If connection cannot be established
            AMQPException: If queue creation fails
        """
        queue_names_str = self.config.RABBITMQ_QUEUE_NAMES or ""
        queue_names = [name.strip() for name in queue_names_str.split(",") if name.strip()]
        
        initialized_queues = {}
        
        for queue_name in queue_names:
            # Always create queues as durable (permanent storage) and non-auto-delete
            # Set x-max-priority for log_queue to support message priorities
            queue_args = {}
            if queue_name == "log_queue":
                queue_args = {"x-max-priority": 10}  # Support message priorities up to 10
            
            queue = await self.ensure_queue_exists(
                queue_name=queue_name,
                durable=True,  # Permanent storage - survives broker restart
                exclusive=False,  # Accessible by multiple connections
                auto_delete=False,  # Permanent - not deleted when unused
                arguments=queue_args if queue_args else None
            )
            initialized_queues[queue_name] = queue
        
        logger.info(f"Initialized {len(initialized_queues)} durable queues from config: {', '.join(initialized_queues.keys())}")
        
        return initialized_queues
    
    async def publish_message(
        self,
        queue_name: str,
        message: Union[Dict[str, Any], str],
        priority: int = 3,
        delivery_mode: DeliveryMode = DeliveryMode.PERSISTENT,
        exchange: Optional[str] = None,
        routing_key: Optional[str] = None,
        headers: Optional[Dict[str, Any]] = None,
        ensure_queue: bool = True,
        queue_durable: bool = True
    ) -> bool:
        """
        Publish a message to a RabbitMQ queue.
        
        By default, messages are published as PERSISTENT (permanent storage) to ensure
        they survive RabbitMQ broker restarts. Queues are also created as DURABLE by default.
        This is the recommended setting for production use.
        
        Args:
            queue_name: Name of the queue to publish to
            message: Message to publish (dict or string). If dict, will be JSON-encoded
            priority: Message priority (0-255, higher = more important)
            delivery_mode: Message delivery mode (default: PERSISTENT for permanent storage)
            exchange: Optional exchange name. If None, uses default exchange
            routing_key: Optional routing key. If None, uses queue_name
            headers: Optional message headers
            ensure_queue: If True, ensures queue exists before publishing (default: True)
            queue_durable: If True, queue will be durable/permanent (default: True)
            
        Returns:
            True if message was published successfully, False otherwise
            
        Raises:
            ConnectionError: If connection cannot be established
            AMQPException: If publishing fails
        """
        try:
            # Ensure queue exists if requested (always create as durable/permanent by default)
            if ensure_queue:
                await self.ensure_queue_exists(
                    queue_name=queue_name,
                    durable=queue_durable,  # Permanent storage - survives broker restart
                    exclusive=False,  # Accessible by multiple connections
                    auto_delete=False  # Permanent - not deleted when unused
                )
            
            # Get channel
            channel = await self._ensure_channel()
            
            # Prepare message body
            if isinstance(message, dict):
                body = json.dumps(message).encode('utf-8')
            elif isinstance(message, str):
                body = message.encode('utf-8')
            else:
                # Try to serialize as JSON
                body = json.dumps(message).encode('utf-8')
            
            # Create message
            aio_message = aio_pika.Message(
                body=body,
                delivery_mode=delivery_mode,
                priority=priority,
                headers=headers or {}
            )
            
            # Determine exchange and routing key
            if exchange:
                # Use specified exchange
                exchange_obj = await channel.get_exchange(exchange)
                await exchange_obj.publish(aio_message, routing_key=routing_key or queue_name)
            else:
                # Use default exchange
                await channel.default_exchange.publish(
                    aio_message,
                    routing_key=routing_key or queue_name
                )
            
            logger.debug(f"Message published to queue '{queue_name}' (priority={priority}, size={len(body)} bytes)")
            return True
            
        except (AMQPException, ConnectionError, json.JSONEncodeError) as e:
            error_msg = f"Failed to publish message to queue '{queue_name}': {e}"
            logger.error(error_msg)
            print(error_msg, file=sys.stderr)
            return False
    
    async def publish_batch(
        self,
        queue_name: str,
        messages: list[Union[Dict[str, Any], str]],
        priority: int = 3,
        delivery_mode: DeliveryMode = DeliveryMode.PERSISTENT,
        ensure_queue: bool = True,
        queue_durable: bool = True
    ) -> int:
        """
        Publish multiple messages to a RabbitMQ queue in a batch.
        
        By default, messages are published as PERSISTENT (permanent storage) and
        queues are created as DURABLE to ensure they survive broker restarts.
        
        Args:
            queue_name: Name of the queue to publish to
            messages: List of messages to publish
            priority: Message priority for all messages (0-255)
            delivery_mode: Message delivery mode (default: PERSISTENT for permanent storage)
            ensure_queue: If True, ensures queue exists before publishing (default: True)
            queue_durable: If True, queue will be durable/permanent (default: True)
            
        Returns:
            Number of messages successfully published
        """
        published_count = 0
        
        for message in messages:
            success = await self.publish_message(
                queue_name=queue_name,
                message=message,
                priority=priority,
                delivery_mode=delivery_mode,
                ensure_queue=ensure_queue if published_count == 0 else False,  # Only ensure once
                queue_durable=queue_durable
            )
            
            if success:
                published_count += 1
        
        logger.info(f"Published {published_count}/{len(messages)} messages to queue '{queue_name}'")
        return published_count
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()

