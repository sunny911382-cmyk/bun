"""
Auth router — thin wrapper around Supabase Auth.
All token validation is done by Supabase; we just proxy sign-up/sign-in
and expose a /me endpoint so the UI can confirm who is logged in.
"""
import os
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr

from db.client import get_db

router  = APIRouter(prefix="/auth", tags=["auth"])
bearer  = HTTPBearer(auto_error=False)


# ── Schemas ───────────────────────────────────────────────────────────────────

class AuthRequest(BaseModel):
    email: EmailStr
    password: str


# ── Dependency: resolve current user from Bearer token ────────────────────────

async def current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer),
) -> dict:
    if not creds:
        raise HTTPException(401, "Not authenticated")
    try:
        result = get_db().auth.get_user(creds.credentials)
        return result.user
    except Exception:
        raise HTTPException(401, "Invalid or expired token")


# ── Routes ────────────────────────────────────────────────────────────────────

@router.post("/signup")
def signup(body: AuthRequest):
    try:
        res = get_db().auth.sign_up({"email": body.email, "password": body.password})
        return {"message": "Check your email to confirm your account.", "user_id": res.user.id}
    except Exception as e:
        raise HTTPException(400, str(e))


@router.post("/login")
def login(body: AuthRequest):
    try:
        res = get_db().auth.sign_in_with_password({"email": body.email, "password": body.password})
        return {
            "access_token": res.session.access_token,
            "refresh_token": res.session.refresh_token,
            "user": {"id": res.user.id, "email": res.user.email},
        }
    except Exception as e:
        raise HTTPException(401, str(e))


@router.post("/logout")
def logout(creds: HTTPAuthorizationCredentials = Depends(bearer)):
    try:
        get_db().auth.sign_out(creds.credentials)
    except Exception:
        pass
    return {"message": "Logged out"}


@router.get("/me")
def me(user: dict = Depends(current_user)):
    return {"id": str(user.id), "email": user.email}
