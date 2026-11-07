from pydantic import BaseModel


class ClienteIn(BaseModel):
    nombre: str
    documento: str
    telefono: str | None = None
    correo: str | None = None
    user_id: int | None = None


class ClienteUpdateIn(BaseModel):
    nombre: str | None = None
    documento: str | None = None
    telefono: str | None = None
    correo: str | None = None
