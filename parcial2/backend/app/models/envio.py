from datetime import datetime, timezone
from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from ..core.database import Base, TenantMixin


class Envio(Base, TenantMixin):
    __tablename__ = "envios_tenant"
    __table_args__ = (UniqueConstraint("tenant_id", "venta_id"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    venta_id: Mapped[int] = mapped_column(ForeignKey("ventas.id"), nullable=False)
    direccion: Mapped[str] = mapped_column(String(300), nullable=False)
    latitud: Mapped[float] = mapped_column(Float, nullable=False)
    longitud: Mapped[float] = mapped_column(Float, nullable=False)
    referencia: Mapped[str | None] = mapped_column(String(300))
    telefono_contacto: Mapped[str | None] = mapped_column(String(50))
    estado: Mapped[str] = mapped_column(String(20), default="pendiente", nullable=False)
    repartidor: Mapped[str | None] = mapped_column(String(200))
    motivo_cancelacion: Mapped[str | None] = mapped_column(String(300))
    fecha_creacion: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    fecha_asignacion: Mapped[datetime | None] = mapped_column(DateTime)
    fecha_salida: Mapped[datetime | None] = mapped_column(DateTime)
    fecha_entrega: Mapped[datetime | None] = mapped_column(DateTime)
