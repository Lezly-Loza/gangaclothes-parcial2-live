from pydantic import BaseModel, ConfigDict, Field


class MovimientoIn(BaseModel):
    sucursal_id: int
    variante_id: int
    tipo: str
    cantidad: int = Field(gt=0)
    motivo: str | None = None
    proveedor_id: int | None = None


class MovimientoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    sucursal_id: int
    variante_id: int
    tipo: str
    cantidad: int
    alerta_minimo: bool


class MinMaxIn(BaseModel):
    sucursal_id: int
    variante_id: int
    stock_min: int = Field(ge=0)
    stock_max: int = Field(ge=0)
