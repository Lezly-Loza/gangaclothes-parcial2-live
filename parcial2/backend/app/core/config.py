from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "GangaSaaS Parcial2"
    api_v1_prefix: str = "/api/v1"

    database_url: str = "sqlite:///./ganga_saas.db"

    jwt_secret: str = "cambia-esto-en-produccion-por-un-secret-largo-y-aleatorio"
    jwt_alg: str = "HS256"
    jwt_exp_minutes: int = 60 * 8

    cors_origins: str = "*"

    stripe_secret_key: str = ""
    stripe_public_key: str = ""
    stripe_api_base: str = "https://api.stripe.com/v1"

    bcp_modo: str = "simulado"
    bcp_usuario: str = ""
    bcp_password: str = ""
    bcp_app_user_id: str = ""
    bcp_public_token: str = ""
    bcp_business_code: str = ""
    bcp_service_code: str = "050"
    bcp_cert_pem: str = ""
    bcp_cert_key: str = ""
    bcp_cert_pfx: str = ""
    bcp_cert_password: str = ""
    bcp_qr_minutos: int = 15
    bcp_simulador_segundos: int = 8

    gemini_api: str = ""
    gemini_api_key: str = ""
    google_api_key: str = ""
    gemini_modelo: str = "gemini-3.5-flash-lite,gemini-3.8-flash"


@lru_cache
def get_settings() -> Settings:
    return Settings()
