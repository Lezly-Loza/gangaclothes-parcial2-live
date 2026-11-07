from datetime import datetime

from pydantic import BaseModel, Field


class LineaReservaIn(BaseModel):
    variante_id: int
    cantidad: int = Field(default=1, gt=0)


class ReservaIn(BaseModel):
    """El cliente se infiere del token o se puede indicar en el body (CU-14)."""

    sucursal_id: int
    fecha_hora_prueba: datetime | None = None
    notas: str | None = Field(default=None, max_length=200)
    detalle: list[LineaReservaIn] = Field(default_factory=list)

    # Campos simplificados CU-14
    variante_id: int | None = None
    cantidad: int | None = Field(default=None, gt=0)
    cliente_id: int | None = None

    def normalizar(self) -> None:
        if not self.detalle and self.variante_id is not None:
            self.detalle = [LineaReservaIn(variante_id=self.variante_id, cantidad=self.cantidad or 1)]
        if self.fecha_hora_prueba is None:
            from datetime import timedelta
            self.fecha_hora_prueba = datetime.now() + timedelta(days=1)
