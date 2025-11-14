"""RabbitMQ schemas for queue and message management."""
from __future__ import annotations

from typing import Any
from pydantic import BaseModel, Field


class MessagePublishSchema(BaseModel):
    """Schema for publishing a message to a single queue."""
    
    queue_name: str = Field(..., description="Name of the queue to publish to", example="orders_queue")
    message: dict[str, Any] | str = Field(
        ..., 
        description="Message content (dict or string)", 
        example="Order #12345 has been created"
    )


class ExchangeSetupSchema(BaseModel):
    """Schema for setting up an exchange with queues (one-time setup)."""
    
    exchange_name: str = Field(..., description="Name of the exchange to create", example="notifications")
    queue_names: list[str] = Field(
        ..., 
        min_length=1, 
        description="List of queue names to bind to exchange. Queues will be created if they don't exist.", 
        example=["email_queue", "sms_queue", "push_queue"]
    )


class ExchangePublishSchema(BaseModel):
    """Schema for publishing a message to an exchange (broadcasts to all bound queues)."""
    
    exchange_name: str = Field(..., description="Name of the exchange to publish to", example="notifications")
    message: dict[str, Any] | str = Field(
        ..., 
        description="Message to broadcast to all queues bound to this exchange", 
        example="User registered successfully"
    )


