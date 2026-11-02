from pydantic import BaseModel, EmailStr, Field


class UsuarioIn(BaseModel):
    nombre: str
    email: EmailStr
    password: str = Field(min_length=8)
    rol: str


class UsuarioUpdateIn(BaseModel):
    nombre: str | None = None
    rol: str | None = None
    activo: bool | None = None
