from datetime import datetime, timedelta, timezone
from uuid import uuid4
from concurrent.futures import ThreadPoolExecutor


def h(token): return {'Authorization': f'Bearer {token}'}


def test_sincronizacion_idempotente_y_conflictos(client, token_luna, token_andina):
    sesion = client.post('/api/v1/auth/login', json={'codigo_tenant': 'luna', 'email': 'cliente@boutique-luna.bo', 'password': 'Luna12345'}).json()
    hc, ha = h(sesion['access_token']), h(token_luna)
    sid = client.get('/api/v1/sucursales', headers=hc).json()[0]['id']
    copia = client.get(f'/api/v1/offline/catalogo?sucursal_id={sid}', headers=hc).json()
    item = next(v for v in copia['variantes'] if v['stock'] >= 2)
    cita = (datetime.now(timezone.utc) - timedelta(hours=4) + timedelta(days=1)).replace(tzinfo=None, microsecond=0).isoformat()
    operacion = {'uuid_operacion': str(uuid4()), 'tipo': 'reserva', 'sucursal_id': sid,
                 'variante_id': item['id'], 'cantidad': 1, 'precio_unitario': item['precio'],
                 'fecha_hora_prueba': cita, 'fecha_local': datetime.now(timezone.utc).isoformat()}
    primero = client.post('/api/v1/offline/sincronizar', headers=hc, json=operacion)
    assert primero.status_code == 200, primero.text
    segundo = client.post('/api/v1/offline/sincronizar', headers=hc, json=operacion)
    assert segundo.status_code == 200 and segundo.json()['repetida']
    assert segundo.json()['codigo'] == primero.json()['codigo']
    alterada = {**operacion, 'cantidad': 2}
    assert client.post('/api/v1/offline/sincronizar', headers=hc, json=alterada).status_code == 409
    assert client.post('/api/v1/offline/sincronizar', headers=ha, json=operacion).status_code == 409
    reserva = next(r for r in client.get('/api/v1/tienda/reservas', headers=hc).json() if r['codigo'] == primero.json()['codigo'])
    assert reserva['fecha_hora_prueba'] == cita and reserva['detalle'][0]['cantidad'] == 1
    assert client.post('/api/v1/offline/sincronizar', headers=hc, json={**operacion, 'uuid_operacion': str(uuid4()), 'cantidad': 100}).status_code == 409
    fecha_venta = (datetime.now(timezone.utc) - timedelta(days=1)).replace(microsecond=0)
    venta = {**operacion, 'uuid_operacion': str(uuid4()), 'tipo': 'venta', 'fecha_hora_prueba': None,
             'fecha_local': fecha_venta.isoformat(), 'monto_recibido': 10000}
    assert client.post('/api/v1/offline/sincronizar', headers=hc, json=venta).status_code == 403
    futura = {**venta, 'uuid_operacion': str(uuid4()), 'fecha_local': (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()}
    assert client.post('/api/v1/offline/sincronizar', headers=ha, json=futura).status_code == 409
    cambiado = {**venta, 'precio_unitario': float(item['precio']) + 1}
    assert client.post('/api/v1/offline/sincronizar', headers=ha, json=cambiado).status_code == 409
    assert client.post('/api/v1/offline/sincronizar', headers=h(token_andina), json=venta).status_code == 409
    creada = client.post('/api/v1/offline/sincronizar', headers=ha, json=venta)
    assert creada.status_code == 200, creada.text
    assert client.post('/api/v1/offline/sincronizar', headers=ha, json=venta).json()['repetida']
    from app.core.database import SessionLocal
    from app.models import Venta
    with SessionLocal() as db:
        assert db.query(Venta).filter_by(uuid_operacion=venta['uuid_operacion']).one().fecha == fecha_venta.replace(tzinfo=None)
    dia_local = (fecha_venta - timedelta(hours=4)).date().isoformat()
    reporte = client.get(f'/api/v1/reportes/ventas?desde={dia_local}&hasta={dia_local}', headers=ha).json()
    assert creada.json()['codigo'] in {fila['nro_comprobante'] for fila in reporte['ventas']}


def test_prenda_despublicada_es_un_conflicto_recuperable(client, token_luna):
    sesion = client.post('/api/v1/auth/login', json={'codigo_tenant': 'luna', 'email': 'cliente@boutique-luna.bo', 'password': 'Luna12345'}).json()
    hc = h(sesion['access_token'])
    sid = client.get('/api/v1/sucursales', headers=hc).json()[0]['id']
    copia = client.get(f'/api/v1/offline/catalogo?sucursal_id={sid}', headers=hc).json()
    item = next(v for v in copia['variantes'] if v['stock'] > 0)
    cita = (datetime.now(timezone.utc) - timedelta(hours=4) + timedelta(days=1)).replace(tzinfo=None, microsecond=0).isoformat()
    op = {'uuid_operacion': str(uuid4()), 'tipo': 'reserva', 'sucursal_id': sid, 'variante_id': item['id'],
          'cantidad': 1, 'precio_unitario': item['precio'], 'fecha_hora_prueba': cita, 'fecha_local': datetime.now(timezone.utc).isoformat()}
    assert client.post(f"/api/v1/prendas/{item['producto_id']}/despublicar", headers=h(token_luna)).status_code == 200
    resultado = client.post('/api/v1/offline/sincronizar', headers=hc, json=op)
    assert resultado.status_code == 409 and 'publicada' in resultado.json()['detail']
    assert client.post(f"/api/v1/prendas/{item['producto_id']}/publicar", headers=h(token_luna), json={}).status_code == 200
    assert client.post('/api/v1/offline/sincronizar', headers=hc, json=op).status_code == 200


def test_reintentos_simultaneos_no_duplican_venta(client, token_luna):
    from app.core.database import SessionLocal
    from app.models import Inventario, OperacionLog, Venta
    ha = h(token_luna)
    sid = client.get('/api/v1/sucursales', headers=ha).json()[0]['id']
    copia = client.get(f'/api/v1/offline/catalogo?sucursal_id={sid}', headers=ha).json()
    item = next(v for v in copia['variantes'] if v['stock'] > 0)
    op = {'uuid_operacion': str(uuid4()), 'tipo': 'venta', 'sucursal_id': sid, 'variante_id': item['id'],
          'cantidad': 1, 'precio_unitario': item['precio'], 'monto_recibido': 10000,
          'fecha_local': datetime.now(timezone.utc).isoformat()}
    with SessionLocal() as db:
        stock_previo = db.query(Inventario).filter_by(sucursal_id=sid, variante_id=item['id']).one().stock
    with ThreadPoolExecutor(max_workers=3) as pool:
        respuestas = list(pool.map(lambda _: client.post('/api/v1/offline/sincronizar', headers=ha, json=op), range(3)))
    assert all(r.status_code in (200, 503) for r in respuestas), [r.text for r in respuestas]
    repeticion = client.post('/api/v1/offline/sincronizar', headers=ha, json=op)
    assert repeticion.status_code == 200 and repeticion.json()['repetida']
    with SessionLocal() as db:
        assert db.query(Venta).filter_by(uuid_operacion=op['uuid_operacion']).count() == 1
        assert db.query(OperacionLog).filter_by(uuid_operacion=op['uuid_operacion']).count() == 1
        assert db.query(Inventario).filter_by(sucursal_id=sid, variante_id=item['id']).one().stock == stock_previo - 1
