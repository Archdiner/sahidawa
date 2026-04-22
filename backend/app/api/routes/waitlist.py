"""Waitlist signup endpoint."""

import json
import os
import re
import urllib.request

from fastapi import APIRouter
from pydantic import BaseModel, field_validator

router = APIRouter(prefix="/waitlist", tags=["waitlist"])

_EMAIL_RE = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")


class WaitlistRequest(BaseModel):
    email: str
    name: str = ""

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        v = v.strip().lower()
        if not _EMAIL_RE.match(v):
            raise ValueError("Invalid email address")
        return v


class WaitlistResponse(BaseModel):
    ok: bool
    message: str


@router.post("", response_model=WaitlistResponse)
async def waitlist_signup(req: WaitlistRequest) -> WaitlistResponse:
    email = req.email
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
