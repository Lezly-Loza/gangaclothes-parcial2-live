from pydantic import BaseModel, ConfigDict, Field


class ItemVentaIn(BaseModel):
    variante_id: int
    cantidad: int = Field(gt=0)


class VentaIn(BaseModel):
    sucursal_id: int
    cliente_id: int | None = None
    forma_pago: str
    items: list[ItemVentaIn] = Field(min_length=1)
    uuid_operacion: str | None = None


class VentaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    codigo: str
    total: float
    estado: str
    comprobante: str


class AnularIn(BaseModel):
    motivo: str = Field(min_length=1)
