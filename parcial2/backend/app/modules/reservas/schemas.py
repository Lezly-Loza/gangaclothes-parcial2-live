from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class ReservaIn(BaseModel):
    sucursal_id: int
    variante_id: int
    cliente_id: int
    cantidad: int = Field(gt=0)
    uuid_operacion: str | None = None


class ReservaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    codigo: str
    sucursal_id: int
    cliente_id: int
    fecha_limite: datetime
    estado: str


class AnularIn(BaseModel):
    motivo: str = Field(min_length=1)
