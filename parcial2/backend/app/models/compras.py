from datetime import datetime, timezone
from decimal import Decimal
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, JSON, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column
from ..core.database import Base, TenantMixin


class ProductoProveedor(Base, TenantMixin):
    __tablename__ = "productos_proveedor_tenant"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    proveedor_id: Mapped[int] = mapped_column(ForeignKey("proveedores.id"), nullable=False)
    nombre: Mapped[str] = mapped_column(String(200), nullable=False)
    descripcion: Mapped[str | None] = mapped_column(String(500))
    categoria_id: Mapped[int | None] = mapped_column(ForeignKey("categorias.id"))
    prenda_id: Mapped[int | None] = mapped_column(ForeignKey("productos.id"))
    precio_referencial: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    cantidad_minima: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    disponible: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    temporada_ids: Mapped[list[int]] = mapped_column(JSON, default=list, nullable=False)
    fecha_actualizacion: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))


class Compra(Base, TenantMixin):
    __tablename__ = "compras_tenant"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    proveedor_id: Mapped[int] = mapped_column(ForeignKey("proveedores.id"), nullable=False)
    sucursal_id: Mapped[int] = mapped_column(ForeignKey("sucursales.id"), nullable=False)
    fecha: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    estado: Mapped[str] = mapped_column(String(20), default="pendiente", nullable=False)
    total: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)


class DetalleCompra(Base, TenantMixin):
    __tablename__ = "detalles_compra_tenant"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    compra_id: Mapped[int] = mapped_column(ForeignKey("compras_tenant.id"), nullable=False)
    variante_id: Mapped[int] = mapped_column(ForeignKey("variantes.id"), nullable=False)
    producto_proveedor_id: Mapped[int | None] = mapped_column(ForeignKey("productos_proveedor_tenant.id"))
    cantidad: Mapped[int] = mapped_column(Integer, nullable=False)
    precio_unitario: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
