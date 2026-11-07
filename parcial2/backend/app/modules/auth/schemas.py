from pydantic import BaseModel, EmailStr, Field


class LoginIn(BaseModel):
    """CU-02: login con contexto de tenant.
    El tenant se identifica por su codigo + email + password.
    (Elegimos codigo de tenant en el formulario; justificacion en el README.)
    """
    codigo_tenant: str = Field(min_length=1, max_length=50)
    email: EmailStr
    password: str


class SuperLoginIn(BaseModel):
    """Login del superadministrador de plataforma. Sin tenant."""
    email: EmailStr
    password: str


class RegistroClienteIn(BaseModel):
    codigo_tenant: str = Field(min_length=1, max_length=50)
    nombre: str = Field(min_length=1, max_length=100)
    apellido: str | None = Field(default=None, max_length=100)
    documento: str = Field(min_length=1, max_length=60)
    telefono: str | None = Field(default=None, max_length=50)
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    kind: str
    """'tenant' o 'super'."""
    tenant_id: int | None = None
    tenant_codigo: str | None = None
    user_id: int
    nombre: str
    roles: list[str]
    permisos: list[str] = Field(default_factory=list)


class MeOut(BaseModel):
    kind: str
    user_id: int
    nombre: str
    email: str
    roles: list[str]
    permisos: list[str] = Field(default_factory=list)
    tenant_id: int | None = None
    tenant_codigo: str | None = None
    tenant_razon_social: str | None = None
