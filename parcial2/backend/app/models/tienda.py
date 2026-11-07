from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from ..core.database import Base, TenantMixin


class CarritoCliente(Base, TenantMixin):
    __tablename__ = 'carritos_cliente'
    __table_args__ = (UniqueConstraint('tenant_id', 'cliente_id'),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    cliente_id: Mapped[int] = mapped_column(ForeignKey('clientes.id'), nullable=False)
    sucursal_id: Mapped[int] = mapped_column(ForeignKey('sucursales.id'), nullable=False)
    items: Mapped[list] = mapped_column(JSON, default=list, nullable=False)


class CitaReserva(Base, TenantMixin):
    __tablename__ = 'citas_reserva'
    __table_args__ = (UniqueConstraint('tenant_id', 'reserva_id'),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    reserva_id: Mapped[int] = mapped_column(ForeignKey('reservas.id'), nullable=False)
    fecha_hora_prueba: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    notas: Mapped[str | None] = mapped_column(String(500))
