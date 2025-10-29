import re
from contextvars import ContextVar
from typing import Optional, Dict, Any
from uuid import uuid4
import threading
import sys
import json
import asyncio
import queue
import aio_pika
from loguru import logger
from app.config.baseapp_config import get_base_config

# Context variables
user_id_context: ContextVar[Optional[str]] = ContextVar('user_id', default=None)
workspace_id_context: ContextVar[Optional[str]] = ContextVar('workspace_id', default=None)
correlation_id_context: ContextVar[Optional[str]] = ContextVar('correlation_id', default=None)


def validate_log_message(log_message: Dict[str, Any]) -> bool:
    """Validate log message structure and content"""
    required_fields = ["service_name", "log_type", "timestamp", "message", "level"]
    valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
    valid_types = ["user_activity", "central_log", "all"]
    
    # Check required fields
    if not all(field in log_message for field in required_fields):
        return False
    
    # Check log level validity
    if log_message.get("level", "").upper() not in valid_levels:
        return False
    
    # Check log type validity
    if log_message.get("log_type") not in valid_types:
        return False
    
    # Check message size (max 10KB)
    message_str = str(log_message.get("message", ""))
    if len(message_str.encode('utf-8')) > 10240:
        return False
    
    return True


def _get_context_info() -> Dict[str, Optional[str]]:
    """Get current logging context from context variables"""
    return {
        "user_id": user_id_context.get(),
        "workspace_id": workspace_id_context.get(),
        "correlation_id": correlation_id_context.get()
    }


def _create_context_string(context: Dict[str, Optional[str]]) -> str:
    """Create context string for log messages"""
    context_info = []
    for key, value in context.items():
        if value:
            context_info.append(f"{key}={value}")
    return f" [{', '.join(context_info)}]" if context_info else ""


def _parse_log_message(message: str) -> tuple[str, str, str, str, str, str, str]:
    """Parse loguru message format and extract components"""
    # Parse loguru message format: "time | level | location - message"
    parts = message.split(" | ", 2)
    if len(parts) < 3:
        return "", "", "", "", "", "", ""
    
    time_str, level, location_and_message = parts
    level = level.strip()
    
    # Split location and message by " - "
    if " - " in location_and_message:
        location, message_text = location_and_message.split(" - ", 1)
    else:
        location = location_and_message
        message_text = ""
    
    message_text = message_text.strip()
    
    # Parse location
    location_parts = location.split(":")
    name = location_parts[0] if len(location_parts) > 0 else ""
    function = location_parts[1] if len(location_parts) > 1 else ""
    line = int(location_parts[2]) if len(location_parts) > 2 and location_parts[2].isdigit() else 0
    
    return time_str, level, name, function, str(line), message_text, location


def _extract_context_from_message(message_text: str) -> tuple[str, str, str, str, str]:
    """Extract context information from message and return cleaned message"""
    user_id = None
    workspace_id = None
    correlation_id = None
    action_type = "general"
    
    # Check if message contains context information in format [user_id=xxx, workspace_id=yyy, correlation_id=zzz]
    context_match = re.search(r'\[([^\]]+)\]$', message_text)
    if context_match:
        context_str = context_match.group(1)
        # Parse individual context values
        for item in context_str.split(', '):
            if '=' in item:
                key, value = item.split('=', 1)
                if key == 'user_id':
                    user_id = value
                elif key == 'workspace_id':
                    workspace_id = value
                elif key == 'correlation_id':
                    correlation_id = value
                elif key == 'action_type':
                    action_type = value
        # Remove context from message text
        message_text = re.sub(r' \[[^\]]+\]$', '', message_text)
    
    # Check if message starts with [action_type] pattern
    action_match = re.match(r'^\[([^\]]+)\]\s*(.*)$', message_text)
    if action_match:
        action_type = action_match.group(1)
        message_text = action_match.group(2)
    
    return message_text, user_id, workspace_id, correlation_id, action_type


