from datetime import datetime, timedelta, timezone


def h(token): return {'Authorization': f'Bearer {token}'}


def test_reporte_generativo_usa_solo_agregados_del_tenant(client, token_luna, token_andina, monkeypatch):
    from app.modules.ventas import analitica
    visto = {}
    monkeypatch.setattr(analitica, '_clave_gemini', lambda: 'clave-de-prueba')
    def modelo(clave, pregunta, datos):
        visto.update(datos)
        return f"Ventas del período: {datos['ventas']['ventas']}"
    monkeypatch.setattr(analitica, '_generar_gemini', modelo)
    r = client.post('/api/v1/reportes/generativo', headers=h(token_luna), json={'pregunta': 'Resume mis ventas'})
    assert r.status_code == 200 and r.json()['modo'] == 'gemini'
    convencional = client.get('/api/v1/reportes/ventas', headers=h(token_luna)).json()
    assert r.json()['datos']['ventas'] == convencional['totales']
    assert 'correo' not in str(visto).lower() and 'documento' not in str(visto).lower()
    andina = client.post('/api/v1/reportes/generativo', headers=h(token_andina), json={'pregunta': 'Resume mis ventas'})
    assert andina.status_code == 200
    assert andina.json()['datos']['ventas']['total'] != r.json()['datos']['ventas']['total']
    assert client.post('/api/v1/reportes/generativo', json={'pregunta': 'Ventas'}).status_code == 401
    otro = client.get('/api/v1/sucursales', headers=h(token_andina)).json()[0]['id']
    assert client.post('/api/v1/reportes/generativo', headers=h(token_luna), json={'pregunta': 'Ventas', 'sucursal_id': otro}).status_code == 404
    monkeypatch.setattr(analitica, '_clave_gemini', lambda: '')
    sin = client.post('/api/v1/reportes/generativo', headers=h(token_luna), json={'pregunta': 'Ventas'})
    assert sin.status_code == 200 and sin.json()['modo'] == 'sin_modelo' and sin.json()['aviso']


def test_prediccion_y_segmentacion_con_historia_y_datos_insuficientes(client, token_luna):
    from app.core.database import SessionLocal
    from app.models import Cliente, Pago, Sucursal, Tenant, Venta
    ahora = datetime.now(timezone.utc)
    with SessionLocal() as db:
        tid = db.query(Tenant).filter_by(codigo='luna').one().id
        sid = db.query(Sucursal).filter_by(tenant_id=tid).first().id
        clientes = db.query(Cliente).filter_by(tenant_id=tid).order_by(Cliente.id).limit(3).all()
        for i in range(20):
            v = Venta(tenant_id=tid, codigo=f'ML-TEST-{i}', sucursal_id=sid, cliente_id=clientes[i % 3].id,
                      forma_pago='EFECTIVO', total=100 + i * 3, estado='CONFIRMADA', fecha=ahora-timedelta(days=i))
            db.add(v); db.flush()
            db.add(Pago(tenant_id=tid, venta_id=v.id, metodo='EFECTIVO', monto=v.total, estado='APROBADO'))
        db.commit()
    r = client.get('/api/v1/reportes/analitica', headers=h(token_luna))
    assert r.status_code == 200, r.text
    assert r.json()['prediccion']['disponible'] and len(r.json()['prediccion']['valores']) == 7
    assert r.json()['segmentos']['disponible'] and sum(g['clientes'] for g in r.json()['segmentos']['grupos']) == 3
    assert 'cliente_id' not in str(r.json()['segmentos'])
    hoy = (ahora - timedelta(hours=4)).date().isoformat()
    insuficiente = client.get(f'/api/v1/reportes/analitica?desde={hoy}&hasta={hoy}', headers=h(token_luna))
    assert insuficiente.status_code == 200 and not insuficiente.json()['prediccion']['disponible']
