from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from ..core.database import Base, TenantMixin


class _Registro(Base, TenantMixin):
    __abstract__ = True
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nombre: Mapped[str] = mapped_column(String(200), nullable=False)
    activo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class Categoria(_Registro):
    __tablename__ = "categorias"
    __table_args__ = (UniqueConstraint("tenant_id", "nombre"),)


class Talla(_Registro):
    __tablename__ = "tallas"
    __table_args__ = (UniqueConstraint("tenant_id", "nombre"),)


class Color(_Registro):
    __tablename__ = "colores"
    __table_args__ = (UniqueConstraint("tenant_id", "nombre"),)
    codigo_hex: Mapped[str | None] = mapped_column(String(7))


class Temporada(_Registro):
    __tablename__ = "temporadas"
    __table_args__ = (UniqueConstraint("tenant_id", "nombre"),)
    fecha_inicio: Mapped[date | None] = mapped_column(Date)
    fecha_fin: Mapped[date | None] = mapped_column(Date)


class Producto(_Registro):
    __tablename__ = "productos"
    descripcion: Mapped[str | None] = mapped_column(Text)
    categoria_id: Mapped[int | None] = mapped_column(ForeignKey("categorias.id"))
    temporada_id: Mapped[int | None] = mapped_column(ForeignKey("temporadas.id"))
    precio_base: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    imagen_url: Mapped[str | None] = mapped_column(String(500))
    actualizado_en: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))


