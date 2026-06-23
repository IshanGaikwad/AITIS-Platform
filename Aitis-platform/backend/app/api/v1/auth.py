import secrets
from typing import Dict, Any

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import RedirectResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.core.oauth2 import oauth2_provider
from app.core.security import verify_token
from app.db.database import get_db
from app.schemas.user import Token, User
from app.services.auth_service import get_or_create_user_from_oauth, create_access_token_for_user

router = APIRouter()
security = HTTPBearer()


async def get_current_user_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict[str, Any]:
    """Extract and verify JWT token"""
    try:
        payload = verify_token(credentials.credentials)
        return payload
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


@router.get("/login")
async def login():
    """Initiate OAuth2 login flow"""
    state = secrets.token_urlsafe(32)
    auth_url = oauth2_provider.get_authorization_url(state)
    return {"authorization_url": auth_url, "state": state}


@router.get("/callback")
async def oauth2_callback(
    code: str,
    state: str,
    db: Session = Depends(get_db)
):
    """Handle OAuth2 callback"""
    try:
        # Exchange code for token
        token_data = await oauth2_provider.exchange_code_for_token(code)

        # Get user info
        access_token = token_data.get("access_token")
        if not access_token:
            raise HTTPException(status_code=400, detail="No access token received")

        user_info = await oauth2_provider.get_user_info(access_token)

        # Create or get user
        user = get_or_create_user_from_oauth(
            db=db,
            provider=oauth2_provider.provider,
            provider_id=user_info.get("sub") or user_info.get("id"),
            email=user_info.get("email"),
            name=user_info.get("name"),
            picture=user_info.get("picture"),
        )

        # Create access token
        jwt_token = create_access_token_for_user(user)

        response_payload = {
            "access_token": jwt_token,
            "token_type": "bearer",
            "user": User.from_orm(user),
        }

        if oauth2_provider.provider == "atlassian":
            response_payload["atlassian_access_token"] = access_token

        return response_payload

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"OAuth2 authentication failed: {str(e)}"
        )


@router.get("/me", response_model=User)
async def get_current_user(
    token: str = Depends(get_current_user_token),
    db: Session = Depends(get_db)
):
    """Get current authenticated user"""
    from app.services.auth_service import get_user_by_email
    user = get_user_by_email(db, token["sub"])
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return User.from_orm(user)


def get_token_from_header(authorization: str = "") -> str:
    """Extract token from Authorization header"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header missing or invalid",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return authorization.split(" ")[1]