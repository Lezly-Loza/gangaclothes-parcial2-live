from typing import Literal

from pydantic import BaseModel, Field


class AnulacionIn(BaseModel):
    """CU-17: anular una reserva o venta.

    Boundary: datos que envía el operador desde el modal de anulación.
    Solo encargado o administrador pueden anular.
    """
    tipo_operacion: Literal["VENTA", "RESERVA"]
    operacion_id: int
    motivo: str = Field(min_length=5, max_length=300,
                        description="Justificación obligatoria para la anulación")
