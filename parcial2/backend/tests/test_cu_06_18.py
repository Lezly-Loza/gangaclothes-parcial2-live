from datetime import datetime, timedelta, timezone

import pytest


def headers(token):
    return {"Authorization": f"Bearer {token}"}


def login(client, email, rol="luna"):
    r = client.post("/api/v1/auth/login", json={"codigo_tenant": rol, "email": email,
                                                  "password": "Luna12345" if rol == "luna" else "Andina12345"})
    assert r.status_code == 200, r.text
    return headers(r.json()["access_token"])


def _seed_ids():
    from app.core.database import SessionLocal
    from app.models import Cliente, Inventario, Producto, Sucursal, Variante, Venta
    with SessionLocal() as db:
        p = db.query(Producto).filter_by(nombre="Polera clásica").one()
        v = db.query(Variante).filter_by(producto_id=p.id).first()
        s = db.query(Sucursal).filter_by(tenant_id=p.tenant_id).first()
        c = db.query(Cliente).filter_by(tenant_id=p.tenant_id).first()
        old = db.query(Venta).filter_by(codigo="DEMO-V-1").one()
        inv = db.query(Inventario).filter_by(tenant_id=p.tenant_id, sucursal_id=s.id, variante_id=v.id).one()
        return dict(producto=p.id, variante=v.id, sucursal=s.id, cliente=c.id,
                    vieja=old.id, stock=inv.stock)


def test_cu12_salida_sin_stock(client):
    ids = _seed_ids()
    h = login(client, "encargado@boutique-luna.bo")
    r = client.post("/api/v1/inventario/movimientos", headers=h,
                    json={"sucursal_id": ids["sucursal"], "variante_id": ids["variante"],
                          "tipo": "SALIDA", "cantidad": 999, "motivo": "Prueba"})
    assert r.status_code == 409


def test_cu14_reserva_sin_stock(client):
    ids = _seed_ids()
    h = login(client, "cliente@boutique-luna.bo")
    r = client.post("/api/v1/reservas", headers=h,
                    json={"sucursal_id": ids["sucursal"], "variante_id": ids["variante"],
                          "cliente_id": ids["cliente"], "cantidad": 999})
    assert r.status_code == 409


def test_cu15_y_cu17_venta_y_anulacion(client):
    ids = _seed_ids()
    vendedor = login(client, "vendedor@boutique-luna.bo")
    encargado = login(client, "encargado@boutique-luna.bo")
    r = client.post("/api/v1/ventas", headers=vendedor,
                    json={"sucursal_id": ids["sucursal"], "cliente_id": ids["cliente"],
                          "forma_pago": "EFECTIVO", "items": [{"variante_id": ids["variante"], "cantidad": 1}]})
    assert r.status_code == 201, r.text
    id_ = r.json()["id"]
    from app.core.database import SessionLocal
    from app.models import Inventario, MovimientoInventario
    with SessionLocal() as db:
        assert db.query(Inventario).filter_by(sucursal_id=ids["sucursal"], variante_id=ids["variante"]).one().stock == ids["stock"] - 1
        assert db.query(MovimientoInventario).filter_by(variante_id=ids["variante"], tipo="VENTA").count() >= 1
    r = client.post(f"/api/v1/ventas/{id_}/anular", headers=encargado, json={"motivo": "Devolución"})
    assert r.status_code == 200, r.text
    with SessionLocal() as db:
        assert db.query(Inventario).filter_by(sucursal_id=ids["sucursal"], variante_id=ids["variante"]).one().stock == ids["stock"]
    assert client.post(f"/api/v1/ventas/{id_}/anular", headers=encargado,
                       json={"motivo": "Otra vez"}).status_code == 409


def test_cu16_fuera_de_plazo(client):
    ids = _seed_ids()
    h = login(client, "vendedor@boutique-luna.bo")
    r = client.post("/api/v1/cambios", headers=h,
                    json={"venta_id": ids["vieja"], "variante_devuelta_id": ids["variante"],
                          "variante_nueva_id": ids["variante"], "motivo": "Talla"})
    assert r.status_code == 409
    assert r.json()["detail"] == "Fuera de plazo"


def test_cu06_bajar_plan(client, token_luna):
    r = client.post("/api/v1/suscripciones/cambiar", headers=headers(token_luna),
                    json={"plan_codigo": "basico"})
    assert r.status_code == 409
    assert r.json()["detail"] == "El uso actual supera el plan elegido"


def test_aislamiento_productos_y_ventas(client, token_andina):
    ids = _seed_ids()
    r = client.get(f"/api/v1/productos/{ids['producto']}", headers=headers(token_andina))
    assert r.status_code == 404
    # Un código de venta de Luna no revela datos al tenant Andina.
    h = login(client, "rodrigo@modaandina.bo", "andina")
    # Este endpoint requiere vendedor/admin; Rodrigo es admin.
    r = client.get("/api/v1/ventas/DEMO-V-1", headers=h)
    assert r.status_code == 404
