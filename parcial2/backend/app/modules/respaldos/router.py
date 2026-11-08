import json
import re
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.orm import Session
from ...core.database import TenantScope
from ...core.deps import get_db, require_roles
from . import service

router = APIRouter(prefix='/respaldos', tags=['Respaldos por empresa'])


@router.get('/empresa')
def descargar(scope: TenantScope = Depends(require_roles('admin')), db: Session = Depends(get_db)):
    datos = service.crear_respaldo(db, scope.tenant_id)
    codigo = re.sub(r'[^a-zA-Z0-9_-]', '_', datos['empresa']['codigo'])
    nombre = f"respaldo-{codigo}-{datos['creado_en'][:10]}.json"
    contenido = json.dumps(datos, ensure_ascii=False, indent=2).encode('utf-8')
    return Response(contenido, media_type='application/json; charset=utf-8', headers={
        'Content-Disposition': f'attachment; filename="{nombre}"', 'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff'})


@router.post('/verificar')
def verificar(datos: dict, scope: TenantScope = Depends(require_roles('admin'))):
    try:
        resultado = service.verificar_respaldo(datos)
    except (ValueError, TypeError, KeyError) as exc:
        raise HTTPException(422, str(exc)) from exc
    if resultado['empresa']['id'] != scope.tenant_id: raise HTTPException(404, 'Respaldo de otra empresa')
    return resultado
