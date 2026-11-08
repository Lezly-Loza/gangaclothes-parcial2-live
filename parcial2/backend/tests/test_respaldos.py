import copy
import sqlite3
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
