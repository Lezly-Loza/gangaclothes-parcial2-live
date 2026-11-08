from datetime import datetime, timedelta, timezone


def h(token): return {'Authorization': f'Bearer {token}'}


def test_cambio_cotiza_devolucion_y_detecta_cambio_de_precio(client, token_luna, token_andina):
    from app.core.database import SessionLocal
    from app.models import Inventario, Variante
    admin = h(token_luna)
    sucursal = client.get('/api/v1/sucursales', headers=admin).json()[0]['id']
    with SessionLocal() as db:
        variantes = db.query(Variante).filter_by(tenant_id=1, producto_id=1, activo=True).order_by(Variante.precio).all()
        barata, cara = variantes[0].id, variantes[-1].id
        precio_barata, precio_cara = float(variantes[0].precio), float(variantes[-1].precio)
    venta = client.post('/api/v1/ventas', headers=admin, json={'sucursal_id': sucursal, 'forma_pago': 'EFECTIVO',
        'monto_recibido': 1000, 'items': [{'variante_id': cara, 'cantidad': 1}]})
    assert venta.status_code == 201, venta.text
    cambio = {'venta_id': venta.json()['id'], 'variante_devuelta_id': cara, 'variante_nueva_id': barata}
    quote = client.post('/api/v1/cambios/cotizar', headers=admin, json=cambio)
    assert quote.status_code == 200, quote.text
    assert quote.json()['precio_pagado'] == precio_cara
    assert quote.json()['precio_nuevo'] == precio_barata
    assert quote.json()['devolver'] == precio_cara - precio_barata and quote.json()['cobrar'] == 0
    assert quote.json()['plazo_dias'] == 7
    assert client.post('/api/v1/cambios/cotizar', headers=h(token_andina), json=cambio).status_code == 404
    with SessionLocal() as db:
        variante = db.query(Variante).filter_by(tenant_id=1, id=barata).one()
        variante.precio += 1
        db.commit()
    obsoleta = client.post('/api/v1/cambios', headers=admin, json={**cambio, 'motivo': 'Talla', 'diferencia_esperada': quote.json()['diferencia']})
    assert obsoleta.status_code == 409
    actual = client.post('/api/v1/cambios/cotizar', headers=admin, json=cambio).json()
    registrado = client.post('/api/v1/cambios', headers=admin, json={**cambio, 'motivo': 'Talla', 'diferencia_esperada': actual['diferencia']})
    assert registrado.status_code == 201 and registrado.json()['devolver'] == actual['devolver']
    assert client.post('/api/v1/cambios/cotizar', headers=admin, json=cambio).status_code == 409
    with SessionLocal() as db:
        assert db.query(Inventario).filter_by(tenant_id=1, sucursal_id=sucursal, variante_id=barata).one().stock >= 0


def test_cambio_respeta_plazo_de_empresa(client, token_luna):
    from app.core.database import SessionLocal
    from app.models import Venta, DetalleVenta, Variante
    with SessionLocal() as db:
        venta = db.query(Venta).filter_by(tenant_id=1, codigo='DEMO-V-2').one()
        detalle = db.query(DetalleVenta).filter_by(tenant_id=1, venta_id=venta.id).first()
        otra = db.query(Variante).filter(Variante.tenant_id == 1, Variante.id != detalle.variante_id).first()
        venta.fecha = datetime.now(timezone.utc) - timedelta(days=8)
        datos = {'venta_id': venta.id, 'variante_devuelta_id': detalle.variante_id, 'variante_nueva_id': otra.id}
        db.commit()
    r = client.post('/api/v1/cambios/cotizar', headers=h(token_luna), json=datos)
    assert r.status_code == 409 and r.json()['detail'] == 'Fuera de plazo'
