"""Waitlist signup endpoint."""

import json
import os
import urllib.request

from fastapi import APIRouter
from pydantic import BaseModel, EmailStr

router = APIRouter(prefix="/waitlist", tags=["waitlist"])


class WaitlistRequest(BaseModel):
    email: EmailStr
    name: str = ""


class WaitlistResponse(BaseModel):
    ok: bool
    message: str


@router.post("", response_model=WaitlistResponse)
async def waitlist_signup(req: WaitlistRequest) -> WaitlistResponse:
    email = req.email.strip().lower()
    name = req.name.strip() or None

    supabase_url = os.environ.get("SUPABASE_URL")
    supabase_key = os.environ.get("SUPABASE_SECRET_KEY")

    if supabase_url and supabase_key:
        try:
            http_req = urllib.request.Request(
                f"{supabase_url}/rest/v1/waitlist",
                data=json.dumps({"email": email, "name": name}).encode(),
                headers={
                    "Content-Type": "application/json",
                    "apikey": supabase_key,
                    "Authorization": f"Bearer {supabase_key}",
                    "Prefer": "return=minimal",
                },
                method="POST",
            )
            urllib.request.urlopen(http_req)
        except Exception as e:
            error_msg = str(e)
            if "409" not in error_msg and "23505" not in error_msg:
                raise

    return WaitlistResponse(ok=True, message="You're on the list!")
