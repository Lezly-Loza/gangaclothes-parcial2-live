"""CU-17: Anular reserva o venta.

Boundary (ICONIX): frontera HTTP para la operación de anulación.
Solo roles 'encargado' o 'administrador' pueden anular (ventas:crear).
"""
from fastapi import APIRouter, Depends, Request

from app.core.auditoria import registrar
from app.core.deps import get_db, require_permiso
from app.modules.anulaciones import service
from app.modules.anulaciones.schemas import AnulacionIn

router = APIRouter()
# En este proyecto los permisos de crear ventas incluyen la anulación (encargado y admin)
anular_perm = require_permiso("ventas:crear")


@router.post("", status_code=200, summary="CU-17: anular una reserva o venta")
def anular(
    datos: AnulacionIn,
    peticion: Request,
    db=Depends(get_db),
    usuario=Depends(anular_perm),
):
    """
    Boundary → Controller → Entity:
    - Boundary: recibe tipo_operacion, operacion_id y motivo.
    - Controller: service.anular() valida reglas y ejecuta la reversión.
    - Entity: Venta/Reserva e Inventario son modificadas atómicamente.
    """
    resultado = service.anular(db, datos, usuario)
    registrar(
        db, modulo="VENTAS", accion="EDITAR", usuario=usuario, peticion=peticion,
        entidad=datos.tipo_operacion.lower(), entidad_id=datos.operacion_id,
        nivel="ALERTA",
        detalle=f"Anulación de {datos.tipo_operacion} #{datos.operacion_id}: {datos.motivo}",
    )
    return resultado
