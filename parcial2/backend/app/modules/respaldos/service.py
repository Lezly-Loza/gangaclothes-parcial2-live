"""Respaldo portable de una empresa, sin incluir otras empresas ni secretos globales."""
from datetime import date, datetime, timezone
from decimal import Decimal
from hashlib import sha256
import json
from sqlalchemy import select
from sqlalchemy.orm import Session
from ...core.database import Base
from ...models import Plan, Tenant

FORMATO = 'gangaclothes-empresa-v1'


def _json(valor):
    if isinstance(valor, (datetime, date)): return valor.isoformat()
    if isinstance(valor, Decimal): return str(valor)
    raise TypeError(f'Tipo no soportado en respaldo: {type(valor).__name__}')


def _canonico(contenido):
    return json.dumps(contenido, ensure_ascii=False, sort_keys=True, separators=(',', ':'), default=_json).encode('utf-8')


def crear_respaldo(db: Session, tenant_id: int):
    # Una conexión independiente ofrece una única fotografía, incluso si la
    # sesión que autentica ya comenzó su propia transacción.
    motor = db.get_bind()
    with motor.connect() as conexion:
        if conexion.dialect.name == 'sqlite':
            conexion.exec_driver_sql('BEGIN')
        else:
            conexion = conexion.execution_options(isolation_level='REPEATABLE READ')
            conexion.begin()
        tenant = conexion.execute(select(Tenant.__table__).where(Tenant.id == tenant_id)).mappings().first()
        if tenant is None: raise ValueError('Empresa no encontrada')
        tablas = {'tenants': [dict(tenant)]}
        for tabla in Base.metadata.sorted_tables:
            if 'tenant_id' not in tabla.c: continue
            tablas[tabla.name] = [dict(row) for row in conexion.execute(select(tabla).where(tabla.c.tenant_id == tenant_id)).mappings()]
        planes = {fila['plan_id'] for fila in tablas.get('suscripciones', []) if fila.get('plan_id') is not None}
        tablas['planes'] = [dict(row) for row in conexion.execute(select(Plan.__table__).where(Plan.id.in_(planes))).mappings()] if planes else []
        contenido = {'formato': FORMATO, 'creado_en': datetime.now(timezone.utc).isoformat(),
                     'empresa': {'id': tenant_id, 'codigo': tenant['codigo'], 'razon_social': tenant['razon_social']},
                     'tablas': tablas}
        # Normalizar antes de firmar evita diferencias de fechas/decimales al leer JSON.
        normalizado = json.loads(_canonico(contenido))
        normalizado['sha256'] = sha256(_canonico(normalizado)).hexdigest()
        return normalizado


def verificar_respaldo(datos):
    if not isinstance(datos, dict) or datos.get('formato') != FORMATO:
        raise ValueError('Formato de respaldo no compatible')
    checksum = datos.get('sha256')
    cuerpo = {k: v for k, v in datos.items() if k != 'sha256'}
    if not isinstance(checksum, str) or sha256(_canonico(cuerpo)).hexdigest() != checksum:
        raise ValueError('El respaldo está incompleto o fue modificado')
    empresa = cuerpo.get('empresa') or {}; tablas = cuerpo.get('tablas')
    if not isinstance(tablas, dict) or not isinstance(empresa.get('id'), int): raise ValueError('Faltan datos de empresa')
    permitidas = {t.name for t in Base.metadata.sorted_tables if 'tenant_id' in t.c} | {'tenants', 'planes'}
    if set(tablas) != permitidas: raise ValueError('Las tablas del respaldo no coinciden con esta versión')
    tid = empresa['id']
    tenants = tablas['tenants']
    if not isinstance(tenants, list) or len(tenants) != 1 or not isinstance(tenants[0], dict) or tenants[0].get('id') != tid or tenants[0].get('codigo') != empresa.get('codigo'):
        raise ValueError('La empresa del respaldo no coincide')
    for nombre, filas in tablas.items():
        if not isinstance(filas, list): raise ValueError(f'Tabla inválida: {nombre}')
        tabla = Base.metadata.tables[nombre]
        columnas = {c.name for c in tabla.columns}
        for fila in filas:
            if not isinstance(fila, dict) or set(fila) != columnas: raise ValueError(f'Columnas inválidas en {nombre}')
            if 'tenant_id' in columnas and fila['tenant_id'] != tid: raise ValueError('El respaldo mezcla empresas')
    planes = {p['id'] for p in tablas['planes']}
    if any(s['plan_id'] not in planes for s in tablas.get('suscripciones', [])): raise ValueError('Falta el plan de una suscripción')
    return {'valido': True, 'empresa': empresa, 'creado_en': cuerpo['creado_en'],
            'registros': {nombre: len(filas) for nombre, filas in tablas.items()}}
