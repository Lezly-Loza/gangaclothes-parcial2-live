# -*- coding: utf-8 -*-
import os

OUTPUT_DIR = r"c:\Users\user\GangaClothes\parcial2\docs\uml-jaime"
os.makedirs(OUTPUT_DIR, exist_ok=True)

DEFS = """<defs>
<linearGradient id="gOval" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#DCEBFA"/><stop offset="1" stop-color="#AECDEC"/></linearGradient>
<linearGradient id="gPkgHdr" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#F6DFBB"/><stop offset="1" stop-color="#EFCF9F"/></linearGradient>
<linearGradient id="gPkgBody" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#FDF2E1"/><stop offset="1" stop-color="#F7E0BC"/></linearGradient>
<linearGradient id="gCmp" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#FBE4E1"/><stop offset="1" stop-color="#F3CBC5"/></linearGradient>
<linearGradient id="gIfc" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#EDF2F9"/><stop offset="1" stop-color="#D8E2EF"/></linearGradient>
<linearGradient id="gDb" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#E9F4E5"/><stop offset="1" stop-color="#CFE6C8"/></linearGradient>
<linearGradient id="gTeal" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#EAFBFA"/><stop offset="1" stop-color="#8AD9D3"/></linearGradient>
<linearGradient id="gTealBox" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#E4F6F4"/><stop offset="1" stop-color="#BCE5E0"/></linearGradient>
<linearGradient id="gCls" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#FEFAEC"/><stop offset="1" stop-color="#F7EBC9"/></linearGradient>
<linearGradient id="gNode" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#F5F8FD"/><stop offset="1" stop-color="#DCE5F2"/></linearGradient>
<marker id="arrOpen" markerWidth="12" markerHeight="10" refX="10" refY="5" orient="auto"><path d="M1,1 L10,5 L1,9" fill="none" stroke="#7A6A50" stroke-width="1.2"/></marker>
<marker id="arrSolid" markerWidth="11" markerHeight="9" refX="9" refY="4.5" orient="auto"><path d="M0,0 L10,4.5 L0,9 Z" fill="#3A3A3A"/></marker>
<marker id="arrRet" markerWidth="12" markerHeight="10" refX="10" refY="5" orient="auto"><path d="M1,1 L10,5 L1,9" fill="none" stroke="#5A5A5A" stroke-width="1.2"/></marker>
<marker id="mComp" markerWidth="18" markerHeight="10" refX="1" refY="5" orient="auto"><path d="M1,5 L9,1 L17,5 L9,9 Z" fill="#555555" stroke="#555555"/></marker>
<marker id="mAgr" markerWidth="18" markerHeight="10" refX="1" refY="5" orient="auto"><path d="M1,5 L9,1 L17,5 L9,9 Z" fill="#FFFFFF" stroke="#555555"/></marker>
<marker id="mHer" markerWidth="14" markerHeight="14" refX="13" refY="7" orient="auto"><path d="M1,1 L13,7 L1,13 Z" fill="#FFFFFF" stroke="#555555" stroke-width="1.1"/></marker>
</defs>"""

def render_actor(cx, cy, label):
    return f"""<circle cx="{cx}" cy="{cy-38}" r="8" fill="#FDF3CF" stroke="#5A748F" stroke-width="1.4"/>
<line x1="{cx}" y1="{cy-30}" x2="{cx}" y2="{cy-8}" stroke="#5A748F" stroke-width="1.4"/>
<line x1="{cx-13}" y1="{cy-23}" x2="{cx+13}" y2="{cy-23}" stroke="#5A748F" stroke-width="1.4"/>
<line x1="{cx}" y1="{cy-8}" x2="{cx-11}" y2="{cy+8}" stroke="#5A748F" stroke-width="1.4"/>
<line x1="{cx}" y1="{cy-8}" x2="{cx+11}" y2="{cy+8}" stroke="#5A748F" stroke-width="1.4"/>
<text x="{cx}" y="{cy+22}" text-anchor="middle" font-family="Segoe UI, Arial, sans-serif" font-size="11.5" font-weight="bold" font-style="italic" fill="#2B2B2B">{label}</text>"""

def render_box_participant(cx, label1, label2, label3=""):
    x = cx - 66.0
    w = 132.0
    h = 53.5
    y = 46.0
    lines_svg = []
    if label3:
        lines_svg.append(f'<text x="{cx}" y="60.0" text-anchor="middle" font-family="Segoe UI, Arial, sans-serif" font-size="9.6" fill="#20403D">{label1}</text>')
        lines_svg.append(f'<text x="{cx}" y="72.5" text-anchor="middle" font-family="Segoe UI, Arial, sans-serif" font-size="9.6" fill="#20403D">{label2}</text>')
        lines_svg.append(f'<text x="{cx}" y="85.0" text-anchor="middle" font-family="Segoe UI, Arial, sans-serif" font-size="9.6" fill="#20403D">{label3}</text>')
    else:
        lines_svg.append(f'<text x="{cx}" y="66.2" text-anchor="middle" font-family="Segoe UI, Arial, sans-serif" font-size="9.6" fill="#20403D">{label1}</text>')
        lines_svg.append(f'<text x="{cx}" y="78.8" text-anchor="middle" font-family="Segoe UI, Arial, sans-serif" font-size="9.6" fill="#20403D">{label2}</text>')

    return f"""<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="url(#gTealBox)" stroke="#7A9B98" stroke-width="1.2"/>
""" + "\n".join(lines_svg)

