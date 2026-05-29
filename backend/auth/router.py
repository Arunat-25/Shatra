"""Маршруты /api/auth."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth import service
from backend.auth.dependencies import get_current_user, get_current_user_public
from backend.auth.schemas import (
    ChangePasswordRequest,
    DistrictsResponse,
    LoginRequest,
    MessageResponse,
    ProfileUpdateRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    UserPublic,
)
from backend.db.models import User
from backend.db.session import get_db

router = APIRouter(tags=["auth"])


@router.get("/districts", response_model=DistrictsResponse)
async def districts():
    return DistrictsResponse(districts=service.list_districts())


@router.post("/register", response_model=TokenResponse)
async def register(body: RegisterRequest, db: AsyncSession = Depends(get_db)):
    return await service.register(db, body)


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    return await service.login(db, body)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(body: RefreshRequest, db: AsyncSession = Depends(get_db)):
    return await service.refresh_session(db, body.refresh_token)


@router.post("/logout", response_model=MessageResponse)
async def logout(body: RefreshRequest, db: AsyncSession = Depends(get_db)):
    await service.logout(db, body.refresh_token)
    await db.commit()
    return MessageResponse(message="Вы вышли из аккаунта")


@router.get("/me", response_model=UserPublic)
async def me(user: UserPublic = Depends(get_current_user_public)):
    return user


@router.post("/password/change", response_model=MessageResponse)
async def change_password(
    body: ChangePasswordRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await service.change_password(db, user, body)
    await db.commit()
    return MessageResponse(message="Пароль изменён. Войдите снова.")


@router.patch("/me", response_model=UserPublic)
async def update_me(
    body: ProfileUpdateRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await service.update_profile(db, user, body)
    await db.commit()
    return result
