import copy
import sqlite3
from datetime import datetime, timedelta, timezone
from app.modules.respaldos.restaurar import restaurar_en_sqlite


def h(token): return {'Authorization': f'Bearer {token}'}


def test_respaldo_aislado_verificable_y_restaurable(client, token_luna, token_andina, tmp_path):
    r = client.get('/api/v1/respaldos/empresa', headers=h(token_luna))
    assert r.status_code == 200, r.text
    respaldo = r.json()
    assert respaldo['empresa']['codigo'] == 'luna'
    assert all(fila['tenant_id'] == respaldo['empresa']['id'] for nombre, filas in respaldo['tablas'].items()
               if nombre not in ('tenants', 'planes') for fila in filas)
    assert client.post('/api/v1/respaldos/verificar', headers=h(token_luna), json=respaldo).status_code == 200
    assert client.post('/api/v1/respaldos/verificar', headers=h(token_andina), json=respaldo).status_code == 404
    alterado = copy.deepcopy(respaldo); alterado['empresa']['codigo'] = 'andina'
    assert client.post('/api/v1/respaldos/verificar', headers=h(token_luna), json=alterado).status_code == 422
    ruta = tmp_path / 'restaurada.db'
    restaurar_en_sqlite(respaldo, ruta)
    with sqlite3.connect(ruta) as db:
        assert db.execute('select codigo from tenants').fetchall() == [('luna',)]
        assert db.execute('select count(*) from users').fetchone()[0] == len(respaldo['tablas']['users'])
        assert db.execute('pragma foreign_key_check').fetchall() == []
    try:
        restaurar_en_sqlite(respaldo, ruta)
        assert False, 'No debe sobrescribir una base existente'
    except FileExistsError:
        pass


def test_programacion_diaria_y_fecha_aisladas_y_recuperacion(client, token_luna, token_andina, tmp_path, monkeypatch):
    from app.core.database import SessionLocal
    from app.models import Tenant
    from app.modules.respaldos import programacion as prog

    monkeypatch.setenv('RESPALDOS_DIRECTORIO', str(tmp_path))
    futuro = datetime.now(timezone.utc).replace(tzinfo=None, microsecond=0) + timedelta(minutes=3)
    cita = futuro.replace(tzinfo=timezone.utc).astimezone(prog.LA_PAZ).isoformat()
    r = client.put('/api/v1/respaldos/programacion', headers=h(token_luna), json={'diario': True, 'hora': '03:15', 'fecha_unica': cita})
    assert r.status_code == 200, r.text
    with SessionLocal() as db:
        tid = db.query(Tenant).filter_by(codigo='luna').one().id
        p = db.get(prog.ProgramaRespaldo, tid)
        p.siguiente_diario = futuro
        db.commit()
    # Simula la vuelta del servidor después de ambas horas programadas.
    prog.ejecutar_pendientes(futuro + timedelta(minutes=2))
    estado = client.get('/api/v1/respaldos/programacion', headers=h(token_luna)).json()
    assert estado['fecha_unica'] is None and estado['ultimo'] and len(estado['copias']) == 2
    for copia in estado['copias']:
        url = '/api/v1/respaldos/programados/' + copia['nombre']
        r = client.get(url, headers=h(token_luna))
        assert r.status_code == 200 and r.json()['empresa']['codigo'] == 'luna'
        assert client.post('/api/v1/respaldos/verificar', headers=h(token_luna), json=r.json()).status_code == 200
        assert client.get(url, headers=h(token_andina)).status_code == 404
    prog.ejecutar_pendientes(futuro + timedelta(minutes=3))
    assert len(client.get('/api/v1/respaldos/programacion', headers=h(token_luna)).json()['copias']) == 2
    assert client.put('/api/v1/respaldos/programacion', headers=h(token_luna), json={'diario': True, 'hora': '29:00'}).status_code == 422
    assert client.put('/api/v1/respaldos/programacion', headers=h(token_luna), json={'diario': True, 'hora': '02:00', 'fecha_unica': '2000-01-01T10:00'}).status_code == 422
    assert client.get('/api/v1/respaldos/programacion').status_code == 401
