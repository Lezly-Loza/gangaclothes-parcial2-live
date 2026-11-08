"""Copiar una fotografía SQLite a una base PostgreSQL nueva y vacía.

La URL de destino se solicita sin eco, o puede indicarse mediante la variable
GANGA_DESTINO_POSTGRES. No se imprime ni se guarda en el repositorio.
"""
import argparse
import getpass
import os
from pathlib import Path
import sqlite3

from sqlalchemy import Integer, create_engine, func, inspect, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.pool import NullPool

from ... import models  # noqa: F401: registra los modelos
from ...core.database import Base


def copiar_sqlite_a_postgres(origen, url_destino):
    origen = Path(origen).resolve(strict=True)
    if not origen.is_file():
        raise ValueError('La base de origen no es un archivo')
    destino_url = make_url(url_destino)
    if destino_url.get_backend_name() != 'postgresql':
        raise ValueError('El destino debe ser una base PostgreSQL')

    # Una transacción de lectura mantiene una fotografía consistente sin
    # modificar el archivo ni interrumpir a la aplicación local.
    uri = origen.as_uri() + '?mode=ro'
    fuente = create_engine('sqlite://', creator=lambda: sqlite3.connect(uri, uri=True), poolclass=NullPool)
    destino = create_engine(destino_url, pool_pre_ping=True)
    try:
        with fuente.connect() as lectura, destino.begin() as escritura:
            lectura.exec_driver_sql('BEGIN')
            inspector_origen = inspect(lectura)
            tablas_origen = set(inspector_origen.get_table_names()) - {'sqlite_sequence'}
            esperadas = set(Base.metadata.tables)
            if tablas_origen != esperadas:
                raise ValueError('Las tablas de la base local no coinciden con esta versión')
            for tabla in Base.metadata.sorted_tables:
                columnas = {c['name'] for c in inspector_origen.get_columns(tabla.name)}
                if columnas != {c.name for c in tabla.columns}:
                    raise ValueError(f'Las columnas de {tabla.name} no coinciden con esta versión')

            # No crea ni modifica tablas en una base que ya contiene datos u
            # otras tablas: evita mezclar la aplicación anterior con la nueva.
            if inspect(escritura).get_table_names(schema='public'):
                raise ValueError('El destino no está vacío; usa una base nueva y separada')
            Base.metadata.create_all(escritura)
            totales = {}
            for tabla in Base.metadata.sorted_tables:
                resultado = lectura.execute(select(tabla)).mappings()
                cantidad = 0
                while lote := resultado.fetchmany(500):
                    escritura.execute(tabla.insert(), [dict(fila) for fila in lote])
                    cantidad += len(lote)
                copiados = escritura.execute(select(func.count()).select_from(tabla)).scalar_one()
                if copiados != cantidad:
                    raise ValueError(f'No coincide la cantidad de registros en {tabla.name}')
                totales[tabla.name] = cantidad

            # Los IDs originales se conservan; las secuencias deben avanzar
            # para que la siguiente inserción no reutilice un ID ya copiado.
            for tabla in Base.metadata.sorted_tables:
                if 'id' not in tabla.c or not isinstance(tabla.c.id.type, Integer):
                    continue
                secuencia = escritura.execute(text('SELECT pg_get_serial_sequence(:tabla, :columna)'),
                    {'tabla': f'public."{tabla.name}"', 'columna': 'id'}).scalar()
                if secuencia:
                    ultimo = escritura.execute(select(func.max(tabla.c.id))).scalar() or 0
                    escritura.execute(text('SELECT setval(CAST(:secuencia AS regclass), :valor, :usada)'),
                        {'secuencia': secuencia, 'valor': max(ultimo, 1), 'usada': ultimo > 0})
            return totales
    finally:
        fuente.dispose()
        destino.dispose()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--origen', default='ganga_saas.db', help='Archivo SQLite local; se abre en modo solo lectura')
    args = parser.parse_args()
    url = os.environ.get('GANGA_DESTINO_POSTGRES') or getpass.getpass('Cadena PostgreSQL de la base nueva (no se mostrará): ')
    try:
        totales = copiar_sqlite_a_postgres(args.origen, url)
    except Exception as exc:
        # Los detalles del controlador pueden contener credenciales o datos.
        print(f'No se pudo completar la copia ({type(exc).__name__}). Verifica que el destino sea una base nueva y esté accesible.')
        raise SystemExit(1) from None
    print(f'Copia completa: {len(totales)} tablas y {sum(totales.values())} registros.')


if __name__ == '__main__':
    main()
