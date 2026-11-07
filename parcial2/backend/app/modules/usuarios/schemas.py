from pydantic import BaseModel, EmailStr, Field


class UsuarioIn(BaseModel):
    nombre: str
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)
    rol: str | None = None
    roles: list[str] | None = None
    apellido: str | None = None
    telefono: str | None = None
    proveedor_id: int | None = None


class UsuarioUpdateIn(BaseModel):
    nombre: str | None = None
    rol: str | None = None
    roles: list[str] | None = None
    activo: bool | None = None
    apellido: str | None = None
    telefono: str | None = None
    proveedor_id: int | None = None
