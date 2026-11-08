"""Restaurar a una base SQLite nueva; nunca modifica una base existente."""
import argparse
from datetime import date, datetime
from decimal import Decimal
import json
import os
from pathlib import Path
from sqlalchemy import Boolean, Date, DateTime, Numeric, create_engine, event
from ... import models  # noqa: F401: registra todas las tablas
from ...core.database import Base
from .service import verificar_respaldo


def restaurar_en_sqlite(datos, destino):
    verificar_respaldo(datos)
    destino = Path(destino).resolve()
    fd = os.open(destino, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    os.close(fd)
    engine = create_engine(f'sqlite:///{destino.as_posix()}')
    @event.listens_for(engine, 'connect')
    def activar_fk(conexion, _):
        conexion.execute('PRAGMA foreign_keys=ON')
    try:
        Base.metadata.create_all(engine)
        with engine.begin() as conn:
            for tabla in Base.metadata.sorted_tables:
                for fila in datos['tablas'].get(tabla.name, []):
                    convertida = {}
                    for columna in tabla.columns:
                        valor = fila[columna.name]
                        if valor is not None:
                            if isinstance(columna.type, DateTime): valor = datetime.fromisoformat(valor)
                            elif isinstance(columna.type, Date): valor = date.fromisoformat(valor)
                            elif isinstance(columna.type, Numeric): valor = Decimal(str(valor))
                            elif isinstance(columna.type, Boolean): valor = bool(valor)
                        convertida[columna.name] = valor
                    conn.execute(tabla.insert().values(**convertida))
            if conn.exec_driver_sql('PRAGMA foreign_key_check').fetchall():
                raise ValueError('El respaldo contiene referencias inválidas')
    finally:
        engine.dispose()
    return destino


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archivo', required=True)
    parser.add_argument('--destino', required=True, help='Archivo SQLite nuevo que aún no exista')
    args = parser.parse_args()
    with open(args.archivo, encoding='utf-8') as archivo:
        datos = json.load(archivo)
    print(f'Restaurado en {restaurar_en_sqlite(datos, args.destino)}')


if __name__ == '__main__': main()
