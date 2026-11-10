"""Contrato de pagos compartido por web y móvil, sin llamar a proveedores externos."""
import io
import json

from app.modules.pasarela import qr_bcp, stripe_gw
from app.modules.ia import router as ia_router


def _cliente_y_carrito(client):
    acceso = client.post('/api/v1/auth/login', json={
        'codigo_tenant': 'luna', 'email': 'cliente@boutique-luna.bo', 'password': 'Luna12345'})
    assert acceso.status_code == 200, acceso.text
    headers = {'Authorization': f"Bearer {acceso.json()['access_token']}"}
    opciones = client.get('/api/v1/catalogo/opciones', headers=headers).json()
    for sucursal in opciones['sucursales']:
        sid = sucursal['id']
        catalogo = client.get(f'/api/v1/catalogo?sucursal_id={sid}', headers=headers).json()
        for producto in catalogo:
            for variante in producto['variantes']:
                if any(s['sucursal_id'] == sid and s['disponible'] >= 2 for s in variante['disponibilidad']):
                    assert client.post('/api/v1/tienda/carrito', headers=headers,
                        json={'sucursal_id': sid}).status_code == 200
                    respuesta = client.post('/api/v1/tienda/carrito/items', headers=headers,
                        json={'variante_id': variante['id'], 'cantidad': 1})
                    assert respuesta.status_code == 200, respuesta.text
                    return headers, sid, variante['id']
    raise AssertionError('La semilla no tiene ninguna variante con stock')


def test_tarjeta_aprobada_y_rechazada(client, monkeypatch):
    monkeypatch.setattr(stripe_gw.settings, 'stripe_secret_key', '')
    headers, _, _ = _cliente_y_carrito(client)
    invalida = client.post('/api/v1/pagos/tarjeta', headers=headers,
        json={'numero_tarjeta': '1234567890123456'})
    assert invalida.status_code == 402
    assert client.get('/api/v1/tienda/carrito', headers=headers).json()['unidades'] == 1
    rechazada = client.post('/api/v1/pagos/tarjeta', headers=headers,
        json={'numero_tarjeta': '4000 0000 0000 0002'})
    assert rechazada.status_code == 402
    assert client.get('/api/v1/tienda/carrito', headers=headers).json()['unidades'] == 1
    aprobada = client.post('/api/v1/pagos/tarjeta', headers=headers,
        json={'numero_tarjeta': '4242 4242 4242 4242'})
    assert aprobada.status_code == 200, aprobada.text
    assert aprobada.json()['referencia'].startswith('pi_sim_')
    assert client.get('/api/v1/tienda/carrito', headers=headers).json() is None
    compras = client.get('/api/v1/tienda/compras', headers=headers).json()
    assert compras[0]['nro_comprobante'] == aprobada.json()['codigo']
    assert compras[0]['pagos'][0]['metodo'] == 'TARJETA'


def test_qr_pendiente_confirmado_e_idempotente(client, monkeypatch):
    monkeypatch.setattr(qr_bcp.settings, 'bcp_modo', 'simulado')
    monkeypatch.setattr(qr_bcp.settings, 'bcp_simulador_segundos', 0)
    headers, sid, vid = _cliente_y_carrito(client)
    creado = client.post('/api/v1/pagos/qr', headers=headers, json={})
    assert creado.status_code == 200, creado.text
    qr_id = creado.json()['qr_id']
    assert creado.json()['estado'] == 'C' and creado.json()['imagen_base64']
    assert client.get(f'/api/v1/pagos/qr/{qr_id}', headers=headers).json()['pendiente'] is True
    assert client.get('/api/v1/tienda/carrito', headers=headers).json()['unidades'] == 1
    confirmado = client.post('/api/v1/pagos/qr/simular', headers=headers,
        json={'qr_id': qr_id, 'estado': 'P'})
    assert confirmado.status_code == 200, confirmado.text
    assert confirmado.json()['aprobado'] is True
    assert client.get('/api/v1/tienda/carrito', headers=headers).json() is None
    repetido = client.get(f'/api/v1/pagos/qr/{qr_id}', headers=headers)
    assert repetido.status_code == 200 and repetido.json()['aprobado'] is True
    assert client.get('/api/v1/tienda/compras', headers=headers).json()[0]['pagos'][0]['metodo'] == 'QR'


def test_qr_vencido_devuelve_el_carrito(client, monkeypatch):
    monkeypatch.setattr(qr_bcp.settings, 'bcp_modo', 'simulado')
    monkeypatch.setattr(qr_bcp.settings, 'bcp_simulador_segundos', 0)
    headers, _, _ = _cliente_y_carrito(client)
    creado = client.post('/api/v1/pagos/qr', headers=headers, json={})
    qr_id = creado.json()['qr_id']
    vencido = client.post('/api/v1/pagos/qr/simular', headers=headers,
        json={'qr_id': qr_id, 'estado': 'V'})
    assert vencido.status_code == 200 and vencido.json()['rechazado'] is True
    assert client.get('/api/v1/tienda/carrito', headers=headers).json()['unidades'] == 1


def test_chat_admin_usa_indicadores_y_restringe_clientes(client, monkeypatch):
    monkeypatch.setattr(ia_router, '_clave_gemini', lambda: '')
    admin = client.post('/api/v1/auth/login', json={
        'codigo_tenant': 'luna', 'email': 'ana@boutique-luna.bo', 'password': 'Luna12345'})
    headers_admin = {'Authorization': f"Bearer {admin.json()['access_token']}"}
    respuesta = client.post('/api/v1/ia/chat', headers=headers_admin,
        json={'mensaje': 'Resume las ventas', 'origen': 'admin'})
    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.json()['modo'] == 'sin_modelo'
    assert 'ventas_confirmadas' in respuesta.json()['datos']
    cliente = client.post('/api/v1/auth/login', json={
        'codigo_tenant': 'luna', 'email': 'cliente@boutique-luna.bo', 'password': 'Luna12345'})
    headers_cliente = {'Authorization': f"Bearer {cliente.json()['access_token']}"}
    assert client.post('/api/v1/ia/chat', headers=headers_cliente,
        json={'mensaje': 'Resume las ventas', 'origen': 'admin'}).status_code == 403


def test_chat_admin_prepara_consulta_gemini_sin_enviar_datos(client, monkeypatch):
    enviados = []
    monkeypatch.setattr(ia_router, '_clave_gemini', lambda: 'clave-ficticia')
    monkeypatch.setattr(ia_router, '_modelos_gemini', lambda: ['modelo-ficticio'])

    def responder(req, timeout):
        enviados.append(json.loads(req.data))
        return io.BytesIO(json.dumps({'candidates': [{'content': {
            'parts': [{'text': 'Hay ventas confirmadas y stock bajo.'}]}}]}).encode())

    monkeypatch.setattr(ia_router.urllib.request, 'urlopen', responder)
    admin = client.post('/api/v1/auth/login', json={
        'codigo_tenant': 'luna', 'email': 'ana@boutique-luna.bo', 'password': 'Luna12345'})
    headers = {'Authorization': f"Bearer {admin.json()['access_token']}"}
    respuesta = client.post('/api/v1/ia/chat', headers=headers,
        json={'mensaje': 'Resume las ventas', 'origen': 'admin'})
    assert respuesta.status_code == 200 and respuesta.json()['modo'] == 'gemini'
    assert len(enviados) == 1
    assert 'ventas_confirmadas' in enviados[0]['contents'][0]['parts'][0]['text']