class Variante(Base, TenantMixin):
    __tablename__ = "variantes"
    __table_args__ = (UniqueConstraint("tenant_id", "sku"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    producto_id: Mapped[int] = mapped_column(ForeignKey("productos.id"), nullable=False)
    talla_id: Mapped[int | None] = mapped_column(ForeignKey("tallas.id"))
    color_id: Mapped[int | None] = mapped_column(ForeignKey("colores.id"))
    sku: Mapped[str] = mapped_column(String(100), nullable=False)
    precio: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    precio_actualizado_en: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    activo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class Proveedor(Base, TenantMixin):
    __tablename__ = "proveedores"
    __table_args__ = (UniqueConstraint("tenant_id", "nit"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    razon_social: Mapped[str] = mapped_column(String(200), nullable=False)
    nit: Mapped[str] = mapped_column(String(50), nullable=False)
    contacto: Mapped[str | None] = mapped_column(String(200))
    telefono: Mapped[str | None] = mapped_column(String(50))
    correo: Mapped[str | None] = mapped_column(String(200))
    activo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class Cliente(Base, TenantMixin):
    __tablename__ = "clientes"
    __table_args__ = (UniqueConstraint("tenant_id", "documento"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nombre: Mapped[str] = mapped_column(String(200), nullable=False)
    documento: Mapped[str] = mapped_column(String(60), nullable=False)
    telefono: Mapped[str | None] = mapped_column(String(50))
    correo: Mapped[str | None] = mapped_column(String(200))
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))


class Inventario(Base, TenantMixin):
    __tablename__ = "inventarios"
    __table_args__ = (UniqueConstraint("sucursal_id", "variante_id"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    sucursal_id: Mapped[int] = mapped_column(ForeignKey("sucursales.id"), nullable=False)
    variante_id: Mapped[int] = mapped_column(ForeignKey("variantes.id"), nullable=False)
    stock: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    reservado: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    stock_min: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    stock_max: Mapped[int] = mapped_column(Integer, default=100, nullable=False)

    def validarStockYGuardar(self, db, tipo: str, cantidad: int):
        if cantidad < 0 or (cantidad == 0 and tipo != "AJUSTE"):
            raise HTTPException(422, "La cantidad debe ser positiva")
        if tipo in {"SALIDA", "VENTA", "TRASPASO"}:
            if self.stock - self.reservado < cantidad:
                raise HTTPException(409, "Stock insuficiente")
            self.stock -= cantidad
        elif tipo in {"ENTRADA", "DEVOLUCION"}:
            self.stock += cantidad
        elif tipo == "AJUSTE":
            if cantidad < self.reservado:
                raise HTTPException(409, "El ajuste no puede ser menor al stock reservado")
            self.stock = cantidad
        else:
            raise HTTPException(422, "Tipo de movimiento inválido")
        db.add(self)
        db.flush()
        return self


class MovimientoInventario(Base, TenantMixin):
    __tablename__ = "movimientos_inventario"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    sucursal_id: Mapped[int] = mapped_column(ForeignKey("sucursales.id"), nullable=False)
    variante_id: Mapped[int] = mapped_column(ForeignKey("variantes.id"), nullable=False)
    tipo: Mapped[str] = mapped_column(String(30), nullable=False)
    cantidad: Mapped[int] = mapped_column(Integer, nullable=False)
    motivo: Mapped[str | None] = mapped_column(String(300))
    proveedor_id: Mapped[int | None] = mapped_column(ForeignKey("proveedores.id"))
    usuario_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    fecha: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))


class Reserva(Base, TenantMixin):
    __tablename__ = "reservas"
    __table_args__ = (UniqueConstraint("tenant_id", "uuid_operacion"), UniqueConstraint("tenant_id", "codigo"))
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    codigo: Mapped[str] = mapped_column(String(60), nullable=False)
    sucursal_id: Mapped[int] = mapped_column(ForeignKey("sucursales.id"), nullable=False)
    cliente_id: Mapped[int] = mapped_column(ForeignKey("clientes.id"), nullable=False)
    uuid_operacion: Mapped[str | None] = mapped_column(String(100))
    origen: Mapped[str] = mapped_column(String(20), default="EN_LINEA")
    fecha_limite: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc) + timedelta(hours=48))
    estado: Mapped[str] = mapped_column(String(20), default="PENDIENTE")
    motivo_anulacion: Mapped[str | None] = mapped_column(String(300))

    def validarStockYApartar(self, db, inventario: Inventario, cantidad: int):
        if cantidad <= 0 or inventario.stock - inventario.reservado < cantidad:
            raise HTTPException(409, "Stock insuficiente en la sucursal")
        inventario.reservado += cantidad
        db.add_all([self, inventario])
        db.flush()
        return self


class DetalleReserva(Base, TenantMixin):
    __tablename__ = "detalles_reserva"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    reserva_id: Mapped[int] = mapped_column(ForeignKey("reservas.id"), nullable=False)
    variante_id: Mapped[int] = mapped_column(ForeignKey("variantes.id"), nullable=False)
    cantidad: Mapped[int] = mapped_column(Integer, nullable=False)


class Venta(Base, TenantMixin):
    __tablename__ = "ventas"
    __table_args__ = (UniqueConstraint("tenant_id", "codigo"), UniqueConstraint("tenant_id", "uuid_operacion"))
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    codigo: Mapped[str] = mapped_column(String(60), nullable=False)
    sucursal_id: Mapped[int] = mapped_column(ForeignKey("sucursales.id"), nullable=False)
    usuario_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    cliente_id: Mapped[int | None] = mapped_column(ForeignKey("clientes.id"))
    uuid_operacion: Mapped[str | None] = mapped_column(String(100))
    origen: Mapped[str] = mapped_column(String(20), default="EN_LINEA")
    fecha: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    forma_pago: Mapped[str] = mapped_column(String(20), nullable=False)
    total: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    estado: Mapped[str] = mapped_column(String(20), default="CONFIRMADA")
    motivo_anulacion: Mapped[str | None] = mapped_column(String(300))
    anulado_por: Mapped[int | None] = mapped_column(ForeignKey("users.id"))

    def validarCobrarYGuardar(self, db, inventarios: list[tuple[Inventario, int]]):
        for inv, cantidad in inventarios:
            if cantidad <= 0 or inv.stock - inv.reservado < cantidad:
                raise HTTPException(409, "Stock insuficiente")
        db.add(self)
        db.flush()
        return self

    def validarYRevertirStock(self, db, inventarios: list[tuple[Inventario, int]], motivo: str, usuario_id: int | None):
        if self.estado == "ANULADA":
            raise HTTPException(409, "La venta ya está anulada")
        self.estado = "ANULADA"
        self.motivo_anulacion = motivo
        self.anulado_por = usuario_id
        for inv, cantidad in inventarios:
            inv.stock += cantidad
            db.add(inv)
        db.flush()


class DetalleVenta(Base, TenantMixin):
    __tablename__ = "detalles_venta"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    venta_id: Mapped[int] = mapped_column(ForeignKey("ventas.id"), nullable=False)
    variante_id: Mapped[int] = mapped_column(ForeignKey("variantes.id"), nullable=False)
    cantidad: Mapped[int] = mapped_column(Integer, nullable=False)
    precio_unitario: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    subtotal: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)


class Pago(Base, TenantMixin):
    __tablename__ = "pagos"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    venta_id: Mapped[int] = mapped_column(ForeignKey("ventas.id"), nullable=False)
    metodo: Mapped[str] = mapped_column(String(20), nullable=False)
    monto: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    referencia_pasarela: Mapped[str | None] = mapped_column(String(100))
    estado: Mapped[str] = mapped_column(String(20), default="APROBADO")


class CambioPrenda(Base, TenantMixin):
    __tablename__ = "cambios_prenda"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    venta_id: Mapped[int] = mapped_column(ForeignKey("ventas.id"), nullable=False)
    variante_devuelta_id: Mapped[int] = mapped_column(ForeignKey("variantes.id"), nullable=False)
    variante_nueva_id: Mapped[int] = mapped_column(ForeignKey("variantes.id"), nullable=False)
    diferencia: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    motivo: Mapped[str] = mapped_column(String(300), nullable=False)
    fecha: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    def verificarPlazoYGuardar(self, db, venta: Venta, plazo_dias: int):
        fecha = venta.fecha.replace(tzinfo=timezone.utc) if venta.fecha.tzinfo is None else venta.fecha
        if datetime.now(timezone.utc) - fecha > timedelta(days=plazo_dias):
            raise HTTPException(409, "Fuera de plazo")
        db.add(self)
        db.flush()
        return self
