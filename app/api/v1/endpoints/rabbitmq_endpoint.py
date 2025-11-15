"""RabbitMQ management endpoints."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
from aio_pika.exceptions import AMQPException

from app.config.logger_config import logger
from app.helper.rabbitmq_helper import RabbitMQHelper
from app.schema.rabbitmq_schema import (
    MessagePublishSchema,
    ExchangeSetupSchema,
    ExchangePublishSchema,
)
from app.schema.response_schema import ApiResponseSchema


router = APIRouter()


@router.post(
    "/rabbitmq/message/publish/",
    response_model=ApiResponseSchema[dict],
)
async def publish_message(payload: MessagePublishSchema):
    """
    Publish a message to a single RabbitMQ queue.
    
    Publishes a message directly to a queue. The queue will be created if it doesn't exist.
    Messages are persistent by default.
    
    Use this when you need to send a message to ONE specific queue.
    """
    try:
        rabbitmq_helper = RabbitMQHelper()
        
        success = await rabbitmq_helper.publish_message(
            queue_name=payload.queue_name,
            message=payload.message,
            priority=3
        )
        
        await rabbitmq_helper.close()
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to publish message"
            )
        
        return ApiResponseSchema[dict](
            success=True,
            data={"queue_name": payload.queue_name},
            message=f"Message published to queue '{payload.queue_name}'"
        )
        
    except HTTPException:
        raise
    except ConnectionError as e:
        logger.error(f"Connection error: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"RabbitMQ connection failed: {str(e)}"
        ) from e
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error: {str(e)}"
        ) from e


@router.post(
    "/rabbitmq/exchange/setup/",
    response_model=ApiResponseSchema[dict],
    status_code=status.HTTP_201_CREATED,
)
async def setup_exchange(payload: ExchangeSetupSchema):
    """
    Setup an exchange with multiple queues (one-time setup).
    
    This endpoint:
    1. Creates the exchange (fanout type for broadcasting)
    2. Creates all specified queues (if they don't exist)
    3. Binds all queues to the exchange
    
    After setup, use /rabbitmq/exchange/publish/ to broadcast messages.
    
    Use this for ONE-TIME SETUP when you want to broadcast messages to multiple queues.
    """
    try:
        rabbitmq_helper = RabbitMQHelper()
        
        # Create exchange
        await rabbitmq_helper.ensure_exchange_exists(
            exchange_name=payload.exchange_name,
            exchange_type="fanout",
            durable=True,
            auto_delete=False
        )
        
        # Create queues and bind them to the exchange
        bound_queues = []
        failed_queues = []
        
        for queue_name in payload.queue_names:
            try:
                # Create queue (always creates if doesn't exist)
                await rabbitmq_helper.ensure_queue_exists(queue_name)
                
                # Bind queue to exchange
                await rabbitmq_helper.bind_queue_to_exchange(
                    queue_name=queue_name,
                    exchange_name=payload.exchange_name,
                    routing_key=""
                )
                bound_queues.append(queue_name)
            except (AMQPException, ConnectionError) as e:
                logger.error(f"Failed to setup queue '{queue_name}': {e}")
                failed_queues.append(queue_name)
        
        await rabbitmq_helper.close()
        
        if len(bound_queues) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to setup any queues for exchange '{payload.exchange_name}'"
            )
        
        return ApiResponseSchema[dict](
            success=True,
            data={
                "exchange_name": payload.exchange_name,
                "bound_queues": bound_queues,
                "failed_queues": failed_queues,
                "total_queues": len(payload.queue_names),
                "successful": len(bound_queues),
                "failed": len(failed_queues)
            },
            message=f"Exchange '{payload.exchange_name}' setup complete with {len(bound_queues)} queues"
        )
        
    except HTTPException:
        raise
    except ConnectionError as e:
        logger.error(f"Connection error: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"RabbitMQ connection failed: {str(e)}"
        ) from e
    except AMQPException as e:
        logger.error(f"AMQP error: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to setup exchange: {str(e)}"
        ) from e
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error: {str(e)}"
        ) from e


@router.post(
    "/rabbitmq/exchange/publish/",
    response_model=ApiResponseSchema[dict],
)
async def publish_to_exchange(payload: ExchangePublishSchema):
    """
    Publish a message to an exchange (broadcasts to all bound queues).
    
    Publishes a message to the exchange, which automatically broadcasts it to 
    all queues that are bound to this exchange.
    
    IMPORTANT: The exchange must be set up first using /rabbitmq/exchange/setup/
    
    Use this when you want to BROADCAST a message to MULTIPLE queues.
    """
    try:
        rabbitmq_helper = RabbitMQHelper()
        
        # Publish message to exchange
        success = await rabbitmq_helper.publish_to_exchange(
            exchange_name=payload.exchange_name,
            message=payload.message,
            routing_key="",
            priority=3
        )
        
        await rabbitmq_helper.close()
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to publish message to exchange"
            )
        
        return ApiResponseSchema[dict](
            success=True,
            data={"exchange_name": payload.exchange_name},
            message=f"Message broadcast to all queues bound to exchange '{payload.exchange_name}'"
        )
        
    except HTTPException:
        raise
    except ConnectionError as e:
        logger.error(f"Connection error: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"RabbitMQ connection failed: {str(e)}"
        ) from e
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error: {str(e)}"
        ) from e
