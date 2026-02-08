from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status as http_status

from sqlalchemy.ext.asyncio import AsyncSession

from app.config.database import get_async_db

from app.config.constants import SuccessMessages, ApiErrorMessages

from app.helper.fastapi.get_header import get_user_id

from app.schema.response_schema import ApiResponseSchema

from app.schema.user_schema import (
    UserSignupSchema,
    UserLoginSchema,
    UserReadSchema,
    UserLoginResponseSchema,
    UserLogoutSchema,
)

from app.service.user_service import UserService

from app.exception.user_exception import (
    UserNotFoundException,
    UserAlreadyExistsException,
    UserCreationException,
    InvalidCredentialsException,
    UserInactiveException,
    UserNotLoggedInException,
)

from app.exception.baseapp_exception import InternalServerErrorException

router = APIRouter()


# ==================== AUTHENTICATION ENDPOINTS ====================


@router.post(
    "/auth/signup/",
    response_model=ApiResponseSchema[UserReadSchema],
    status_code=http_status.HTTP_201_CREATED,
)
async def signup(
    payload: UserSignupSchema,
    db: AsyncSession = Depends(get_async_db),
):
    """
    Register a new user.

    This endpoint allows registering a new user account with email, username, and password.
    A workspace_id will be automatically generated for the user.
    """
    try:
        data = await UserService(db).signup(payload=payload)

        return ApiResponseSchema[UserReadSchema](
            success=True, data=data, message=SuccessMessages.USER_CREATED
        )

    except (
        UserCreationException,
        UserAlreadyExistsException,
        InternalServerErrorException,
    ) as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from e
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"{ApiErrorMessages.USER_CREATION_FAILED}: {str(e)}",
        ) from e


@router.post(
    "/auth/login/",
    response_model=ApiResponseSchema[UserLoginResponseSchema],
    status_code=http_status.HTTP_200_OK,
)
async def login(
    payload: UserLoginSchema,
    db: AsyncSession = Depends(get_async_db),
):
    """
    Authenticate user and get access token.

    This endpoint authenticates the user with email and password,
    and returns the user_id, workspace_id, and access token.
    """
    try:
        data = await UserService(db).login(payload=payload)

        return ApiResponseSchema[UserLoginResponseSchema](
            success=True, data=data, message=SuccessMessages.USER_LOGIN_SUCCESS
        )

    except (
        InvalidCredentialsException,
        UserInactiveException,
        UserNotFoundException,
    ) as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from e
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"{ApiErrorMessages.USER_LOGIN_FAILED}: {str(e)}",
        ) from e


@router.post(
    "/auth/logout/",
    response_model=ApiResponseSchema[UserLogoutSchema],
    status_code=http_status.HTTP_200_OK,
)
async def logout(
    db: AsyncSession = Depends(get_async_db),
    user_id: UUID = Depends(get_user_id),
):
    """
    Logout the currently authenticated user.

    This endpoint logs out the user by invalidating their session.
    Requires the user-id header.
    """
    try:
        data = await UserService(db).logout(user_id=user_id)

        return ApiResponseSchema[UserLogoutSchema](
            success=True, data=data, message=SuccessMessages.USER_LOGOUT_SUCCESS
        )

    except (
        UserNotFoundException,
        UserNotLoggedInException,
    ) as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from e
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"{ApiErrorMessages.USER_LOGOUT_FAILED}: {str(e)}",
        ) from e
