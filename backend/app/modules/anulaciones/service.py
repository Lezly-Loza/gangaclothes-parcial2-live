"""CU-17: Anular reserva o venta.

Reglas de negocio:
  VENTA:
    - Solo anular ventas en estado 'pagada' o 'pendiente'.
    - Si está 'pagada': verificar que no tenga un cambio previo.
    - Revertir stock: por cada línea, sumar cantidad al inventario.
    - Pasar estado a 'anulada' y registrar en bitácora.
  RESERVA:
    - Solo anular reservas en estado 'pendiente' o 'preparada'.
    - Liberar cantidad_reservada en el inventario.
    - Pasar estado a 'cancelada'.

Controller (ICONIX): este módulo orquesta la lógica de anulación.
Entity (ICONIX): Venta / Reserva e Inventario son las entidades afectadas.
"""
from fastapi import HTTPException
from sqlalchemy import update
from sqlalchemy.orm import Session

from app.core.fechas import utc_iso
from app.models.catalogo import Color, Prenda, Talla, Variante
from app.models.inventario import Inventario, MovimientoInventario
from app.models.sucursales import Sucursal
from app.models.usuarios import Cliente, Usuario
from app.models.ventas import CambioPrenda, DetalleReserva, DetalleVenta, Reserva, Venta


# ---------------------------------------------------------------- VENTA

def _anular_venta(db: Session, venta_id: int, motivo: str, usuario: Usuario) -> dict:
    venta = db.get(Venta, venta_id)
    if venta is None:
        raise HTTPException(404, f"La venta #{venta_id} no existe")

    if venta.estado == "anulada":
        raise HTTPException(400, "Esta venta ya fue anulada anteriormente")
    if venta.estado not in ("pagada", "pendiente"):
        raise HTTPException(
            400,
            f"No se puede anular una venta en estado '{venta.estado}'. "
            "Solo se anulan ventas pagadas o pendientes."
        )

    # Verificar que no haya un cambio previo (solo para ventas pagadas)
    if venta.estado == "pagada":
        cambio = db.query(CambioPrenda).filter(CambioPrenda.venta_id == venta_id).first()
        if cambio:
            raise HTTPException(
                400,
                f"Esta venta tiene un cambio registrado (#{cambio.id}). "
                "No se puede anular una venta que ya fue cambiada."
            )

    # Revertir stock: reingresa cada prenda al inventario
    lineas = (
        db.query(DetalleVenta, Variante, Prenda)
        .join(Variante, Variante.id == DetalleVenta.variante_id)
        .join(Prenda, Prenda.id == Variante.prenda_id)
        .filter(DetalleVenta.venta_id == venta_id)
        .all()
    )

    unidades_revertidas = 0
    for d, v, p in lineas:
        inv = (
            db.query(Inventario)
            .filter(Inventario.variante_id == d.variante_id, Inventario.sucursal_id == venta.sucursal_id)
            .first()
        )
        if inv:
            inv.cantidad += d.cantidad
            db.add(MovimientoInventario(
                variante_id=d.variante_id,
                sucursal_id=venta.sucursal_id,
                usuario_id=usuario.id,
                tipo="devolucion",
                cantidad=d.cantidad,
                motivo=f"Anulación de venta #{venta_id}: {motivo}",
            ))
            unidades_revertidas += d.cantidad

    venta.estado = "anulada"
    db.commit()

    sucursal = db.get(Sucursal, venta.sucursal_id)
    return {
        "operacion": "VENTA",
        "id": venta_id,
        "nuevo_estado": "anulada",
        "unidades_revertidas": unidades_revertidas,
        "sucursal": sucursal.nombre if sucursal else None,
        "motivo": motivo,
        "usuario_id": usuario.id,
        "mensaje": f"✓ Venta #{venta_id} anulada. {unidades_revertidas} unidad(es) reingresadas al inventario.",
    }


# ---------------------------------------------------------------- RESERVA

def _anular_reserva(db: Session, reserva_id: int, motivo: str, usuario: Usuario) -> dict:
    reserva = db.get(Reserva, reserva_id)
    if reserva is None:
        raise HTTPException(404, f"La reserva #{reserva_id} no existe")

    if reserva.estado in ("cancelada", "expirada", "atendida"):
        raise HTTPException(
            400,
            f"La reserva está '{reserva.estado}': solo se anulan reservas pendientes o preparadas."
        )

    detalles = (
        db.query(DetalleReserva)
        .filter(DetalleReserva.reserva_id == reserva_id, DetalleReserva.estado == "reservado")
        .all()
    )

    unidades_liberadas = 0
    for d in detalles:
        db.execute(
            update(Inventario)
            .where(Inventario.variante_id == d.variante_id, Inventario.sucursal_id == reserva.sucursal_id)
            .values(cantidad_reservada=Inventario.cantidad_reservada - d.cantidad)
            .execution_options(synchronize_session=False)
        )
        d.estado = "liberado"
        unidades_liberadas += d.cantidad

    reserva.estado = "cancelada"
    reserva.notas = (reserva.notas or "") + f" | Anulada por {usuario.email}: {motivo}"
    db.commit()

    sucursal = db.get(Sucursal, reserva.sucursal_id)
    cliente = db.get(Cliente, reserva.cliente_id)
    cliente_usuario = db.get(Usuario, cliente.usuario_id) if cliente else None
    return {
        "operacion": "RESERVA",
        "id": reserva_id,
        "nuevo_estado": "cancelada",
        "unidades_liberadas": unidades_liberadas,
        "sucursal": sucursal.nombre if sucursal else None,
        "cliente": " ".join(filter(None, [cliente_usuario.nombre, cliente_usuario.apellido])) if cliente_usuario else None,
        "motivo": motivo,
        "usuario_id": usuario.id,
        "mensaje": f"✓ Reserva #{reserva_id} anulada. {unidades_liberadas} unidad(es) liberadas del inventario.",
    }


# ---------------------------------------------------------------- ENDPOINT PRINCIPAL

def anular(db: Session, datos, usuario: Usuario) -> dict:
    """
    Controller (ICONIX): despacha al handler correcto según tipo_operacion.
    """
    if datos.tipo_operacion == "VENTA":
        return _anular_venta(db, datos.operacion_id, datos.motivo, usuario)
    elif datos.tipo_operacion == "RESERVA":
        return _anular_reserva(db, datos.operacion_id, datos.motivo, usuario)
    else:
        raise HTTPException(400, f"Tipo de operación inválido: {datos.tipo_operacion}")
