import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, Text, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class QueryLog(Base):
    """Tracks every user query for analytics and data improvement."""

    __tablename__ = "query_logs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    phone_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    raw_input: Mapped[str] = mapped_column(Text, nullable=False)
    parsed_drug: Mapped[str | None] = mapped_column(String(300), nullable=True)
    parsed_salt: Mapped[str | None] = mapped_column(String(500), nullable=True)
    match_found: Mapped[bool | None] = mapped_column(default=None)
    response_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    response_time_ms: Mapped[int | None] = mapped_column(nullable=True)
    language: Mapped[str | None] = mapped_column(String(10), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
