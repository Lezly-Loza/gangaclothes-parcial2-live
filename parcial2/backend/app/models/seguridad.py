from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, JSON, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from ..core.database import Base, TenantMixin


class Rol(Base, TenantMixin):
    """Rol propio de una empresa; sus permisos no se comparten con otros tenants."""
    __tablename__ = "roles_tenant"
    __table_args__ = (UniqueConstraint("tenant_id", "nombre", name="uq_rol_tenant_nombre"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nombre: Mapped[str] = mapped_column(String(50), nullable=False)
    descripcion: Mapped[str | None] = mapped_column(String(300))
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    permisos: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)


class UsuarioRol(Base, TenantMixin):
    __tablename__ = "usuario_roles_tenant"
    __table_args__ = (UniqueConstraint("tenant_id", "usuario_id", "rol_id", name="uq_usuario_rol_tenant"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    rol_id: Mapped[int] = mapped_column(ForeignKey("roles_tenant.id", ondelete="CASCADE"), nullable=False)


class PerfilUsuario(Base, TenantMixin):
    __tablename__ = "perfiles_usuario_tenant"
    __table_args__ = (UniqueConstraint("tenant_id", "usuario_id", name="uq_perfil_usuario_tenant"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    apellido: Mapped[str | None] = mapped_column(String(200))
    telefono: Mapped[str | None] = mapped_column(String(50))


class Bitacora(Base, TenantMixin):
    __tablename__ = "bitacora_tenant"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    fecha: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    usuario_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    actor: Mapped[str] = mapped_column(String(200), nullable=False)
    modulo: Mapped[str] = mapped_column(String(50), nullable=False)
    accion: Mapped[str] = mapped_column(String(30), nullable=False)
    nivel: Mapped[str] = mapped_column(String(20), default="INFO", nullable=False)
    entidad: Mapped[str | None] = mapped_column(String(80))
    entidad_id: Mapped[int | None] = mapped_column(Integer)
    detalle: Mapped[str | None] = mapped_column(String(500))
    ip: Mapped[str | None] = mapped_column(String(45))
