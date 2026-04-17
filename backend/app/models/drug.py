import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Numeric, String, Text, Boolean, func
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class SaltComposition(Base):
    __tablename__ = "salt_compositions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(500), nullable=False, unique=True, index=True)
    synonyms: Mapped[list[str] | None] = mapped_column(ARRAY(String), nullable=True)
    therapeutic_class: Mapped[str | None] = mapped_column(String(200), nullable=True)
    is_narrow_therapeutic_index: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    drugs: Mapped[list["Drug"]] = relationship(back_populates="salt")
    generics: Mapped[list["GenericDrug"]] = relationship(back_populates="salt")


class Drug(Base):
    """Branded drug entry."""

    __tablename__ = "drugs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    brand_name: Mapped[str] = mapped_column(String(300), nullable=False, index=True)
    manufacturer: Mapped[str] = mapped_column(String(300), nullable=False)
    salt_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("salt_compositions.id"), nullable=False)
    strength: Mapped[str] = mapped_column(String(100), nullable=False)
    dosage_form: Mapped[str] = mapped_column(String(100), nullable=False)
    pack_size: Mapped[str | None] = mapped_column(String(50), nullable=True)
    mrp: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    price_per_unit: Mapped[float | None] = mapped_column(Numeric(10, 4), nullable=True)
    source: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    salt: Mapped["SaltComposition"] = relationship(back_populates="drugs")


class GenericDrug(Base):
    """Generic equivalent entries — including Jan Aushadhi products."""

    __tablename__ = "generic_drugs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(300), nullable=False)
    manufacturer: Mapped[str] = mapped_column(String(300), nullable=False)
    salt_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("salt_compositions.id"), nullable=False)
    strength: Mapped[str] = mapped_column(String(100), nullable=False)
    dosage_form: Mapped[str] = mapped_column(String(100), nullable=False)
    pack_size: Mapped[str | None] = mapped_column(String(50), nullable=True)
    mrp: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    price_per_unit: Mapped[float | None] = mapped_column(Numeric(10, 4), nullable=True)
    is_jan_aushadhi: Mapped[bool] = mapped_column(Boolean, default=False)
    source: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    salt: Mapped["SaltComposition"] = relationship(back_populates="generics")
