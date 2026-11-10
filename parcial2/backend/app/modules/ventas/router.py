from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session
from ...core.database import TenantScope
from ...core.deps import get_db, require_permiso, require_auth
from . import schemas, service
from .comprobante_pdf import generar_pdf_comprobante
from ...models import Cliente

router = APIRouter(prefix="/ventas", tags=["CU-15/17 Ventas"])


@router.post("", response_model=schemas.VentaOut, status_code=201)
def registrar(body: schemas.VentaIn, scope: TenantScope = Depends(require_permiso("ventas:crear")), db: Session = Depends(get_db)):
    if "cliente" in scope.roles and "clientes:ver" not in scope.permisos:
        cliente = db.query(Cliente).filter_by(tenant_id=scope.tenant_id, user_id=scope.user_id).first()
        if not cliente or (body.cliente_id is not None and body.cliente_id != cliente.id):
            raise HTTPException(404, "Cliente no encontrado")
        body = body.model_copy(update={"cliente_id": cliente.id})
    return service.registrar_venta(db, scope.tenant_id, body, scope.user_id)


@router.post("/{id}/anular", response_model=schemas.VentaOut)
def anular(id: int, body: schemas.AnularIn, scope: TenantScope = Depends(require_permiso("ventas:anular")), db: Session = Depends(get_db)):
    return service.anular_venta(db, scope.tenant_id, id, body.motivo, scope.user_id)


@router.get("/{id}/comprobante")
def obtener_comprobante(id: int, scope: TenantScope = Depends(require_auth), db: Session = Depends(get_db)):
    return service.comprobante(db, scope.tenant_id, id, usuario_id=scope.user_id, roles=scope.roles)


@router.get("/{id}/comprobante.pdf")
def obtener_comprobante_pdf(id: int, descargar: bool = False, scope: TenantScope = Depends(require_auth), db: Session = Depends(get_db)):
    datos = service.comprobante(db, scope.tenant_id, id, usuario_id=scope.user_id, roles=scope.roles)
    pdf_bytes = generar_pdf_comprobante(datos)
    nro = datos.get("codigo", f"venta-{id}")
    disposition = f'{"attachment" if descargar else "inline"}; filename="comprobante-{nro}.pdf"'
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": disposition}
    )
