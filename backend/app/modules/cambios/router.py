"""CU-16: Cambio de prendas.

Boundary (ICONIX): los endpoints son la frontera entre el cliente HTTP y la lógica.
Solo el personal con permiso 'ventas:crear' puede registrar cambios.
"""
from fastapi import APIRouter, Depends, Request

from app.core.auditoria import registrar
from app.core.deps import get_db, require_permiso
from app.modules.cambios import service
from app.modules.cambios.schemas import CambioIn

router = APIRouter()
crear = require_permiso("ventas:crear")
ver = require_permiso("ventas:ver")


@router.get("/venta/{venta_id}", summary="CU-16: buscar venta para iniciar cambio")
def buscar_venta(venta_id: int, db=Depends(get_db), _=Depends(ver)):
    return service.buscar_venta(db, venta_id)


@router.post("", status_code=201, summary="CU-16: registrar cambio de prenda")
def registrar_cambio(
    datos: CambioIn,
    peticion: Request,
    db=Depends(get_db),
    usuario=Depends(crear),
):
    """
    Boundary → Controller → Entity:
    - Boundary: este endpoint recibe los datos del formulario de cambio.
    - Controller: service.registrar_cambio() valida reglas y ejecuta la transacción.
    - Entity: Venta, Inventario, CambioPrenda son modificadas.
    """
    resultado = service.registrar_cambio(db, datos, usuario)
    registrar(
        db, modulo="VENTAS", accion="CREAR", usuario=usuario, peticion=peticion,
        entidad="cambio_prenda", entidad_id=resultado["cambio_id"],
        detalle=(
            f"Cambio en venta #{datos.venta_id}: "
            f"{resultado['devuelta']['sku']} → {resultado['nueva']['sku']}, "
            f"saldo Bs {resultado['saldo']:.2f}"
        ),
    )
    return resultado
