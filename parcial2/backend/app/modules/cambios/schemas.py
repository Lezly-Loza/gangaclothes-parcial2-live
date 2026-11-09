from pydantic import BaseModel, Field
from decimal import Decimal


class CotizarIn(BaseModel):
    venta_id: int
    variante_devuelta_id: int
    variante_nueva_id: int | None = None


class CambioIn(CotizarIn):
    motivo: str = Field(min_length=1)
    diferencia_esperada: Decimal | None = None
