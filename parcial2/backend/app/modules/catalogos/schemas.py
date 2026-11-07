from datetime import date
from pydantic import BaseModel


class RegistroIn(BaseModel):
    nombre: str
    codigo_hex: str | None = None
    fecha_inicio: date | None = None
    fecha_fin: date | None = None
