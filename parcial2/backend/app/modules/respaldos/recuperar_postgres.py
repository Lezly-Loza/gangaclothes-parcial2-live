"""Recupera una copia PostgreSQL en un SQLite nuevo sin alterar el origen.

Solicita la URL PostgreSQL sin mostrarla. No sobrescribe archivos existentes.
"""
import argparse
import getpass
import os
from pathlib import Path

from sqlalchemy import create_engine, event, func, inspect, select
from sqlalchemy.engine import make_url

from ... import models  # noqa: F401
from ...core.database import Base
from . import programacion  # noqa: F401, registra la tabla local nueva


def copiar_postgres_a_sqlite(url, destino):
    url = make_url(url)
    if url.get_backend_name() != 'postgresql':
        raise ValueError('Se requiere una conexión PostgreSQL')
    destino = Path(destino).resolve()
    fd = os.open(destino, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    os.close(fd)
    origen = create_engine(url, pool_pre_ping=True)
    local = create_engine('sqlite:///' + destino.as_posix())

    @event.listens_for(local, 'connect')
    def activar_fk(conexion, _):
        conexion.execute('PRAGMA foreign_keys=ON')

    try:
        with origen.connect().execution_options(isolation_level='REPEATABLE READ') as lectura:
            lectura.exec_driver_sql('SET TRANSACTION READ ONLY')
            inspector = inspect(lectura)
            tablas_origen = set(inspector.get_table_names(schema='public'))
            esperadas = set(Base.metadata.tables)
            faltantes = esperadas - tablas_origen
            # Esta tabla se añadió después de copiar la base publicada.
            if faltantes - {'programas_respaldo'} or tablas_origen - esperadas:
                raise ValueError('Las tablas de origen no coinciden con esta versión')
            for nombre in tablas_origen:
                tabla = Base.metadata.tables[nombre]
                if {c['name'] for c in inspector.get_columns(nombre, schema='public')} != {c.name for c in tabla.columns}:
                    raise ValueError('Las columnas no coinciden: ' + nombre)
            Base.metadata.create_all(local)
            totales = {}
            with local.begin() as escritura:
                for tabla in Base.metadata.sorted_tables:
                    if tabla.name not in tablas_origen:
                        continue
                    resultado = lectura.execute(select(tabla)).mappings()
                    cantidad = 0
                    while lote := resultado.fetchmany(500):
                        escritura.execute(tabla.insert(), [dict(fila) for fila in lote])
                        cantidad += len(lote)
                    if escritura.execute(select(func.count()).select_from(tabla)).scalar_one() != cantidad:
                        raise ValueError('No coincide el número de filas en ' + tabla.name)
                    totales[tabla.name] = cantidad
                if escritura.exec_driver_sql('PRAGMA foreign_key_check').fetchall():
                    raise ValueError('Hay referencias inválidas')
            return totales
    finally:
        origen.dispose()
        local.dispose()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--destino', required=True, help='Archivo SQLite nuevo que todavía no exista')
    args = parser.parse_args()
    url = getpass.getpass('Cadena PostgreSQL de Neon (no se mostrará): ')
    try:
        totales = copiar_postgres_a_sqlite(url, args.destino)
    except Exception as exc:
        print(f'No se completó la copia ({type(exc).__name__}). El origen no fue modificado. No se sobrescribió ningún archivo existente.')
        raise SystemExit(1) from None
    print(f'Copia completa: {len(totales)} tablas y {sum(totales.values())} registros, incluido el superadministrador.')


if __name__ == '__main__':
    main()
