from pydantic import BaseModel, Field


class CambioIn(BaseModel):
    venta_id: int
    variante_devuelta_id: int
    variante_nueva_id: int
    motivo: str = Field(min_length=1)
