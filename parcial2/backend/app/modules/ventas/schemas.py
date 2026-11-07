from pydantic import BaseModel, ConfigDict, Field
from decimal import Decimal


class ItemVentaIn(BaseModel):
    variante_id: int
    cantidad: int = Field(gt=0)


class VentaIn(BaseModel):
    sucursal_id: int
    cliente_id: int | None = None
    forma_pago: str
    items: list[ItemVentaIn] = Field(min_length=1)
    uuid_operacion: str | None = None
    reserva_id: int | None = None
    monto_recibido: Decimal | None = Field(default=None, ge=0)


class VentaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    codigo: str
    total: float
    estado: str
    comprobante: str
    items: list[dict] = Field(default_factory=list)


class AnularIn(BaseModel):
    motivo: str = Field(min_length=1)
