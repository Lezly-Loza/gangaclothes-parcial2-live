def _h(token):
    return {"Authorization": f"Bearer {token}"}


def test_catalogos_del_panel_reusan_datos_del_tenant(client, token_luna, token_andina):
    luna, andina = _h(token_luna), _h(token_andina)
    ciudades = client.get('/api/v1/admin/ciudades', headers=luna)
    sucursales = client.get('/api/v1/admin/sucursales', headers=luna)
    assert ciudades.status_code == sucursales.status_code == 200
    assert len(sucursales.json()) == 2
    assert all(s['ciudad_id'] in {c['id'] for c in ciudades.json()} for s in sucursales.json())

    nueva = client.post('/api/v1/admin/categorias', headers=luna,
                        json={'nombre': 'Accesorios', 'descripcion': 'Complementos'})
    assert nueva.status_code == 201, nueva.text
    categoria = nueva.json()
    assert categoria['descripcion'] == 'Complementos'
    assert any(c['nombre'] == 'Accesorios' for c in client.get('/api/v1/catalogos/categorias', headers=luna).json())
    assert client.put(f"/api/v1/admin/categorias/{categoria['id']}", headers=andina,
                      json={'nombre': 'No debe cambiar'}).status_code == 404


def test_clientes_del_panel_y_limite_de_sucursales(client, token_luna, token_andina):
    luna, andina = _h(token_luna), _h(token_andina)
    cliente = client.post('/api/v1/admin/clientes', headers=luna,
                          json={'nombre': 'Cliente Panel', 'documento': '9876543', 'telefono': '70000000'})
    assert cliente.status_code == 201, cliente.text
    assert any(c['documento'] == '9876543' for c in client.get('/api/v1/clientes?q=9876543', headers=luna).json())
    assert client.delete(f"/api/v1/admin/clientes/{cliente.json()['id']}", headers=luna).status_code == 200
    assert not next(c for c in client.get('/api/v1/admin/clientes', headers=luna).json()
                    if c['id'] == cliente.json()['id'])['activo']

    ciudades = client.get('/api/v1/admin/ciudades', headers=andina).json()
    sucursal = client.post('/api/v1/admin/sucursales', headers=andina,
                           json={'nombre': 'Sucursal extra', 'ciudad_id': ciudades[0]['id'], 'direccion': 'Av. Principal'})
    assert sucursal.status_code == 409


def test_inventario_del_panel_movimientos_y_aislamiento(client, token_luna, token_andina):
    luna, andina = _h(token_luna), _h(token_andina)
    sucursal = client.get('/api/v1/admin/sucursales', headers=luna).json()[0]['id']
    filas = client.get(f'/api/v1/inventario?sucursal_id={sucursal}', headers=luna)
    assert filas.status_code == 200 and filas.json()
    fila = filas.json()[0]
    assert fila['sku'] and fila['prenda'] and fila['cantidad'] == fila['stock']
    limites = client.put(f"/api/v1/inventario/{fila['id']}", headers=luna,
                         json={'stock_minimo': fila['cantidad'] + 2, 'stock_maximo': fila['cantidad'] + 10})
    assert limites.status_code == 200, limites.text
    alertas = client.get(f'/api/v1/inventario/alertas?sucursal_id={sucursal}', headers=luna).json()
    assert any(a['id'] == fila['id'] for a in alertas)
    assert client.put(f"/api/v1/inventario/{fila['id']}", headers=andina,
                      json={'stock_minimo': 0, 'stock_maximo': 10}).status_code == 404
    movimiento = client.post('/api/v1/inventario/movimientos', headers=luna,
                             json={'sucursal_id': sucursal, 'variante_id': fila['variante_id'],
                                   'tipo': 'ingreso', 'cantidad': 3, 'motivo': 'Prueba'})
    assert movimiento.status_code == 201, movimiento.text
    assert movimiento.json()['stock_actual'] == fila['cantidad'] + 3
    assert movimiento.json()['movimiento']['tipo'] == 'ingreso'
    historial = client.get(f"/api/v1/inventario/movimientos?sucursal_id={sucursal}&variante_id={fila['variante_id']}", headers=luna)
    assert historial.status_code == 200 and historial.json()[0]['motivo'] == 'Prueba'


