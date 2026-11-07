from datetime import datetime, timedelta


def headers(token): return {'Authorization': f'Bearer {token}'}


def test_flujo_cliente_y_aislamiento(client, token_luna, token_andina):
    login = client.post('/api/v1/auth/login', json={'codigo_tenant': 'luna', 'email': 'cliente@boutique-luna.bo', 'password': 'Luna12345'})
    hc = headers(login.json()['access_token'])
    opts = client.get('/api/v1/catalogo/opciones', headers=hc).json()
    sid = opts['sucursales'][0]['id']
    catalogo = client.get(f'/api/v1/catalogo?sucursal_id={sid}', headers=hc).json()
    variante = next(v for p in catalogo for v in p['variantes'] if v['disponible_total'] >= 3)
    vid = variante['id']; disponible = variante['disponibilidad'][0]['disponible']
    cita = (datetime.utcnow() - timedelta(hours=4) + timedelta(days=1)).replace(microsecond=0).isoformat()
    reserva = client.post('/api/v1/tienda/reservas', headers=hc, json={'sucursal_id': sid, 'fecha_hora_prueba': cita, 'detalle': [{'variante_id': vid, 'cantidad': 1}]})
    assert reserva.status_code == 201, reserva.text
    rid = reserva.json()['id']; codigo = reserva.json()['codigo']
    assert reserva.json()['fecha_hora_prueba'] == cita
    assert client.get('/api/v1/tienda/reservas', headers=hc).json()[0]['codigo'] == codigo
    otro = client.post('/api/v1/auth/register', json={'codigo_tenant': 'luna', 'nombre': 'Otra Clienta',
        'documento': 'DOC99971', 'email': 'otra-tienda@ejemplo.bo', 'password': 'Segura123'})
    assert otro.status_code == 201, otro.text
    ho = headers(otro.json()['access_token'])
    assert client.get('/api/v1/tienda/reservas', headers=ho).json() == []
    assert client.post(f'/api/v1/tienda/reservas/{rid}/cancelar', headers=ho).status_code == 404
    assert client.post(f'/api/v1/tienda/reservas/{rid}/cancelar', headers=headers(token_andina)).status_code == 403
    assert client.post(f'/api/v1/tienda/reservas/{rid}/cancelar', headers=hc).json()['estado'] == 'cancelada'
    assert client.get('/api/v1/tienda/carrito', headers=hc).json() is None
    assert client.post('/api/v1/tienda/carrito', headers=hc, json={'sucursal_id': sid}).status_code == 200
    agregar = client.post('/api/v1/tienda/carrito/items', headers=hc, json={'variante_id': vid, 'cantidad': 1})
    assert agregar.status_code == 200 and agregar.json()['detalle'][0]['disponible'] == disponible
    assert client.put(f'/api/v1/tienda/carrito/items/{vid}', headers=hc, json={'cantidad': disponible + 1}).status_code in (409, 422)
    assert client.post('/api/v1/tienda/carrito/comprar', headers=hc, json={'direccion': 'Calle prueba'}).status_code == 422
    compra = client.post('/api/v1/tienda/carrito/comprar', headers=hc, json={'direccion': 'Calle prueba 123', 'latitud': -17.78, 'longitud': -63.18})
    assert compra.status_code == 200, compra.text
    assert compra.json()['codigo'].startswith('V-')
    assert client.get('/api/v1/tienda/carrito', headers=hc).json() is None
    assert client.post('/api/v1/tienda/carrito/comprar', headers=hc, json={}).status_code == 409
    compras = client.get('/api/v1/tienda/compras', headers=hc).json()
    assert compras[0]['nro_comprobante'] == compra.json()['codigo']
    assert 'Simulado' in compras[0]['pagos'][0]['metodo']
    assert client.get('/api/v1/tienda/compras', headers=ho).json() == []
    assert client.get('/api/v1/tienda/pedidos', headers=ho).json() == []
    pedidos = client.get('/api/v1/tienda/pedidos', headers=hc).json()
    assert pedidos[0]['estado'] == 'pendiente' and pedidos[0]['venta']['nro_comprobante'] == compra.json()['codigo']
    eid = pedidos[0]['id']
    assert client.post(f'/api/v1/envios/{eid}/asignar', headers=headers(token_luna), json={'repartidor': 'Repartidor Prueba'}).status_code == 200
    assert client.get('/api/v1/tienda/pedidos', headers=hc).json()[0]['estado'] == 'asignado'
    assert client.get('/api/v1/tienda/pedidos', headers=headers(token_andina)).status_code == 403
    assert client.get('/api/v1/tienda/compras').status_code == 401
