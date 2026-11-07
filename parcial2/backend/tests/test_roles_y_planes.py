def _h(token):
    return {"Authorization": f"Bearer {token}"}


def test_crear_usuario_sin_rol_y_asignar_permiso_por_tenant(client, token_luna, token_andina):
    luna, andina = _h(token_luna), _h(token_andina)
    inicial = client.get('/api/v1/seguridad/roles', headers=luna)
    assert inicial.status_code == 200
    assert {'administrador', 'encargado', 'vendedor', 'cliente'} <= {r['nombre'] for r in inicial.json()}

    creado = client.post('/api/v1/usuarios', headers=luna, json={
        'nombre': 'Usuario sin rol', 'email': 'sinrol@ejemplo.bo',
        'password': 'Prueba123!', 'roles': [], 'telefono': '70000001',
    })
    assert creado.status_code == 201, creado.text
    usuario = creado.json()
    assert usuario['roles'] == []
    assert usuario['telefono'] == '70000001'

    rol = client.post('/api/v1/seguridad/roles', headers=luna,
                      json={'nombre': 'Supervisor', 'permisos': ['usuarios:ver']})
    assert rol.status_code == 201, rol.text
    rol = rol.json()
    assert rol['nombre'] == 'supervisor'
    assert client.put(f"/api/v1/seguridad/roles/{rol['id']}", headers=andina,
                      json={'permisos': []}).status_code == 404
    assert client.post('/api/v1/seguridad/roles', headers=andina,
                       json={'nombre': 'supervisor', 'permisos': []}).status_code == 201

    asignacion = client.put(f"/api/v1/usuarios/{usuario['id']}", headers=luna,
                            json={'roles': ['supervisor']})
    assert asignacion.status_code == 200, asignacion.text
    assert asignacion.json()['roles'] == ['supervisor']

    login = client.post('/api/v1/auth/login', json={'codigo_tenant': 'luna',
                        'email': 'sinrol@ejemplo.bo', 'password': 'Prueba123!'})
    assert login.status_code == 200, login.text
    supervisor = _h(login.json()['access_token'])
    assert 'usuarios:ver' in login.json()['permisos']
    assert client.get('/api/v1/usuarios', headers=supervisor).status_code == 200
    assert client.post('/api/v1/usuarios', headers=supervisor, json={
        'nombre': 'No autorizado', 'email': 'no@ejemplo.bo', 'password': 'Prueba123!',
    }).status_code == 403
    assert client.put(f"/api/v1/seguridad/roles/{rol['id']}", headers=luna,
                      json={'permisos': []}).status_code == 200
    assert client.get('/api/v1/usuarios', headers=supervisor).status_code == 403


def test_ultimo_administrador_y_usuario_de_otra_empresa(client, token_luna, token_andina):
    luna = _h(token_luna)
    usuarios = client.get('/api/v1/usuarios', headers=luna).json()
    ana = next(u for u in usuarios if u['email'] == 'ana@boutique-luna.bo')
    assert client.put(f"/api/v1/usuarios/{ana['id']}", headers=luna, json={'roles': []}).status_code == 409
    assert client.put(f"/api/v1/usuarios/{ana['id']}", headers=_h(token_andina),
                      json={'nombre': 'Cambio ajeno'}).status_code == 404


def test_superadmin_configura_precio_y_empresa_no_puede(client, token_super, token_luna):
    super_headers, tenant_headers = _h(token_super), _h(token_luna)
    planes = client.get('/api/v1/planes', headers=super_headers)
    assert planes.status_code == 200
    plan = next(p for p in planes.json() if p['codigo'] == 'profesional')
    ruta = f"/api/v1/planes/{plan['id']}"
    assert client.patch(ruta, headers=tenant_headers, json={'precio_mensual': 55}).status_code == 403
    actualizacion = client.patch(ruta, headers=super_headers, json={'precio_mensual': 55})
    assert actualizacion.status_code == 200, actualizacion.text
    assert float(actualizacion.json()['precio_mensual']) == 55