def _create_log_message(
    log_type: str,
    message_text: str,
    level: str,
    time_str: str,
    user_id: Optional[str] = None,
    workspace_id: Optional[str] = None,
    correlation_id: Optional[str] = None,
    action_type: str = "general",
    priority: int = 3
) -> Dict[str, Any]:
    """Create structured log message based on type"""
    config = get_base_config()
    
    base_message = {
        "service_name": config.SERVICE_NAME or "workspace-management-service",
        "log_type": log_type,
        "correlation_id": correlation_id or str(uuid4()),
        "timestamp": time_str + "Z",
        "message": message_text,
        "level": level.upper(),
        "action_type": action_type,
        "priority": priority
    }
    
    # Add optional fields based on log type
    if log_type in ["user_activity", "all"] and user_id:
        base_message["user_id"] = user_id
    if log_type in ["user_activity", "all"] and workspace_id:
        base_message["workspace_id"] = workspace_id
    
    return base_message

class QueueLogHandler:
    """Simplified queue log handler with connection pooling"""
    
    def __init__(self):
        self.config = get_base_config()
        self._connection = None
        self._log_queue = queue.Queue()
        self._worker_thread = None
        self._stop_event = threading.Event()
    
    async def _ensure_connection(self):
        """Ensure we have a working connection"""
        if self._connection is None or self._connection.is_closed:
            try:
                self._connection = await aio_pika.connect_robust(self.config.RABBITMQ_URL)
            except (aio_pika.exceptions.AMQPException, ConnectionError) as e:
                print(f"Failed to connect to RabbitMQ: {e}", file=sys.stderr)
                self._connection = None # Ensure connection is None on failure
                raise
    
    def write(self, message: str):
        """Write method called by loguru - simplified version"""
        try:
            # Parse and process message
            time_str, level, _, _, _, message_text, _ = _parse_log_message(message)
            if not time_str:
                return
            
            # Determine log type
            if message_text.startswith("USER_ACTIVITY:"):
                message_text = message_text.replace("USER_ACTIVITY: ", "")
                log_type = "user_activity"
                priority = 5
            elif message_text.startswith("ALL_LOG:"):
                message_text = message_text.replace("ALL_LOG: ", "")
                log_type = "all"
                priority = 8
            elif message_text.startswith("CENTRAL:"):
                message_text = message_text.replace("CENTRAL: ", "")
                log_type = "central_log"
                priority = 3
            else:
                log_type = "central_log"
                priority = 3
            
            # Extract context
            message_text, msg_user_id, msg_workspace_id, msg_correlation_id, msg_action_type = _extract_context_from_message(message_text)
            context = _get_context_info()
            
            # Create log message
            log_message = _create_log_message(
                log_type=log_type,
                message_text=message_text,
                level=level,
                time_str=time_str,
                user_id=msg_user_id or context["user_id"],
                workspace_id=msg_workspace_id or context["workspace_id"],
                correlation_id=msg_correlation_id or context["correlation_id"],
                action_type=msg_action_type or "general",
                priority=priority
            )
            
            # Send asynchronously
            if validate_log_message(log_message):
                self._log_queue.put(log_message)
                
        except (ValueError, TypeError, AttributeError, KeyError) as e:
            print(f"Error processing log: {e}", file=sys.stderr)
    
    def _worker(self):
        """The worker method that runs in a separate thread."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(self._run())
        finally:
            loop.run_until_complete(loop.shutdown_asyncgens())
            loop.close()

    async def _run(self):
        """The async part of the worker, runs the main loop."""
        while not self._stop_event.is_set():
            try:
                log_message = self._log_queue.get(timeout=0.1)
                await self._send_message(log_message)
                self._log_queue.task_done()
            except queue.Empty:
                continue
            except (ConnectionError, ValueError, TypeError, RuntimeError, OSError) as e:
                print(f"Error in log worker: {e}", file=sys.stderr)

    async def _send_message(self, log_message: dict):
        """Send a single log message to RabbitMQ."""
        try:
            await self._ensure_connection()
            if self._connection:
                async with self._connection.channel() as channel:
                    await channel.default_exchange.publish(
                        aio_pika.Message(
                            body=json.dumps(log_message).encode(),
                            delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
                            priority=log_message.get("priority", 3),
                        ),
                        routing_key="log_queue",
                    )
        except (ConnectionError, ValueError, TypeError, RuntimeError, OSError) as e:
            print(f"Failed to send log to queue: {e}", file=sys.stderr)

    async def _close_connection(self):
        if self._connection and not self._connection.is_closed:
            await self._connection.close()

    def start(self):
        """Starts the background worker thread."""
        self._worker_thread = threading.Thread(target=self._worker, daemon=True)
        self._worker_thread.start()

    def stop(self):
        """Stops the background worker thread."""
        self._log_queue.join() # Wait for all logs to be processed
        self._stop_event.set()
        if self._worker_thread:
            self._worker_thread.join()
        if self._connection:
            # We need a loop to close the async connection
            asyncio.run(self._close_connection())


# Global handler instance for proper connection management
_GLOBAL_QUEUE_HANDLER = None

def configure_logging() -> None:
    """Configure logging with queue integration"""
    global _GLOBAL_QUEUE_HANDLER  # pylint: disable=global-statement
    config = get_base_config()

    logger.remove()

    # Console handler
    logger.add(
        sys.stdout,
        level="INFO",
        backtrace=False,
        diagnose=False,
        enqueue=True,  # Keep console logs enqueued for performance
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level:<8} | {name}:{function}:{line} - {message}",
    )

    # Conditionally add queue handler
    if config.QUEUE_LOG:
        _GLOBAL_QUEUE_HANDLER = QueueLogHandler()
        _GLOBAL_QUEUE_HANDLER.start()
        logger.add(
            _GLOBAL_QUEUE_HANDLER,
            level="INFO",
            backtrace=False,
            diagnose=False,
            enqueue=True,
            format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level:<8} | {name}:{function}:{line} - {message}",
        )

async def shutdown_logging() -> None:
    """Gracefully shutdown logging and close RabbitMQ connection"""
    global _GLOBAL_QUEUE_HANDLER  # pylint: disable=global-statement
    
    if _GLOBAL_QUEUE_HANDLER:
        _GLOBAL_QUEUE_HANDLER.stop()
        _GLOBAL_QUEUE_HANDLER = None
        print("Logging system shutdown completed", file=sys.stderr)

def get_logger_context(user_id: str = "", workspace_id: str = "", correlation_id: str = ""):
    """
    Configure logging context for the current request
    
    Args:
        user_id: User ID for user activity logs
        workspace_id: Workspace ID for user activity logs  
        correlation_id: Correlation ID for request tracing
    """
    # Always set the context variables, even if they're empty strings
    # This ensures the context is properly initialized for the request
    user_id_context.set(user_id)
    workspace_id_context.set(workspace_id)
    correlation_id_context.set(correlation_id)


def _log_with_context(message: str, log_type: str, level: str = "info", exc_info: bool = False):
    """Internal function to log with context - reduces code duplication"""
    context = _get_context_info()
    context_str = _create_context_string(context)
    
    # Get the appropriate logger method
    log_level = level.lower()
    log_method = getattr(logger, log_level, logger.info)
    
    # Log with context information embedded in the message
    if exc_info:
        log_method(f"{log_type}: {{message}}{context_str}", message=message, exc_info=True)
    else:
        log_method(f"{log_type}: {{message}}{context_str}", message=message)


def log_user_activity(message: str, action_type: str = "general", level: str = "info", exc_info: bool = False):
    """
    Log user activity - goes to user_activities table only
    
    Args:
        message: The log message
        action_type: Type of action performed
        level: Log level ("info", "debug", "warning", "error", "critical")
        exc_info: Whether to include exception info in the log
    """
    _log_with_context(f"[{action_type}] {message}", "USER_ACTIVITY", level, exc_info)


def log_all(message: str, action_type: str = "general", level: str = "info", exc_info: bool = False):
    """
    Log important events - goes to BOTH tables (user_activities + central_logs)
    
    Args:
        message: The log message
        action_type: Type of action performed
        level: Log level ("info", "debug", "warning", "error", "critical")
        exc_info: Whether to include exception info in the log
    """
    _log_with_context(f"[{action_type}] {message}", "ALL_LOG", level, exc_info)


def log_central(message: str, level: str = "info", exc_info: bool = False):
    """
    Log central system events - goes to central_logs table only
    
    Args:
        message: The log message
        level: Log level ("info", "debug", "warning", "error", "critical")
        exc_info: Whether to include exception info in the log
    """
    _log_with_context(message, "CENTRAL", level, exc_info)