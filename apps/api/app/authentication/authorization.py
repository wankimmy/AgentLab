from typing import Annotated

from fastapi import Depends, HTTPException, status

from app.authentication.router import CurrentUser, get_current_user
from app.models.entities import User, UserRole


def require_write_user(user: User = Depends(get_current_user)) -> User:
    if user.role == UserRole.demo:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Demo account is read-only",
        )
    return user


WriteUser = Annotated[User, Depends(require_write_user)]
