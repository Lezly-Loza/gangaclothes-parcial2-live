from datetime import datetime, timedelta, timezone


def h(token): return {'Authorization': f'Bearer {token}'}


def test_registro_cliente_y_catalogo_aislado(client, token_luna, token_andina):
    registro = client.post('/api/v1/auth/register', json={'codigo_tenant': 'luna', 'nombre': 'Cliente Nuevo',
        'documento': '123987', 'email': 'nuevo-cliente@ejemplo.bo', 'password': 'Segura123'})
    assert registro.status_code == 201, registro.text
    assert registro.json()['roles'] == ['cliente']
    hc = h(registro.json()['access_token'])
    sucursal = client.get('/api/v1/sucursales', headers=hc).json()[0]['id']
    categorias = client.get('/api/v1/offline/opciones', headers=hc).json()['categorias']
    catalogo = client.get(f'/api/v1/offline/catalogo?sucursal_id={sucursal}', headers=hc)
    assert catalogo.status_code == 200 and catalogo.json()['productos']
    assert categorias
    prenda = catalogo.json()['productos'][0]
    filtro = client.get(f"/api/v1/offline/catalogo?sucursal_id={sucursal}&categoria_id={prenda['categoria_id']}", headers=hc).json()
    assert all(p['categoria_id'] == prenda['categoria_id'] for p in filtro['productos'])
    assert client.post(f"/api/v1/prendas/{prenda['id']}/despublicar", headers=h(token_luna)).status_code == 200
    assert prenda['id'] not in {p['id'] for p in client.get(f'/api/v1/offline/catalogo?sucursal_id={sucursal}', headers=hc).json()['productos']}
    otro = client.get('/api/v1/sucursales', headers=h(token_andina)).json()[0]['id']
    assert client.get(f'/api/v1/offline/catalogo?sucursal_id={otro}', headers=hc).status_code == 404
    assert client.post('/api/v1/auth/register', json={'codigo_tenant': 'luna', 'nombre': 'Otra',
        'documento': '123987', 'email': 'otro@ejemplo.bo', 'password': 'Segura123'}).status_code == 409


def test_promocion_aplica_en_caja_y_guarda_descuento(client, token_luna, token_andina):
    luna, andina = h(token_luna), h(token_andina)
    sucursal = client.get('/api/v1/sucursales', headers=luna).json()[0]['id']
    fila = next(f for f in client.get(f'/api/v1/inventario?sucursal_id={sucursal}', headers=luna).json() if f['disponible'] > 0)
    hoy = (datetime.now(timezone.utc) - timedelta(hours=4)).date().isoformat()
    body = {'nombre': 'Descuento prueba', 'tipo_descuento': 'porcentaje', 'valor': 20,
            'fecha_inicio': hoy, 'fecha_fin': hoy, 'prenda_ids': [fila['prenda_id']]}
    promo = client.post('/api/v1/promociones', headers=luna, json=body)
    assert promo.status_code == 201, promo.text
    assert client.put(f"/api/v1/promociones/{promo.json()['id']}", headers=andina, json={'activo': False}).status_code == 404
    venta = client.post('/api/v1/ventas', headers=luna, json={'sucursal_id': sucursal, 'forma_pago': 'EFECTIVO',
                        'monto_recibido': 10000, 'items': [{'variante_id': fila['variante_id'], 'cantidad': 1}]})
    assert venta.status_code == 201, venta.text
    item = venta.json()['items'][0]
    assert item['promocion'] == 'Descuento prueba'
    assert item['precio_unitario'] < item['precio_lista'] and item['descuento'] > 0
    reporte = client.get('/api/v1/reportes/ventas', headers=luna).json()
    linea = next(v for v in reporte['ventas'] if v['id'] == venta.json()['id'])
    assert linea['descuento'] == item['descuento']
    assert round(linea['subtotal'] - linea['descuento'], 2) == linea['total']
    assert client.put(f"/api/v1/promociones/{promo.json()['id']}", headers=luna, json={'activo': False}).status_code == 200
    historial = client.post('/api/v1/ventas', headers=luna, json={'sucursal_id': sucursal, 'forma_pago': 'EFECTIVO',
                         'items': [{'variante_id': fila['variante_id'], 'cantidad': 1}]})
    assert historial.json()['items'][0]['promocion'] is None


def test_codigos_recientes_solo_del_tenant(client, token_luna, token_andina):
    luna, andina = h(token_luna), h(token_andina)
    recientes = client.get('/api/v1/operaciones/recientes?tipo=ventas', headers=luna)
    assert recientes.status_code == 200 and recientes.json()
    codigo = recientes.json()[0]['codigo']
    assert codigo not in {v['codigo'] for v in client.get('/api/v1/operaciones/recientes?tipo=ventas', headers=andina).json()}


def test_catalogo_cliente_muestra_stock_y_aisla_empresas(client, token_luna, token_andina):
    sesion = client.post('/api/v1/auth/login', json={'codigo_tenant': 'luna',
                         'email': 'cliente@boutique-luna.bo', 'password': 'Luna12345'})
    hc = h(sesion.json()['access_token'])
    opciones = client.get('/api/v1/catalogo/opciones', headers=hc)
    assert opciones.status_code == 200 and len(opciones.json()['sucursales']) == 2
    for sucursal in opciones.json()['sucursales']:
        catalogo = client.get(f"/api/v1/catalogo?sucursal_id={sucursal['id']}", headers=hc)
        assert catalogo.status_code == 200 and catalogo.json()
        assert all(p['disponible_total'] > 0 for p in catalogo.json())
        assert all(v['sucursal_id'] == sucursal['id'] for p in catalogo.json() for x in p['variantes'] for v in x['disponibilidad'])
    otro = client.get('/api/v1/sucursales', headers=h(token_andina)).json()[0]['id']
    assert client.get(f'/api/v1/catalogo?sucursal_id={otro}', headers=hc).status_code == 404
    assert client.get('/api/v1/catalogo').status_code == 401
