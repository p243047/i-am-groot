"""
Users API endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.security import get_password_hash
from app.models.schemas import User
from app.models.schemas_api import UserResponse, UserUpdate
from app.api.auth import get_current_user as auth_get_current_user

router = APIRouter()


@router.get("/", response_model=list[UserResponse])
async def list_users(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(auth_get_current_user),
):
    """List all users (admin only)."""
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions",
        )
    
    result = await db.execute(select(User))
    users = list(result.scalars().all())
    return users


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(auth_get_current_user),
):
    """Get a specific user by ID."""
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    
    # Users can only view their own profile unless admin
    if not current_user.is_superuser and user.id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions",
        )
    
    return user


@router.put("/me", response_model=UserResponse)
async def update_profile(
    user_data: UserUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(auth_get_current_user),
):
    """Update current user profile."""
    # Update fields
    if user_data.email is not None:
        # Check if email is taken by another user
        result = await db.execute(select(User).where(User.email == user_data.email))
        existing = result.scalar_one_or_none()
        if existing and existing.id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered",
            )
        current_user.email = user_data.email
    
    if user_data.username is not None:
        result = await db.execute(select(User).where(User.username == user_data.username))
        existing = result.scalar_one_or_none()
        if existing and existing.id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already taken",
            )
        current_user.username = user_data.username
    
    if user_data.full_name is not None:
        current_user.full_name = user_data.full_name
    
    if user_data.password is not None:
        current_user.hashed_password = get_password_hash(user_data.password)
    
    await db.commit()
    await db.refresh(current_user)
    
    return current_user
