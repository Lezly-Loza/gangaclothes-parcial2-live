from pydantic import BaseModel


class ProveedorIn(BaseModel):
    razon_social: str
    nit: str
    contacto: str | None = None
    telefono: str | None = None
    correo: str | None = None


class ProveedorUpdateIn(BaseModel):
    razon_social: str | None = None
    nit: str | None = None
    contacto: str | None = None
    telefono: str | None = None
    correo: str | None = None
