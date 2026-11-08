import json
import re
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, field_validator
from sqlalchemy.orm import Session
from ...core.database import TenantScope
from ...core.deps import get_db, require_roles
from . import service
from . import programacion as prog

router = APIRouter(prefix='/respaldos', tags=['Respaldos por empresa'])


class Configuracion(BaseModel):
    diario: bool
    hora: str
    fecha_unica: datetime | None = None

    @field_validator('hora')
    @classmethod
    def hora_valida(cls, valor):
        if not re.fullmatch(r'(?:[01]\d|2[0-3]):[0-5]\d', valor):
            raise ValueError('Usa una hora válida HH:MM')
        return valor


def _configuracion(p):
    def local(fecha):
        return fecha.replace(tzinfo=timezone.utc).astimezone(prog.LA_PAZ).isoformat() if fecha else None
    return {'diario': p.diario, 'hora': p.hora, 'siguiente_diario': local(p.siguiente_diario) if p.diario else None,
            'fecha_unica': local(p.fecha_unica), 'ultimo': local(p.ultimo), 'error': p.error,
            'zona': 'America/La_Paz', 'almacenamiento': 'Archivos del servidor; requiere disco persistente.'}


@router.get('/programacion')
def consultar_programacion(scope: TenantScope = Depends(require_roles('admin')), db: Session = Depends(get_db)):
    p = prog.obtener(db, scope.tenant_id)
    return {**_configuracion(p), 'copias': prog.listar(scope.tenant_id)}


@router.put('/programacion')
def configurar(body: Configuracion, scope: TenantScope = Depends(require_roles('admin')), db: Session = Depends(get_db)):
    fecha = body.fecha_unica
    if fecha:
        if fecha.tzinfo is None:
            fecha = fecha.replace(tzinfo=prog.LA_PAZ)
        fecha = fecha.astimezone(timezone.utc).replace(tzinfo=None)
        if fecha <= prog.ahora_utc():
            raise HTTPException(422, 'La fecha programada debe estar en el futuro')
    p = prog.obtener(db, scope.tenant_id)
    p.diario, p.hora, p.fecha_unica = body.diario, body.hora, fecha
    p.siguiente_diario = prog.siguiente(body.hora, prog.ahora_utc())
    p.error = None
    db.commit()
    return _configuracion(p)


@router.get('/programados/{nombre}')
def descargar_programado(nombre: str, scope: TenantScope = Depends(require_roles('admin'))):
    ruta = prog.ruta_segura(scope.tenant_id, nombre)
    if ruta is None:
        raise HTTPException(404, 'Copia no encontrada')
    from fastapi.responses import FileResponse
    return FileResponse(ruta, filename=nombre, media_type='application/json', headers={'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff'})


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
