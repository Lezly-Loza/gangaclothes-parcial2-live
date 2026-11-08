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


class PrendaFavorita(Base, TenantMixin):
    __tablename__ = 'prendas_favoritas'
    __table_args__ = (UniqueConstraint('tenant_id', 'usuario_id', 'producto_id', name='uq_favorito_tenant_user_prod'),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    usuario_id: Mapped[int] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    producto_id: Mapped[int] = mapped_column(ForeignKey('productos.id', ondelete='CASCADE'), nullable=False)
    fecha: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class PrendaResena(Base, TenantMixin):
    __tablename__ = 'prendas_resenas'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    producto_id: Mapped[int] = mapped_column(ForeignKey('productos.id', ondelete='CASCADE'), nullable=False)
    usuario_id: Mapped[int] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    autor_nombre: Mapped[str] = mapped_column(String(120), nullable=False)
    calificacion: Mapped[int] = mapped_column(Integer, nullable=False)  # 1 a 5 estrellas
    comentario: Mapped[str] = mapped_column(String(1000), nullable=False)
    fecha: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