def test_prendas_panel_comparten_producto_variantes_e_inventario(client, token_luna, token_andina):
    luna, andina = _h(token_luna), _h(token_andina)
    categoria = client.get('/api/v1/admin/categorias', headers=luna).json()[0]['id']
    talla = client.get('/api/v1/admin/tallas', headers=luna).json()[0]['id']
    color = client.get('/api/v1/admin/colores', headers=luna).json()[0]['id']
    sucursal = client.get('/api/v1/admin/sucursales', headers=luna).json()[0]['id']
    creada = client.post('/api/v1/prendas', headers=luna,
                         json={'nombre': 'Prenda de prueba', 'categoria_id': categoria, 'precio_venta': 75, 'costo': 30})
    assert creada.status_code == 201, creada.text
    id = creada.json()['id']
    assert not creada.json()['publicado']
    assert any(p['id'] == id for p in client.get('/api/v1/productos', headers=luna).json())
    lote = client.post(f'/api/v1/prendas/{id}/variantes/lote', headers=luna,
                       json={'talla_ids': [talla], 'color_ids': [color], 'stock_inicial': [
                           {'sucursal_id': sucursal, 'cantidad': 4, 'stock_minimo': 1, 'stock_maximo': 10}]})
    assert lote.status_code == 201, lote.text
    variante = lote.json()['creadas'][0]
    assert variante['stock_total'] == 4
    inventario = client.get(f'/api/v1/inventario?sucursal_id={sucursal}', headers=luna).json()
    assert any(i['variante_id'] == variante['id'] and i['cantidad'] == 4 for i in inventario)
    assert client.post(f'/api/v1/prendas/{id}/publicar', headers=luna, json={}).json()['publicado']
    assert client.get(f'/api/v1/prendas/{id}/variantes', headers=andina).status_code == 404


def test_cambio_no_se_puede_repetir_por_misma_unidad(client, token_luna):
    h = _h(token_luna)
    sucursal = client.get('/api/v1/admin/sucursales', headers=h).json()[0]['id']
    filas = [f for f in client.get(f'/api/v1/inventario?sucursal_id={sucursal}', headers=h).json() if f['disponible'] > 1]
    assert len(filas) >= 2
    venta = client.post('/api/v1/ventas', headers=h, json={'sucursal_id': sucursal, 'forma_pago': 'EFECTIVO',
                       'items': [{'variante_id': filas[0]['variante_id'], 'cantidad': 1}]})
    assert venta.status_code == 201, venta.text
    body = {'venta_id': venta.json()['id'], 'variante_devuelta_id': filas[0]['variante_id'],
            'variante_nueva_id': filas[1]['variante_id'], 'motivo': 'Talla'}
    assert client.post('/api/v1/cambios', headers=h, json=body).status_code == 201
    assert client.post('/api/v1/cambios', headers=h, json=body).status_code == 409


def test_cliente_no_puede_usar_identidad_de_otro_cliente(client, token_luna):
    h = _h(token_luna)
    sucursal = client.get('/api/v1/admin/sucursales', headers=h).json()[0]['id']
    fila = client.get(f'/api/v1/inventario?sucursal_id={sucursal}', headers=h).json()[0]
    otros = client.get('/api/v1/clientes', headers=h).json()
    otro = next(c for c in otros if not c.get('user_id'))
    sesion = client.post('/api/v1/auth/login', json={'codigo_tenant': 'luna',
                         'email': 'cliente@boutique-luna.bo', 'password': 'Luna12345'})
    cliente = _h(sesion.json()['access_token'])
    reserva = client.post('/api/v1/reservas', headers=cliente, json={
        'sucursal_id': sucursal, 'variante_id': fila['variante_id'], 'cliente_id': otro['id'], 'cantidad': 1})
    assert reserva.status_code == 404
    venta = client.post('/api/v1/ventas', headers=cliente, json={
        'sucursal_id': sucursal, 'cliente_id': otro['id'], 'forma_pago': 'EFECTIVO',
        'items': [{'variante_id': fila['variante_id'], 'cantidad': 1}]})
    assert venta.status_code == 404


