from datetime import date
from decimal import Decimal
from sqlalchemy import Boolean, Date, ForeignKey, Integer, JSON, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from ..core.database import Base, TenantMixin


class Promocion(Base, TenantMixin):
    __tablename__ = 'promociones_tenant'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nombre: Mapped[str] = mapped_column(String(200), nullable=False)
    descripcion: Mapped[str | None] = mapped_column(String(500))
    tipo_descuento: Mapped[str] = mapped_column(String(20), nullable=False)
    valor: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    fecha_inicio: Mapped[date] = mapped_column(Date, nullable=False)
    fecha_fin: Mapped[date] = mapped_column(Date, nullable=False)
    activo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    prenda_ids: Mapped[list[int]] = mapped_column(JSON, default=list, nullable=False)


class DescuentoVenta(Base, TenantMixin):
    __tablename__ = 'descuentos_venta_tenant'
    __table_args__ = (UniqueConstraint('tenant_id', 'detalle_venta_id'),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    detalle_venta_id: Mapped[int] = mapped_column(ForeignKey('detalles_venta.id'), nullable=False)
    promocion_id: Mapped[int] = mapped_column(ForeignKey('promociones_tenant.id'), nullable=False)
    promocion_nombre: Mapped[str] = mapped_column(String(200), nullable=False)
    precio_lista: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    descuento: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
