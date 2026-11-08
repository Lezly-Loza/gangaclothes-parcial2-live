"""Programación local de respaldos. Requiere proceso y almacenamiento persistentes."""
from datetime import datetime, timedelta, timezone
from pathlib import Path
from threading import Event, Lock, Thread
import json
import logging
import os
import re

from sqlalchemy import Boolean, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column
from ...core.database import Base, SessionLocal
from ...models import Tenant
from .service import crear_respaldo

log = logging.getLogger(__name__)
LA_PAZ = timezone(timedelta(hours=-4))
_lock = Lock()


class ProgramaRespaldo(Base):
    __tablename__ = 'programas_respaldo'
    empresa_id: Mapped[int] = mapped_column(ForeignKey('tenants.id', ondelete='CASCADE'), primary_key=True)
    diario: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    hora: Mapped[str] = mapped_column(String(5), default='02:00', nullable=False)
    siguiente_diario: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    fecha_unica: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    ultimo: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    error: Mapped[str | None] = mapped_column(String(500), nullable=True)


def ahora_utc():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def siguiente(hora, ahora):
    local = ahora.replace(tzinfo=timezone.utc).astimezone(LA_PAZ)
    h, m = map(int, hora.split(':'))
    cita = local.replace(hour=h, minute=m, second=0, microsecond=0)
    if cita <= local:
        cita += timedelta(days=1)
    return cita.astimezone(timezone.utc).replace(tzinfo=None)


def obtener(db, tid):
    p = db.get(ProgramaRespaldo, tid)
    if p is None:
        p = ProgramaRespaldo(empresa_id=tid, diario=True, hora='02:00', siguiente_diario=siguiente('02:00', ahora_utc()))
        db.add(p)
        db.commit()
        db.refresh(p)
    return p


def carpeta(tid):
    base = Path(os.environ.get('RESPALDOS_DIRECTORIO', str(Path(__file__).resolve().parents[3] / '.respaldos')))
    return base / str(tid)


def listar(tid):
    directorio = carpeta(tid)
    if not directorio.exists():
        return []
    return [{'nombre': f.name, 'bytes': f.stat().st_size} for f in sorted(directorio.glob('respaldo-*.json'), reverse=True) if f.is_file()][:30]


def ruta_segura(tid, nombre):
    if not re.fullmatch(r'respaldo-(?:diario|unico)-[0-9]{8}T[0-9]{6}\.json', nombre):
        return None
    ruta = carpeta(tid) / nombre
    return ruta if ruta.is_file() else None


def ejecutar_pendientes(ahora=None):
    if not _lock.acquire(blocking=False):
        return
    try:
        ahora = ahora or ahora_utc()
        with SessionLocal() as db:
            for tenant in db.query(Tenant).filter_by(activo=True).all():
                p = obtener(db, tenant.id)
                tareas = []
                if p.diario and p.siguiente_diario <= ahora:
                    tareas.append(('diario', p.siguiente_diario))
                if p.fecha_unica and p.fecha_unica <= ahora:
                    tareas.append(('unico', p.fecha_unica))
                for tipo, fecha in tareas:
                    try:
                        datos = crear_respaldo(db, tenant.id)
                        directorio = carpeta(tenant.id)
                        directorio.mkdir(parents=True, exist_ok=True)
                        nombre = f"respaldo-{tipo}-{fecha:%Y%m%dT%H%M%S}.json"
                        destino = directorio / nombre
                        temporal = destino.with_suffix('.tmp')
                        with temporal.open('w', encoding='utf-8') as archivo:
                            json.dump(datos, archivo, ensure_ascii=False, indent=2)
                        os.replace(temporal, destino)
                        p.ultimo = ahora
                        p.error = None
                        if tipo == 'diario':
                            p.siguiente_diario = siguiente(p.hora, ahora)
                        else:
                            p.fecha_unica = None
                        db.commit()
                    except Exception:
                        db.rollback()
                        log.exception('Error al respaldar empresa %s', tenant.id)
                        p = db.get(ProgramaRespaldo, tenant.id)
                        p.error = 'No se pudo crear la copia. Se volverá a intentar.'
                        db.commit()
    finally:
        _lock.release()


def iniciar():
    detener = Event()
    def ciclo():
        while not detener.is_set():
            try:
                ejecutar_pendientes()
            except Exception:
                log.exception('Error en el programador de respaldos')
            detener.wait(30)
    hilo = Thread(target=ciclo, name='respaldos', daemon=True)
    hilo.start()
    return detener, hilo