def test_catalogo_interno_y_ciclo_de_reserva(client, token_luna, token_andina):
    luna, andina = _h(token_luna), _h(token_andina)
    sucursal = client.get('/api/v1/admin/sucursales', headers=luna).json()[0]['id']
    catalogo = client.get('/api/v1/prendas/catalogo-interno', headers=luna)
    assert catalogo.status_code == 200 and catalogo.json()
    variante = next(v for p in catalogo.json() for v in p['variantes']
                    if any(s['sucursal_id'] == sucursal and s['disponible'] > 1 for s in v['disponibilidad']))
    cliente = client.get('/api/v1/clientes', headers=luna).json()[0]
    nueva = client.post('/api/v1/reservas', headers=luna, json={'sucursal_id': sucursal, 'cliente_id': cliente['id'],
                         'variante_id': variante['id'], 'cantidad': 1})
    assert nueva.status_code == 201, nueva.text
    id = nueva.json()['id']
    reservas = client.get(f'/api/v1/reservas?sucursal_id={sucursal}', headers=luna)
    assert reservas.status_code == 200
    assert next(r for r in reservas.json() if r['id'] == id)['estado'] == 'pendiente'
    assert client.post(f'/api/v1/reservas/{id}/preparar', headers=andina).status_code == 404
    assert client.post(f'/api/v1/reservas/{id}/preparar', headers=luna).json()['estado'] == 'preparada'
    assert client.post(f'/api/v1/reservas/{id}/atender', headers=luna).json()['estado'] == 'atendida'
    assert client.post(f'/api/v1/reservas/{id}/atender', headers=luna).status_code == 409


def test_caja_venta_con_reserva_y_reintento(client, token_luna):
    h = _h(token_luna)
    sucursal = client.get('/api/v1/admin/sucursales', headers=h).json()[0]['id']
    fila = next(x for x in client.get(f'/api/v1/inventario?sucursal_id={sucursal}', headers=h).json() if x['disponible'] >= 2)
    cliente = client.get('/api/v1/clientes', headers=h).json()[0]
    reserva = client.post('/api/v1/reservas', headers=h, json={'sucursal_id': sucursal, 'cliente_id': cliente['id'],
                           'variante_id': fila['variante_id'], 'cantidad': 1}).json()
    assert client.post(f"/api/v1/reservas/{reserva['id']}/preparar", headers=h).status_code == 200
    body = {'sucursal_id': sucursal, 'reserva_id': reserva['id'], 'forma_pago': 'EFECTIVO',
            'monto_recibido': 10000, 'uuid_operacion': 'prueba-venta-reserva',
            'items': [{'variante_id': fila['variante_id'], 'cantidad': 1}]}
    venta = client.post('/api/v1/ventas', headers=h, json=body)
    assert venta.status_code == 201, venta.text
    assert client.post('/api/v1/ventas', headers=h, json=body).json()['id'] == venta.json()['id']
    inv = client.get(f'/api/v1/inventario?sucursal_id={sucursal}', headers=h).json()
    actual = next(x for x in inv if x['id'] == fila['id'])
    assert actual['cantidad'] == fila['cantidad'] - 1 and actual['cantidad_reservada'] == fila['cantidad_reservada']


def test_compra_recibida_actualiza_stock_solo_una_vez(client, token_luna, token_andina):
    luna, andina = _h(token_luna), _h(token_andina)
    sucursal = client.get('/api/v1/admin/sucursales', headers=luna).json()[0]['id']
    proveedor = client.get('/api/v1/admin/proveedores', headers=luna).json()[0]['id']
    fila = client.get(f'/api/v1/inventario?sucursal_id={sucursal}', headers=luna).json()[0]
    assert client.get('/api/v1/oferta?solo_disponibles=false', headers=luna).status_code == 200
    nueva = client.post('/api/v1/compras', headers=luna, json={'proveedor_id': proveedor, 'sucursal_id': sucursal,
                        'detalle': [{'variante_id': fila['variante_id'], 'cantidad': 3, 'precio_unitario': 20}]})
    assert nueva.status_code == 201, nueva.text
    id = nueva.json()['id']
    assert client.get(f'/api/v1/compras/{id}', headers=andina).status_code == 404
    recibida = client.post(f'/api/v1/compras/{id}/recibir', headers=luna)
    assert recibida.status_code == 200 and recibida.json()['compra']['estado'] == 'recibida'
    assert client.post(f'/api/v1/compras/{id}/recibir', headers=luna).status_code == 409
    actual = next(x for x in client.get(f'/api/v1/inventario?sucursal_id={sucursal}', headers=luna).json() if x['id'] == fila['id'])
    assert actual['cantidad'] == fila['cantidad'] + 3


