from pydantic import BaseModel, Field


class VarianteIn(BaseModel):
    sku: str
    talla_id: int | None = None
    color_id: int | None = None
    precio: float = Field(ge=0)


class ProductoIn(BaseModel):
    nombre: str
    descripcion: str | None = None
    categoria_id: int | None = None
    temporada_id: int | None = None
    precio_base: float = Field(ge=0)
    imagen_url: str | None = None
    variantes: list[VarianteIn] = []


class ProductoUpdateIn(BaseModel):
    nombre: str | None = None
    descripcion: str | None = None
    categoria_id: int | None = None
    temporada_id: int | None = None
    precio_base: float | None = None
    imagen_url: str | None = None
