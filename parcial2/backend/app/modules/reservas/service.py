from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy.orm import Session

from ...models import Cliente, Color, DetalleReserva, Inventario, Producto, Reserva, Sucursal, Talla, Variante
from . import schemas


def crear(db: Session, tenant_id: int, data: schemas.ReservaIn, *, antes_de_guardar=None):
    if data.uuid_operacion:
        previa = db.query(Reserva).filter_by(tenant_id=tenant_id, uuid_operacion=data.uuid_operacion).first()
        if previa:
            return previa
    for model, id_ in ((Cliente, data.cliente_id), (Sucursal, data.sucursal_id), (Variante, data.variante_id)):
        if not db.query(model).filter_by(id=id_, tenant_id=tenant_id).first():
            raise HTTPException(404, "Recurso no encontrado")
    inv = db.query(Inventario).filter_by(tenant_id=tenant_id, sucursal_id=data.sucursal_id,
                                         variante_id=data.variante_id).with_for_update().first()
    if not inv:
        raise HTTPException(409, "Stock insuficiente en la sucursal")
    reserva = Reserva(tenant_id=tenant_id, codigo=f"RES-{uuid4().hex[:10].upper()}",
                      sucursal_id=data.sucursal_id, cliente_id=data.cliente_id,
                      uuid_operacion=data.uuid_operacion, origen="EN_LINEA", estado="PENDIENTE")
    reserva.validarStockYApartar(db, inv, data.cantidad)
    db.add(DetalleReserva(tenant_id=tenant_id, reserva_id=reserva.id,
                          variante_id=data.variante_id, cantidad=data.cantidad))
    if antes_de_guardar is not None:
        antes_de_guardar(reserva)
    db.commit()
    db.refresh(reserva)
    return reserva


def anular_reserva(db: Session, tenant_id: int, id: int, motivo: str):
    reserva = db.query(Reserva).filter_by(id=id, tenant_id=tenant_id).first()
    if not reserva:
        raise HTTPException(404, "Reserva no encontrada")
    if reserva.estado not in {"PENDIENTE", "PREPARADA"}:
        raise HTTPException(409, "La reserva ya no está pendiente")
    for item in db.query(DetalleReserva).filter_by(reserva_id=id, tenant_id=tenant_id):
        inv = db.query(Inventario).filter_by(tenant_id=tenant_id, sucursal_id=reserva.sucursal_id,
                                             variante_id=item.variante_id).first()
        if inv:
            inv.reservado -= item.cantidad
    reserva.estado, reserva.motivo_anulacion = "ANULADA", motivo
    db.commit()
    return reserva


def salida_panel(db: Session, tenant_id: int, reserva: Reserva):
    cliente = db.query(Cliente).filter_by(tenant_id=tenant_id, id=reserva.cliente_id).first()
    sucursal = db.query(Sucursal).filter_by(tenant_id=tenant_id, id=reserva.sucursal_id).first()
    detalles = []
    for detalle in db.query(DetalleReserva).filter_by(tenant_id=tenant_id, reserva_id=reserva.id).all():
        variante = db.query(Variante).filter_by(tenant_id=tenant_id, id=detalle.variante_id).first()
        producto = db.query(Producto).filter_by(tenant_id=tenant_id, id=variante.producto_id).first() if variante else None
        talla = db.query(Talla).filter_by(tenant_id=tenant_id, id=variante.talla_id).first() if variante and variante.talla_id else None
        color = db.query(Color).filter_by(tenant_id=tenant_id, id=variante.color_id).first() if variante and variante.color_id else None
        detalles.append({"id": detalle.id, "variante_id": detalle.variante_id, "sku": variante.sku if variante else "",
                         "prenda": producto.nombre if producto else "", "talla": talla.nombre if talla else "—",
                         "color": color.nombre if color else "—", "cantidad": detalle.cantidad,
                         "estado": "reservado" if reserva.estado in {"PENDIENTE", "PREPARADA"} else "liberado"})
    estados = {"PENDIENTE": "pendiente", "PREPARADA": "preparada", "ATENDIDA": "atendida",
               "ANULADA": "cancelada", "EXPIRADA": "expirada"}
    from ...models.tienda import CitaReserva
    cita = db.query(CitaReserva).filter_by(tenant_id=tenant_id, reserva_id=reserva.id).first()
    return {"id": reserva.id, "codigo": reserva.codigo, "estado": estados.get(reserva.estado, reserva.estado.lower()),
            "fecha_creacion": None, "fecha_hora_prueba": cita.fecha_hora_prueba if cita else None, "fecha_limite": reserva.fecha_limite,
            "notas": cita.notas if cita else None, "sucursal_id": reserva.sucursal_id, "sucursal": sucursal.nombre if sucursal else None,
            "unidades": sum(d["cantidad"] for d in detalles), "detalle": detalles,
            "cliente": {"id": reserva.cliente_id, "nombre": cliente.nombre if cliente else None,
                        "email": cliente.correo if cliente else None, "telefono": cliente.telefono if cliente else None}}


def transicion_panel(db: Session, tenant_id: int, id: int, accion: str):
    reserva = db.query(Reserva).filter_by(tenant_id=tenant_id, id=id).with_for_update().first()
    if reserva is None: raise HTTPException(404, "Reserva no encontrada")
    if accion == "preparar":
        if reserva.estado != "PENDIENTE": raise HTTPException(409, "Solo se puede preparar una reserva pendiente")
        reserva.estado = "PREPARADA"
    elif accion in {"atender", "expirar"}:
        estados = {"PREPARADA"} if accion == "atender" else {"PENDIENTE", "PREPARADA"}
        if reserva.estado not in estados: raise HTTPException(409, "La reserva no admite esta operación")
        for item in db.query(DetalleReserva).filter_by(tenant_id=tenant_id, reserva_id=id).all():
            inv = db.query(Inventario).filter_by(tenant_id=tenant_id, sucursal_id=reserva.sucursal_id,
                                                  variante_id=item.variante_id).with_for_update().first()
            if not inv or inv.reservado < item.cantidad: raise HTTPException(409, "El inventario reservado no coincide")
            inv.reservado -= item.cantidad
        reserva.estado = "ATENDIDA" if accion == "atender" else "EXPIRADA"
    else:
        raise HTTPException(404, "Operación desconocida")
    db.commit()
    return salida_panel(db, tenant_id, reserva)