def test_usuario_proveedor_publica_oferta_para_tienda(client, token_luna, token_andina):
    luna, andina = _h(token_luna), _h(token_andina)
    proveedor = client.get('/api/v1/admin/proveedores', headers=luna).json()[0]['id']
    temporada = client.get('/api/v1/admin/temporadas', headers=luna).json()[0]['id']
    nuevo = client.post('/api/v1/usuarios', headers=luna, json={'nombre': 'Proveedor prueba',
                         'email': 'proveedor.prueba@ejemplo.bo', 'password': 'Prueba12345',
                         'roles': ['proveedor'], 'proveedor_id': proveedor})
    assert nuevo.status_code == 201, nuevo.text
    assert nuevo.json()['proveedor_id'] == proveedor
    sesion = client.post('/api/v1/auth/login', json={'codigo_tenant': 'luna',
                         'email': 'proveedor.prueba@ejemplo.bo', 'password': 'Prueba12345'})
    h = _h(sesion.json()['access_token'])
    oferta = client.post('/api/v1/oferta/mia', headers=h, json={'nombre': 'Producto de prueba',
                         'precio_referencial': 15, 'cantidad_minima': 1, 'temporada_ids': [temporada]})
    assert oferta.status_code == 201, oferta.text
    assert any(x['id'] == oferta.json()['id'] for x in client.get('/api/v1/oferta', headers=luna).json())
    assert not any(x['id'] == oferta.json()['id'] for x in client.get('/api/v1/oferta', headers=andina).json())


def test_envio_de_venta_pagada_y_transiciones(client, token_luna, token_andina):
    luna, andina = _h(token_luna), _h(token_andina)
    sucursal = client.get('/api/v1/admin/sucursales', headers=luna).json()[0]['id']
    fila = next(x for x in client.get(f'/api/v1/inventario?sucursal_id={sucursal}', headers=luna).json() if x['disponible'] > 0)
    venta = client.post('/api/v1/ventas', headers=luna, json={'sucursal_id': sucursal, 'forma_pago': 'EFECTIVO',
                         'items': [{'variante_id': fila['variante_id'], 'cantidad': 1}]}).json()
    envio = client.post('/api/v1/envios', headers=luna, json={'codigo_venta': venta['codigo'], 'sucursal_id': sucursal, 'direccion': 'Av. Principal 123',
                        'latitud': -17.78, 'longitud': -63.18})
    assert envio.status_code == 201, envio.text
    id = envio.json()['id']
    assert client.post(f'/api/v1/envios/{id}/asignar', headers=andina, json={'repartidor': 'Persona'}).status_code == 404
    assert client.post(f"/api/v1/ventas/{venta['id']}/anular", headers=luna, json={'motivo': 'Prueba'}).status_code == 409
    assert client.post(f'/api/v1/envios/{id}/entregar', headers=luna, json={}).status_code == 409
    assert client.post(f'/api/v1/envios/{id}/asignar', headers=luna, json={'repartidor': 'Repartidor'}).json()['estado'] == 'asignado'
    assert client.post(f'/api/v1/envios/{id}/en-camino', headers=luna, json={}).json()['estado'] == 'en_camino'
    assert client.post(f'/api/v1/envios/{id}/entregar', headers=luna, json={}).json()['estado'] == 'entregado'
    assert any(e['id'] == id for e in client.get(f'/api/v1/envios?sucursal_id={sucursal}', headers=luna).json())


def test_reportes_suman_ventas_reales_y_respetan_empresa(client, token_luna, token_andina):
    luna, andina = _h(token_luna), _h(token_andina)
    sucursal = client.get('/api/v1/admin/sucursales', headers=luna).json()[0]['id']
    fila = next(x for x in client.get(f'/api/v1/inventario?sucursal_id={sucursal}', headers=luna).json() if x['disponible'] > 0)
    assert client.put(f"/api/v1/prendas/{fila['prenda_id']}", headers=luna, json={'costo': 12}).status_code == 200
    venta = client.post('/api/v1/ventas', headers=luna, json={'sucursal_id': sucursal, 'forma_pago': 'EFECTIVO',
                         'monto_recibido': 10000, 'items': [{'variante_id': fila['variante_id'], 'cantidad': 1}]})
    assert venta.status_code == 201, venta.text
    ventas = client.get('/api/v1/reportes/ventas', headers=luna)
    assert ventas.status_code == 200, ventas.text
    assert any(v['id'] == venta.json()['id'] for v in ventas.json()['ventas'])
    assert not any(v['id'] == venta.json()['id'] for v in client.get('/api/v1/reportes/ventas', headers=andina).json()['ventas'])
    for ruta in ('dashboard', 'inventario', 'margen'):
        r = client.get(f'/api/v1/reportes/{ruta}', headers=luna)
        assert r.status_code == 200, r.text
    margenes = client.get('/api/v1/reportes/margen', headers=luna).json()['prendas']
    assert any(p['prenda_id'] == fila['prenda_id'] and p['costo'] == 12 for p in margenes)
    csv = client.get('/api/v1/reportes/ventas?formato=csv', headers=luna)
    assert csv.status_code == 200 and venta.json()['codigo'] in csv.text
