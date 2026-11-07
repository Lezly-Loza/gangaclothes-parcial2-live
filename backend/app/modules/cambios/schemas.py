from pydantic import BaseModel, Field


class CambioIn(BaseModel):
    """CU-16: datos del cambio de prenda.

    Boundary: recibe lo que el frontend envía para iniciar el cambio.
    La venta se busca por ID; los items por variante_id.
    """
    venta_id: int
    variante_devuelta_id: int
    variante_nueva_id: int
    motivo: str = Field(max_length=200)