def make_sequence_svg(filename, title, actor_name, ui_labels, client_labels, router_labels, service_labels, db_labels, events, alt_blocks=None):
    # X coordinates
    p_x = [78.0, 232.4, 386.8, 541.2, 695.6, 850.0]
    
    # Calculate height based on number of events
    max_y = 120 + len(events) * 36 + 80
    height = max(860, max_y)
    
    svg = [f'<svg xmlns="http://www.w3.org/2000/svg" width="960" height="{height}" viewBox="0 0 960 {height}" font-family="Segoe UI, Arial, sans-serif">']
    svg.append(DEFS)
    # Background and frame
    svg.append(f'<rect width="100%" height="100%" fill="#FFFFFF"/><rect x="1" y="1" width="958" height="{height-2}" fill="#FFFFFF" stroke="#8C8C8C" stroke-width="1.2"/>')
    svg.append(f'<path d="M1,1 L440,1 L440,19 L431,27 L1,27 Z" fill="#FFFFFF" stroke="#8C8C8C" stroke-width="1.2"/>')
    svg.append(f'<text x="9.0" y="19.0" text-anchor="start" font-family="Segoe UI, Arial, sans-serif" font-size="12.5" font-weight="bold" font-style="italic" fill="#1A1A1A">sd {title}</text>')
    
    # Lifelines
    for idx, x in enumerate(p_x):
        top_y = 104 if idx == 0 else 99.5
        svg.append(f'<line x1="{x}" y1="{top_y}" x2="{x}" y2="{height-28}" stroke="#9A9A9A" stroke-width="1" stroke-dasharray="4,4"/>')

    # Activations
    # Default activations on lifelines 1, 2, 3, 4, 5
    svg.append(f'<rect x="{p_x[1]-5}" y="114.0" width="10" height="{height-160}" fill="#F6F1DE" stroke="#8C8C8C" stroke-width="1"/>')
    svg.append(f'<rect x="{p_x[2]-5}" y="148.0" width="10" height="{height-210}" fill="#F6F1DE" stroke="#8C8C8C" stroke-width="1"/>')
    svg.append(f'<rect x="{p_x[3]-5}" y="182.0" width="10" height="{height-260}" fill="#F6F1DE" stroke="#8C8C8C" stroke-width="1"/>')
    svg.append(f'<rect x="{p_x[4]-5}" y="216.0" width="10" height="{height-310}" fill="#F6F1DE" stroke="#8C8C8C" stroke-width="1"/>')
    svg.append(f'<rect x="{p_x[5]-5}" y="250.0" width="10" height="{height-360}" fill="#F6F1DE" stroke="#8C8C8C" stroke-width="1"/>')

    # Alt blocks if any
    if alt_blocks:
        for ab in alt_blocks:
            ay, ah, cond_true, cond_false, split_y = ab
            svg.append(f'<rect x="470.0" y="{ay}" width="460.0" height="{ah}" fill="none" stroke="#8C8C8C" stroke-width="1.2"/>')
            svg.append(f'<path d="M470.0,{ay} L512.0,{ay} L512.0,{ay+13} L504.0,{ay+19} L470.0,{ay+19} Z" fill="#EDEDED" stroke="#8C8C8C" stroke-width="1"/>')
            svg.append(f'<text x="477.0" y="{ay+14}" text-anchor="start" font-family="Segoe UI, Arial, sans-serif" font-size="10" font-weight="bold" fill="#333333">alt</text>')
            svg.append(f'<text x="522.0" y="{ay+14}" text-anchor="start" font-family="Segoe UI, Arial, sans-serif" font-size="10" font-style="italic" fill="#333333">[{cond_true}]</text>')
            if split_y:
                svg.append(f'<line x1="470.0" y1="{split_y}" x2="930.0" y2="{split_y}" stroke="#8C8C8C" stroke-width="1" stroke-dasharray="5,4"/>')
                svg.append(f'<text x="478.0" y="{split_y+13}" text-anchor="start" font-family="Segoe UI, Arial, sans-serif" font-size="10" font-style="italic" fill="#333333">[{cond_false}]</text>')

    # Events / Messages
    cur_y = 128.0
    for ev in events:
        from_idx, to_idx, text, is_ret, is_self = ev
        x1 = p_x[from_idx]
        x2 = p_x[to_idx]

        if is_self:
            # Self call on service
            svg.append(f'<path d="M{x1+5},{cur_y-6} L{x1+40},{cur_y-6} L{x1+40},{cur_y+8} L{x1+10},{cur_y+8}" fill="none" stroke="#3A3A3A" stroke-width="1.2" marker-end="url(#arrSolid)"/>')
            svg.append(f'<text x="{x1+48}" y="{cur_y-1}" text-anchor="start" font-family="Segoe UI, Arial, sans-serif" font-size="10" font-style="italic" fill="#1A1A1A">{text}</text>')
        elif is_ret:
            svg.append(f'<line x1="{x1}" y1="{cur_y}" x2="{x2}" y2="{cur_y}" stroke="#5A5A5A" stroke-width="1.2" stroke-dasharray="5,4" marker-end="url(#arrRet)"/>')
            tx = min(x1, x2) + 10.0
            svg.append(f'<text x="{tx}" y="{cur_y-5}" text-anchor="start" font-family="Segoe UI, Arial, sans-serif" font-size="10" font-style="italic" fill="#1A1A1A">{text}</text>')
        else:
            svg.append(f'<line x1="{x1}" y1="{cur_y}" x2="{x2}" y2="{cur_y}" stroke="#3A3A3A" stroke-width="1.2" marker-end="url(#arrSolid)"/>')
            tx = min(x1, x2) + 10.0
            svg.append(f'<text x="{tx}" y="{cur_y-5}" text-anchor="start" font-family="Segoe UI, Arial, sans-serif" font-size="10" font-style="italic" fill="#1A1A1A">{text}</text>')
        cur_y += 34.0

    # Participants Header at top
    svg.append(render_actor(p_x[0], 78, actor_name))
    svg.append(render_box_participant(p_x[1], ui_labels[0], ui_labels[1], ui_labels[2] if len(ui_labels)>2 else ""))
    svg.append(render_box_participant(p_x[2], client_labels[0], client_labels[1]))
    svg.append(render_box_participant(p_x[3], router_labels[0], router_labels[1]))
    svg.append(render_box_participant(p_x[4], service_labels[0], service_labels[1], service_labels[2] if len(service_labels)>2 else ""))
    svg.append(render_box_participant(p_x[5], db_labels[0], db_labels[1], db_labels[2] if len(db_labels)>2 else ""))

    svg.append("</svg>")
    
    filepath = os.path.join(OUTPUT_DIR, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write("\n".join(svg))
    print(f"Generated {filename}")

def make_communication_svg(filename, title, actor_name, ui_name, ctrl_name, entity_name, messages):
    width = 940
    height = 270
    
    svg = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" font-family="Segoe UI, Arial, sans-serif">']
    svg.append(DEFS)
    svg.append(f'<rect width="100%" height="100%" fill="#FFFFFF"/><rect x="1" y="1" width="{width-2}" height="{height-2}" fill="#FFFFFF" stroke="#8C8C8C" stroke-width="1.2"/>')
    svg.append(f'<path d="M1,1 L340,1 L340,19 L331,27 L1,27 Z" fill="#FFFFFF" stroke="#8C8C8C" stroke-width="1.2"/>')
    svg.append(f'<text x="9.0" y="19.0" text-anchor="start" font-family="Segoe UI, Arial, sans-serif" font-size="12.5" font-weight="bold" font-style="italic" fill="#1A1A1A">sd {title}</text>')

    # Coordinates
    act_x, act_y = 95, 130
    ui_x, ui_y = 320, 130
    ctrl_x, ctrl_y = 565, 130
    ent_x, ent_y = 810, 130

    # Connecting horizontal lines
    svg.append(f'<line x1="{act_x+14}" y1="{act_y}" x2="{ui_x-58}" y2="{ui_y}" stroke="#7A7A7A" stroke-width="1.2"/>')
    svg.append(f'<line x1="{ui_x+24}" y1="{ui_y}" x2="{ctrl_x-24}" y2="{ctrl_y}" stroke="#7A7A7A" stroke-width="1.2"/>')
    svg.append(f'<line x1="{ctrl_x+24}" y1="{ctrl_y}" x2="{ent_x-24}" y2="{ent_y}" stroke="#7A7A7A" stroke-width="1.2"/>')

    # Actor
    svg.append(f'<circle cx="{act_x}" cy="{act_y-52}" r="8" fill="#FDF3CF" stroke="#5A748F" stroke-width="1.4"/>')
    svg.append(f'<line x1="{act_x}" y1="{act_y-44}" x2="{act_x}" y2="{act_y-22}" stroke="#5A748F" stroke-width="1.4"/>')
    svg.append(f'<line x1="{act_x-13}" y1="{act_y-37}" x2="{act_x+13}" y2="{act_y-37}" stroke="#5A748F" stroke-width="1.4"/>')
    svg.append(f'<line x1="{act_x}" y1="{act_y-22}" x2="{act_x-11}" y2="{act_y-6}" stroke="#5A748F" stroke-width="1.4"/>')
    svg.append(f'<line x1="{act_x}" y1="{act_y-22}" x2="{act_x+11}" y2="{act_y-6}" stroke="#5A748F" stroke-width="1.4"/>')
    svg.append(f'<text x="{act_x}" y="{act_y+8}" text-anchor="middle" font-family="Segoe UI, Arial, sans-serif" font-size="11.5" font-weight="bold" font-style="italic" fill="#2B2B2B">{actor_name}</text>')

    # Boundary (UI)
    svg.append(f'<line x1="{ui_x-40}" y1="{ui_y-14}" x2="{ui_x-40}" y2="{ui_y+14}" stroke="#4E7A76" stroke-width="1.6"/>')
    svg.append(f'<line x1="{ui_x-40}" y1="{ui_y}" x2="{ui_x-24}" y2="{ui_y}" stroke="#4E7A76" stroke-width="1.6"/>')
    svg.append(f'<circle cx="{ui_x}" cy="{ui_y}" r="24" fill="url(#gTeal)" stroke="#4E7A76" stroke-width="1.5"/>')
    svg.append(f'<text x="{ui_x}" y="{ui_y+42}" text-anchor="middle" font-family="Segoe UI, Arial, sans-serif" font-size="11.5" font-weight="bold" font-style="italic" fill="#2B2B2B">{ui_name}</text>')

    # Control
    svg.append(f'<circle cx="{ctrl_x}" cy="{ctrl_y}" r="24" fill="url(#gTeal)" stroke="#4E7A76" stroke-width="1.5"/>')
    svg.append(f'<path d="M{ctrl_x-9},{ctrl_y-30} L{ctrl_x+3},{ctrl_y-22} M{ctrl_x-9},{ctrl_y-30} L{ctrl_x+1},{ctrl_y-35}" fill="none" stroke="#4E7A76" stroke-width="1.6"/>')
    svg.append(f'<text x="{ctrl_x}" y="{ctrl_y+42}" text-anchor="middle" font-family="Segoe UI, Arial, sans-serif" font-size="11.5" font-weight="bold" font-style="italic" fill="#2B2B2B">{ctrl_name}</text>')

    # Entity
    svg.append(f'<circle cx="{ent_x}" cy="{ent_y}" r="24" fill="url(#gTeal)" stroke="#4E7A76" stroke-width="1.5"/>')
    svg.append(f'<line x1="{ent_x-24}" y1="{ent_y+27}" x2="{ent_x+24}" y2="{ent_y+27}" stroke="#4E7A76" stroke-width="1.6"/>')
    svg.append(f'<text x="{ent_x}" y="{ent_y+45}" text-anchor="middle" font-family="Segoe UI, Arial, sans-serif" font-size="11.5" font-weight="bold" font-style="italic" fill="#2B2B2B">{entity_name}</text>')

    # Messages
    # msg format: (from_x, to_x, y, text, direction) where direction is 'right' or 'left'
    for m in messages:
        mx, my, mtext, mdir = m
        svg.append(f'<text x="{mx}" y="{my}" text-anchor="start" font-family="Segoe UI, Arial, sans-serif" font-size="10.5" font-style="italic" fill="#1A1A1A">{mtext}</text>')
        # Arrow icon
        if mdir == 'right':
            svg.append(f'<line x1="{mx+len(mtext)*5.8 + 8}" y1="{my-4}" x2="{mx+len(mtext)*5.8 + 28}" y2="{my-4}" stroke="#1A1A1A" stroke-width="1.6" marker-end="url(#arrSolid)"/>')
        else:
            svg.append(f'<line x1="{mx+len(mtext)*5.8 + 28}" y1="{my-4}" x2="{mx+len(mtext)*5.8 + 8}" y2="{my-4}" stroke="#1A1A1A" stroke-width="1.6" marker-end="url(#arrSolid)"/>')

    svg.append("</svg>")
    
    filepath = os.path.join(OUTPUT_DIR, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write("\n".join(svg))
    print(f"Generated {filename}")

# =========================================================================
# 1. CU-08: Gestión de Productos y Variantes
# =========================================================================
make_sequence_svg(
    filename="CU-08_secuencia.svg",
    title="CU-08: Gestión de Productos y Variantes (Web)",
    actor_name="Encargado / Admin",
    ui_labels=["UI: ProductosList +", "ProductoForm", ": Web App"],
    client_labels=["S: productos.service", ": HttpClient"],
    router_labels=["R: /api/v1/productos", ": FastAPI Router"],
    service_labels=["SV: productos/service.py", ": service.py"],
    db_labels=["BD: productos, variantes,", "suscripciones", ": PostgreSQL multitenant"],
    events=[
        (0, 1, "1: abrir Productos y Variantes", False, False),
        (1, 2, "2: listar_productos()", False, False),
        (2, 3, "3: GET /api/v1/productos", False, False),
        (3, 4, "4: listar_productos(tenant_id)", False, False),
        (4, 5, "5: SELECT Producto WHERE tenant_id = scope.tenant_id", False, False),
        (5, 4, "6: list[Producto]", True, False),
        (4, 3, "7: 200 OK · List[ProductoOut]", True, False),
        (3, 2, "8: productos", True, False),
        (2, 1, "9: muestra prendas y stock", True, False),
        (0, 1, "10: guardarProducto(nombre, cat_id, precio, costo)", False, False),
        (1, 2, "11: crear_producto(dto)", False, False),
        (2, 3, "12: POST /api/v1/productos", False, False),
        (3, 4, "13: crear_producto(data, tenant_id)", False, False),
        (4, 4, "14: verificar_cupo_productos(tenant_id)", False, True),
        (4, 5, "15: SELECT COUNT(*) FROM Producto WHERE tenant_id=?", False, False),
        (5, 4, "16: total_actual", True, False),
        (4, 5, "17: INSERT Producto (tenant_id, nombre, cat_id, precio...)", False, False),
        (4, 5, "18: INSERT Variante (tenant_id, producto_id, sku, talla, color)", False, False),
        (4, 3, "19: Producto y variantes creados", True, False),
        (4, 3, "20: 400 BAD REQUEST 'Límite de productos alcanzado para su plan'", True, False),
        (3, 2, "21: 201 Created · ProductoOut", True, False),
        (2, 1, "22: producto guardado", True, False),
        (1, 0, "23: catálogo actualizado con variantes", True, False)
    ],
    alt_blocks=[
        (560.0, 185.0, "total_actual < limite_productos", "else: límite superado", 670.0)
    ]
)

make_communication_svg(
    filename="CU-08_comunicacion.svg",
    title="CU-08: Gestión de Productos y Variantes",
    actor_name="EncargadoTienda",
    ui_name="ProductosUI",
    ctrl_name="ProductoCtr",
    entity_name="Producto",
    messages=[
        (135.0, 78.0, "1: abrirCatalogo()", "right"),
        (135.0, 96.0, "1.1: nuevoProducto(datos, variantes)", "right"),
        (345.0, 96.0, "1.2: crear_producto(data)", "right"),
        (590.0, 96.0, "1.3: verificarCupo() e insertar()", "right"),
        (610.0, 172.0, "1.4: productoRegistrado()", "left"),
        (350.0, 200.0, "1.5: catalogoActualizado()", "left")
    ]
)

# =========================================================================
# 2. CU-09: Catálogos Base (Categorías, Tallas, Colores, Temporadas)
# =========================================================================
make_sequence_svg(
    filename="CU-09_secuencia.svg",
    title="CU-09: Catálogos Base de Atributos de Ropa (Web)",
    actor_name="Encargado / Admin",
    ui_labels=["UI: CatalogosTabs +", "ElementoForm", ": Web App"],
    client_labels=["S: catalogos.service", ": HttpClient"],
    router_labels=["R: /api/v1/catalogos", ": FastAPI Router"],
    service_labels=["SV: catalogos/service.py", ": service.py"],
    db_labels=["BD: categorias, tallas,", "colores, temporadas", ": PostgreSQL multitenant"],
    events=[
        (0, 1, "1: seleccionar Pestaña (ej: Tallas)", False, False),
        (1, 2, "2: listar_catalogo('tallas')", False, False),
        (2, 3, "3: GET /api/v1/catalogos/tallas", False, False),
        (3, 4, "4: listar_tallas(tenant_id)", False, False),
        (4, 5, "5: SELECT Talla WHERE tenant_id = scope.tenant_id", False, False),
        (5, 4, "6: list[Talla]", True, False),
        (4, 3, "7: 200 OK · List[TallaOut]", True, False),
        (3, 2, "8: tallas", True, False),
        (2, 1, "9: muestra cuadrícula de tallas activas", True, False),
        (0, 1, "10: agregarElemento(tipo='colores', nombre='Azul Marino', hex='#000080')", False, False),
        (1, 2, "11: crear_elemento(tipo, dto)", False, False),
        (2, 3, "12: POST /api/v1/catalogos/colores", False, False),
        (3, 4, "13: crear_color(data, tenant_id)", False, False),
        (4, 5, "14: SELECT Color WHERE tenant_id=? AND nombre=?", False, False),
        (5, 4, "15: existe?", True, False),
        (4, 5, "16: INSERT Color (tenant_id, nombre, codigo_hex, activo)", False, False),
        (4, 3, "17: Color registrado", True, False),
        (4, 3, "18: 409 CONFLICT 'Ya existe un color con este nombre'", True, False),
        (3, 2, "19: 201 Created · ColorOut", True, False),
        (2, 1, "20: elemento creado", True, False),
        (1, 0, "21: pestaña actualizada", True, False)
    ],
    alt_blocks=[
        (560.0, 155.0, "nombre no existe en tenant", "else: duplicado", 635.0)
    ]
)

make_communication_svg(
    filename="CU-09_comunicacion.svg",
    title="CU-09: Catálogos Base de Atributos",
    actor_name="Administrador",
    ui_name="CatalogosUI",
    ctrl_name="CatalogoCtr",
    entity_name="CatalogoBase",
    messages=[
        (135.0, 78.0, "1: verCatalogos(tipo)", "right"),
        (135.0, 96.0, "1.1: nuevoElemento(tipo, nombre, extras)", "right"),
        (345.0, 96.0, "1.2: crear_item(tipo, data)", "right"),
        (590.0, 96.0, "1.3: validarUnicidad() e insertar()", "right"),
        (610.0, 172.0, "1.4: itemCreado()", "left"),
        (350.0, 200.0, "1.5: listaActualizada()", "left")
    ]
)

# =========================================================================
# 3. CU-03: Administrar Usuarios y Roles del Personal
# =========================================================================
make_sequence_svg(
    filename="CU-03_secuencia.svg",
    title="CU-03: Administrar Usuarios y Roles del Personal (Web)",
    actor_name="Administrador Tenant",
    ui_labels=["UI: PersonalList +", "PersonalForm", ": Web App"],
    client_labels=["S: usuarios.service", ": HttpClient"],
    router_labels=["R: /api/v1/usuarios", ": FastAPI Router"],
    service_labels=["SV: usuarios/service.py", ": service.py"],
    db_labels=["BD: users, suscripciones,", "planes", ": PostgreSQL multitenant"],
    events=[
        (0, 1, "1: abrir Gestión de Personal", False, False),
        (1, 2, "2: listar_usuarios()", False, False),
        (2, 3, "3: GET /api/v1/usuarios", False, False),
        (3, 4, "4: listar_usuarios(tenant_id)", False, False),
        (4, 5, "5: SELECT User WHERE tenant_id = scope.tenant_id", False, False),
        (5, 4, "6: list[User]", True, False),
        (4, 3, "7: 200 OK · List[UserOut]", True, False),
        (3, 2, "8: usuarios", True, False),
        (2, 1, "9: muestra lista de cajeros y encargados", True, False),
        (0, 1, "10: registrarUsuario(nombre, email, password, rol='cajero')", False, False),
        (1, 2, "11: crear_usuario(dto)", False, False),
        (2, 3, "12: POST /api/v1/usuarios", False, False),
        (3, 4, "13: crear_usuario(data, tenant_id)", False, False),
        (4, 4, "14: verificar_cupo_usuarios(tenant_id)", False, True),
        (4, 5, "15: SELECT COUNT(*) FROM User WHERE tenant_id=?", False, False),
        (5, 4, "16: total_usuarios", True, False),
        (4, 5, "17: SELECT User WHERE tenant_id=? AND email=?", False, False),
        (5, 4, "18: existe?", True, False),
        (4, 4, "19: get_password_hash(password)", False, True),
        (4, 5, "20: INSERT User (tenant_id, email, hashed_pwd, rol, activo)", False, False),
        (4, 3, "21: Usuario creado", True, False),
        (4, 3, "22: 400 BAD REQUEST 'Límite de usuarios alcanzado para el plan'", True, False),
        (3, 2, "23: 201 Created · UserOut", True, False),
        (2, 1, "24: usuario registrado", True, False),
        (1, 0, "25: lista actualizada con nuevo personal", True, False)
    ],
    alt_blocks=[
        (560.0, 205.0, "total_usuarios < max_usuarios AND email libre", "else: límite o email duplicado", 695.0)
    ]
)

make_communication_svg(
    filename="CU-03_comunicacion.svg",
    title="CU-03: Administrar Usuarios y Roles del Personal",
    actor_name="AdminTenant",
    ui_name="PersonalUI",
    ctrl_name="UsuarioCtr",
    entity_name="User",
    messages=[
        (135.0, 78.0, "1: abrirPersonal()", "right"),
        (135.0, 96.0, "1.1: nuevoUsuario(nombre, email, rol, pwd)", "right"),
        (345.0, 96.0, "1.2: crear_usuario(data)", "right"),
        (590.0, 96.0, "1.3: verificarCupo() e insertar()", "right"),
        (610.0, 172.0, "1.4: usuarioCreado()", "left"),
        (350.0, 200.0, "1.5: personalActualizado()", "left")
    ]
)

# =========================================================================
# 4. CU-10: Gestión de Proveedores
# =========================================================================
make_sequence_svg(
    filename="CU-10_secuencia.svg",
    title="CU-10: Gestión de Proveedores Textiles (Web)",
    actor_name="Encargado / Admin",
    ui_labels=["UI: ProveedoresList +", "ProveedorForm", ": Web App"],
    client_labels=["S: proveedores.service", ": HttpClient"],
    router_labels=["R: /api/v1/proveedores", ": FastAPI Router"],
    service_labels=["SV: proveedores/service.py", ": service.py"],
    db_labels=["BD: proveedores", ": PostgreSQL multitenant"],
    events=[
        (0, 1, "1: abrir Proveedores", False, False),
        (1, 2, "2: listar_proveedores()", False, False),
        (2, 3, "3: GET /api/v1/proveedores", False, False),
        (3, 4, "4: listar_proveedores(tenant_id)", False, False),
        (4, 5, "5: SELECT Proveedor WHERE tenant_id = scope.tenant_id", False, False),
        (5, 4, "6: list[Proveedor]", True, False),
        (4, 3, "7: 200 OK · List[ProveedorOut]", True, False),
        (3, 2, "8: proveedores", True, False),
        (2, 1, "9: muestra directorio textil", True, False),
        (0, 1, "10: registrarProveedor(nombre='TexAndina', nit='987654', contacto='Carlos')", False, False),
        (1, 2, "11: crear_proveedor(dto)", False, False),
        (2, 3, "12: POST /api/v1/proveedores", False, False),
        (3, 4, "13: crear_proveedor(data, tenant_id)", False, False),
        (4, 5, "14: SELECT Proveedor WHERE tenant_id=? AND nit=?", False, False),
        (5, 4, "15: existe?", True, False),
        (4, 5, "16: INSERT Proveedor (tenant_id, nombre, nit, contacto, tel, email)", False, False),
        (4, 3, "17: Proveedor registrado", True, False),
        (4, 3, "18: 409 CONFLICT 'Ya existe un proveedor con este NIT'", True, False),
        (3, 2, "19: 201 Created · ProveedorOut", True, False),
        (2, 1, "20: proveedor guardado", True, False),
        (1, 0, "21: directorio actualizado", True, False)
    ],
    alt_blocks=[
        (560.0, 155.0, "NIT libre en tenant", "else: NIT duplicado", 635.0)
    ]
)

make_communication_svg(
    filename="CU-10_comunicacion.svg",
    title="CU-10: Gestión de Proveedores",
    actor_name="EncargadoTienda",
    ui_name="ProveedoresUI",
    ctrl_name="ProveedorCtr",
    entity_name="Proveedor",
    messages=[
        (135.0, 78.0, "1: abrirProveedores()", "right"),
        (135.0, 96.0, "1.1: nuevoProveedor(nombre, nit, contacto)", "right"),
        (345.0, 96.0, "1.2: crear_proveedor(data)", "right"),
        (590.0, 96.0, "1.3: verificarNIT() e insertar()", "right"),
        (610.0, 172.0, "1.4: proveedorRegistrado()", "left"),
        (350.0, 200.0, "1.5: listaActualizada()", "left")
    ]
)

# =========================================================================
# 5. CU-11: Gestión de Clientes del Tenant
# =========================================================================
make_sequence_svg(
    filename="CU-11_secuencia.svg",
    title="CU-11: Gestión de Clientes de Tienda (Web)",
    actor_name="Cajero / Encargado",
    ui_labels=["UI: ClientesList +", "ClienteForm", ": Web App"],
    client_labels=["S: clientes.service", ": HttpClient"],
    router_labels=["R: /api/v1/clientes", ": FastAPI Router"],
    service_labels=["SV: clientes/service.py", ": service.py"],
    db_labels=["BD: clientes", ": PostgreSQL multitenant"],
    events=[
        (0, 1, "1: abrir Cartera de Clientes", False, False),
        (1, 2, "2: listar_clientes(query='Valeria')", False, False),
        (2, 3, "3: GET /api/v1/clientes?q=Valeria", False, False),
        (3, 4, "4: listar_clientes(q, tipo, activo, tenant_id)", False, False),
        (4, 5, "5: SELECT Cliente WHERE tenant_id = scope.tenant_id AND nombre ILIKE '%Valeria%'", False, False),
        (5, 4, "6: list[Cliente]", True, False),
        (4, 3, "7: 200 OK · List[ClienteOut]", True, False),
        (3, 2, "8: clientes encontrados", True, False),
        (2, 1, "9: muestra lista filtrada", True, False),
        (0, 1, "10: registrarCliente(nombre='Valeria', ci_nit='8765432', tipo='vip')", False, False),
        (1, 2, "11: crear_cliente(dto)", False, False),
        (2, 3, "12: POST /api/v1/clientes", False, False),
        (3, 4, "13: crear_cliente(data, tenant_id)", False, False),
        (4, 5, "14: SELECT Cliente WHERE tenant_id=? AND (ci_nit=? OR email=?)", False, False),
        (5, 4, "15: existe?", True, False),
        (4, 5, "16: INSERT Cliente (tenant_id, nombre, apellido, ci_nit, tel, email, tipo)", False, False),
        (4, 3, "17: Cliente registrado con éxito", True, False),
        (4, 3, "18: 409 CONFLICT 'Ya existe un cliente con este CI/NIT o correo'", True, False),
        (3, 2, "19: 201 Created · ClienteOut", True, False),
        (2, 1, "20: cliente guardado", True, False),
        (1, 0, "21: cartera actualizada", True, False)
    ],
    alt_blocks=[
        (560.0, 155.0, "CI/NIT y correo libres en tenant", "else: duplicado", 635.0)
    ]
)

make_communication_svg(
    filename="CU-11_comunicacion.svg",
    title="CU-11: Gestión de Clientes de Tienda",
    actor_name="CajeroTienda",
    ui_name="ClientesUI",
    ctrl_name="ClienteCtr",
    entity_name="Cliente",
    messages=[
        (135.0, 78.0, "1: buscarCliente(ci_nit)", "right"),
        (135.0, 96.0, "1.1: nuevoCliente(nombre, ci_nit, tipo)", "right"),
        (345.0, 96.0, "1.2: crear_cliente(data)", "right"),
        (590.0, 96.0, "1.3: validarUnicidad() e insertar()", "right"),
        (610.0, 172.0, "1.4: clienteRegistrado()", "left"),
        (350.0, 200.0, "1.5: carteraActualizada()", "left")
    ]
)

# =========================================================================
# 6. Galería HTML interactiva
# =========================================================================
gallery_html = """<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <title>GangaSaaS — Parcial 2 — Diagramas UML (Jaime - Casos de Uso Asignados)</title>
  <style>
    body {
      background: #0F172A;
      color: #F8FAFC;
      margin: 0;
      padding: 32px 40px;
      font-family: 'Segoe UI', -apple-system, sans-serif;
    }
    header {
      margin-bottom: 32px;
      border-bottom: 1px solid rgba(255,255,255,0.1);
      padding-bottom: 20px;
    }
    h1 {
      font-size: 24px;
      color: #60A5FA;
      margin: 0 0 8px 0;
    }
    p.hint {
      color: #94A3B8;
      font-size: 14px;
      margin: 0;
    }
    .cu-section {
      background: #1E293B;
      border-radius: 12px;
      border: 1px solid #334155;
      padding: 24px;
      margin-bottom: 36px;
    }
    .cu-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 16px;
      border-bottom: 1px solid #334155;
      padding-bottom: 12px;
    }
    .cu-title {
      font-size: 18px;
      font-weight: bold;
      color: #38BDF8;
    }
    .cu-badge {
      background: #0284C7;
      color: white;
      padding: 4px 12px;
      border-radius: 6px;
      font-size: 12px;
      font-weight: 600;
    }
    .diagram-container {
      margin-top: 18px;
    }
    .diagram-title {
      font-size: 14px;
      font-weight: 600;
      color: #E2E8F0;
      margin-bottom: 8px;
    }
    .svg-wrapper {
      background: #FFFFFF;
      border-radius: 8px;
      padding: 12px;
      overflow-x: auto;
      box-shadow: 0 4px 6px -1px rgba(0,0,0,0.3);
    }
    .svg-wrapper img {
      display: block;
      max-width: 100%;
      height: auto;
    }
    .nav-bar {
      position: sticky;
      top: 0;
      background: #0F172A;
      padding: 12px 0;
      z-index: 100;
      display: flex;
      gap: 10px;
      border-bottom: 1px solid #1E293B;
      margin-bottom: 24px;
      flex-wrap: wrap;
    }
    .nav-btn {
      background: #1E293B;
      color: #94A3B8;
      border: 1px solid #334155;
      padding: 6px 14px;
      border-radius: 6px;
      cursor: pointer;
      text-decoration: none;
      font-size: 13px;
      transition: all 0.2s;
    }
    .nav-btn:hover {
      background: #2563EB;
      color: white;
      border-color: #2563EB;
    }
  </style>
</head>
<body>

  <header>
    <h1>GangaSaaS — Diagramas UML (Metodología ICONIX · UAGRM)</h1>
    <p class="hint">Diagramas de Secuencia y de Comunicación correspondientes a los 5 casos de uso de gestión del SaaS multitenant. Estilo Enterprise Architect profesional.</p>
  </header>

  <nav class="nav-bar">
    <a href="#cu08" class="nav-btn">CU-08: Productos y Variantes</a>
    <a href="#cu09" class="nav-btn">CU-09: Catálogos Base</a>
    <a href="#cu03" class="nav-btn">CU-03: Usuarios y Roles</a>
    <a href="#cu10" class="nav-btn">CU-10: Proveedores</a>
    <a href="#cu11" class="nav-btn">CU-11: Clientes</a>
  </nav>

  <!-- CU-08 -->
  <section class="cu-section" id="cu08">
    <div class="cu-header">
      <div class="cu-title">CU-08: Gestión de Productos y Variantes</div>
      <span class="cu-badge">Catálogo e Inventario</span>
    </div>
    <div class="diagram-container">
      <div class="diagram-title">Diagrama de Secuencia (Flujo con validación de límite de plan)</div>
      <div class="svg-wrapper">
        <img src="CU-08_secuencia.svg" alt="CU-08 Secuencia">
      </div>
    </div>
    <div class="diagram-container">
      <div class="diagram-title">Diagrama de Comunicación (Objetos Robustez: Boundary, Control, Entity)</div>
      <div class="svg-wrapper">
        <img src="CU-08_comunicacion.svg" alt="CU-08 Comunicación">
      </div>
    </div>
  </section>

  <!-- CU-09 -->
  <section class="cu-section" id="cu09">
    <div class="cu-header">
      <div class="cu-title">CU-09: Catálogos Base (Categorías, Tallas, Colores y Temporadas)</div>
      <span class="cu-badge">Atributos Maestros</span>
    </div>
    <div class="diagram-container">
      <div class="diagram-title">Diagrama de Secuencia (Aislamiento por Tenant)</div>
      <div class="svg-wrapper">
        <img src="CU-09_secuencia.svg" alt="CU-09 Secuencia">
      </div>
    </div>
    <div class="diagram-container">
      <div class="diagram-title">Diagrama de Comunicación</div>
      <div class="svg-wrapper">
        <img src="CU-09_comunicacion.svg" alt="CU-09 Comunicación">
      </div>
    </div>
  </section>

  <!-- CU-03 -->
  <section class="cu-section" id="cu03">
    <div class="cu-header">
      <div class="cu-title">CU-03: Administrar Usuarios y Roles del Personal</div>
      <span class="cu-badge">Control de Cupo</span>
    </div>
    <div class="diagram-container">
      <div class="diagram-title">Diagrama de Secuencia (Roles cajero, encargado, admin y cupo del plan)</div>
      <div class="svg-wrapper">
        <img src="CU-03_secuencia.svg" alt="CU-03 Secuencia">
      </div>
    </div>
    <div class="diagram-container">
      <div class="diagram-title">Diagrama de Comunicación</div>
      <div class="svg-wrapper">
        <img src="CU-03_comunicacion.svg" alt="CU-03 Comunicación">
      </div>
    </div>
  </section>

  <!-- CU-10 -->
  <section class="cu-section" id="cu10">
    <div class="cu-header">
      <div class="cu-title">CU-10: Gestión de Proveedores</div>
      <span class="cu-badge">Cadena de Suministro</span>
    </div>
    <div class="diagram-container">
      <div class="diagram-title">Diagrama de Secuencia (Registro de proveedor con NIT)</div>
      <div class="svg-wrapper">
        <img src="CU-10_secuencia.svg" alt="CU-10 Secuencia">
      </div>
    </div>
    <div class="diagram-container">
      <div class="diagram-title">Diagrama de Comunicación</div>
      <div class="svg-wrapper">
        <img src="CU-10_comunicacion.svg" alt="CU-10 Comunicación">
      </div>
    </div>
  </section>

  <!-- CU-11 -->
  <section class="cu-section" id="cu11">
    <div class="cu-header">
      <div class="cu-title">CU-11: Gestión de Clientes del Tenant</div>
      <span class="cu-badge">Compradores y Fidelización</span>
    </div>
    <div class="diagram-container">
      <div class="diagram-title">Diagrama de Secuencia (Búsqueda textual y alta con CI/NIT)</div>
      <div class="svg-wrapper">
        <img src="CU-11_secuencia.svg" alt="CU-11 Secuencia">
      </div>
    </div>
    <div class="diagram-container">
      <div class="diagram-title">Diagrama de Comunicación</div>
      <div class="svg-wrapper">
        <img src="CU-11_comunicacion.svg" alt="CU-11 Comunicación">
      </div>
    </div>
  </section>

</body>
</html>
"""

gallery_path = os.path.join(OUTPUT_DIR, "galeria.html")
with open(gallery_path, "w", encoding="utf-8") as f:
    f.write(gallery_html)
print(f"Generated {gallery_path}")

print("All diagrams generated successfully!")
