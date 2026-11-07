from sqlalchemy import Boolean, Integer, JSON, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from ..core.database import Base, TenantMixin


class RegistroComplementario(Base, TenantMixin):
    """Colecciones y ciudades conservadas de la interfaz anterior."""
    __tablename__ = "catalogos_complementarios"
    __table_args__ = (UniqueConstraint("tenant_id", "tipo", "nombre"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tipo: Mapped[str] = mapped_column(String(40), nullable=False)
    nombre: Mapped[str] = mapped_column(String(200), nullable=False)
    activo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    datos: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)


class DatosComplementarios(Base, TenantMixin):
    """Campos de la interfaz anterior sin duplicar el registro principal."""
    __tablename__ = "datos_complementarios"
    __table_args__ = (UniqueConstraint("tenant_id", "tipo", "registro_id"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tipo: Mapped[str] = mapped_column(String(40), nullable=False)
    registro_id: Mapped[int] = mapped_column(Integer, nullable=False)
    datos: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
