"""CU-26: Dashboard analítico con Machine Learning.

Solo accesible para roles con permiso 'reportes:ver'.
"""
from fastapi import APIRouter, Depends

from app.core.deps import get_db, require_permiso
from app.modules.analitica import service

router = APIRouter()
ver = require_permiso("reportes:ver")


@router.get("/dashboard", summary="CU-26: predicción de ventas y segmentación de clientes (ML)")
def dashboard_ml(db=Depends(get_db), _=Depends(ver)):
    """
    Boundary → Controller → Entity (ICONIX):
    - Boundary: este endpoint recibe la petición HTTP del dashboard Angular.
    - Controller: service.dashboard_ml() orquesta los modelos ML.
    - Entity: Venta, DetalleVenta, Cliente (leídos para entrenar/predecir).
    """
    return service.dashboard_ml(db)
