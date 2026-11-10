from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .core.config import get_settings
from .core.database import init_db
from .modules.auth.router import router as auth_router
from .modules.planes.router import router as planes_router
from .modules.sucursales.router import router as sucursales_router
from .modules.suscripciones.router import router as suscripciones_router
from .modules.tenants.router import router as tenants_router
from .modules.usuarios.router import router as usuarios_router
from .modules.catalogos.router import router as catalogos_router
from .modules.productos.router import router as productos_router
from .modules.proveedores.router import router as proveedores_router
from .modules.clientes.router import router as clientes_router
from .modules.inventario.router import router as inventario_router
from .modules.reservas.router import router as reservas_router
from .modules.ventas.router import router as ventas_router
from .modules.cambios.router import router as cambios_router
from .modules.offline.router import router as offline_router
from .modules.seguridad.router import router as seguridad_router
from .modules.catalogos.compatibilidad import router as catalogos_compat_router
from .modules.productos.panel import router as prendas_panel_router
from .modules.proveedores.compras import router as compras_router
from .modules.ventas.envios import router as envios_router
from .modules.ventas.reportes import router as reportes_router
from .modules.productos.promociones import router as promociones_router
from .modules.productos.catalogo_tienda import router as catalogo_tienda_router
from .modules.ventas.tienda import router as tienda_router
from .modules.offline.sincronizacion import router as sincronizacion_router
from .modules.ventas.analitica import router as analitica_router
from .modules.respaldos.router import router as respaldos_router
from .modules.ia.router import router as ia_router
from .modules.pasarela.router import router as pagos_router


settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    try:
        from .seeds.poblar_completo_evaluacion import ejecutar_poblamiento
        ejecutar_poblamiento()
    except Exception as e:
        import logging
        logging.getLogger("uvicorn.error").warning("Error ejecutando poblar_completo_evaluacion: %s", e)
    from .modules.respaldos.programacion import iniciar
    detener, hilo = iniciar()
    try:
        yield
    finally:
        detener.set()
        hilo.join(timeout=5)


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        description=(
            "SaaS multitenant para tiendas de ropa. Parcial 2 SI2 UAGRM.\n\n"
            "Aislamiento central por `tenant_id` via listener de SQLAlchemy "
            "`do_orm_execute` + `with_loader_criteria` sobre `TenantMixin`."
        ),
        lifespan=lifespan,
    )

    origins = [o.strip() for o in settings.cors_origins.split(",")] if settings.cors_origins else []
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins or ["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    prefix = settings.api_v1_prefix
    app.include_router(auth_router, prefix=prefix)
    app.include_router(tenants_router, prefix=prefix)
    app.include_router(sucursales_router, prefix=prefix)
    app.include_router(suscripciones_router, prefix=prefix)
    app.include_router(planes_router, prefix=prefix)
    for router in (usuarios_router, catalogos_router, productos_router, proveedores_router,
                   clientes_router, inventario_router, reservas_router, ventas_router,
                   cambios_router, offline_router, seguridad_router, catalogos_compat_router, prendas_panel_router, compras_router, envios_router, reportes_router, promociones_router, catalogo_tienda_router, tienda_router, sincronizacion_router, analitica_router, respaldos_router, ia_router, pagos_router):
        app.include_router(router, prefix=prefix)

    @app.get("/health", tags=["health"])
    def health():
        return {"status": "ok", "app": settings.app_name}

    return app


app = create_app()
