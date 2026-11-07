from pydantic import BaseModel, ConfigDict, Field, field_validator


class MovimientoIn(BaseModel):
    sucursal_id: int
    variante_id: int
    tipo: str
    cantidad: int = Field(ge=0)
    motivo: str | None = None
    proveedor_id: int | None = None

    @field_validator("tipo")
    @classmethod
    def normalizar_tipo(cls, valor: str) -> str:
        return {"INGRESO": "ENTRADA"}.get(valor.upper(), valor.upper())


class MovimientoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    sucursal_id: int
    variante_id: int
    tipo: str
    cantidad: int
    alerta_minimo: bool
    movimiento: dict | None = None
    stock_anterior: int | None = None
    stock_actual: int | None = None
    inventario: dict | None = None


class MinMaxIn(BaseModel):
    sucursal_id: int
    variante_id: int
    stock_min: int = Field(ge=0)
    stock_max: int = Field(ge=0)


class LimitesPanel(BaseModel):
    stock_minimo: int = Field(ge=0)
    stock_maximo: int = Field(ge=0)
