#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ea_uml.py - Diagramas UML estilo Enterprise Architect (PUDS) desde un spec JSON."""
import argparse, html, json, math, os, random, re, sys, unicodedata
from collections import Counter, defaultdict

FONT = "Segoe UI, Arial, sans-serif"
AVISOS = []


def aviso(m):
    AVISOS.append(m)


def esc(s):
    return html.escape(str(s), quote=False)


def num(cid):
    m = re.findall(r"\d+", str(cid))
    return int(m[0]) if m else 0


def slug(s):
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode()
    s = re.sub(r"[^A-Za-z0-9]+", "_", str(s)).strip("_").lower()
    return s or "x"


def T(x, y, s, size=11.0, bold=False, italic=False, anchor="start", fill="#222222"):
    b = ' font-weight="bold"' if bold else ""
    i = ' font-style="italic"' if italic else ""
    return (f'<text x="{x:.1f}" y="{y:.1f}" text-anchor="{anchor}" font-family="{FONT}" '
            f'font-size="{size}"{b}{i} fill="{fill}">{esc(s)}</text>')


def tw(s, size=11.5, bold=True):
    return len(str(s)) * size * (0.56 if bold else 0.52)


def wrap(s, maxc):
    words, lines, cur = str(s).split(), [], ""
    for w in words:
        if cur and len(cur) + 1 + len(w) > maxc:
            lines.append(cur)
            cur = w
        else:
            cur = f"{cur} {w}".strip()
    if cur:
        lines.append(cur)
    return lines or [""]


def split2(s):
    words = str(s).split()
    if len(s) <= 12 or len(words) == 1:
        return [s]
    best = None
    for i in range(1, len(words)):
        a, b = " ".join(words[:i]), " ".join(words[i:])
        m = max(len(a), len(b))
        if best is None or m < best[0]:
            best = (m, [a, b])
    return best[1]


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


def svg(w, h, body):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{int(w)}" height="{int(h)}" '
            f'viewBox="0 0 {int(w)} {int(h)}" font-family="{FONT}">{DEFS}'
            f'<rect width="100%" height="100%" fill="#FFFFFF"/>{body}</svg>')


def frame(w, h, label):
    lw = 14 + tw(label, 12.5)
    return (f'<rect x="1" y="1" width="{w-2}" height="{h-2}" fill="#FFFFFF" stroke="#8C8C8C" stroke-width="1.2"/>'
            f'<path d="M1,1 L{1+lw:.0f},1 L{1+lw:.0f},19 L{lw-8:.0f},27 L1,27 Z" fill="#FFFFFF" stroke="#8C8C8C" stroke-width="1.2"/>'
            + T(9, 19, label, 12.5, True, True, fill="#1A1A1A"))


def actor_lines(a):
    lines = a["nombre"] if isinstance(a["nombre"], list) else split2(a["nombre"])
    return lines + (["«externo»"] if a.get("externo") else [])


def actor_alto(a):
    return 60 + 13 * (len(actor_lines(a)) - 1) + 5


def actor(cx, cy, a):
    c = "#5A748F"
    s = (f'<circle cx="{cx}" cy="{cy}" r="8" fill="#FDF3CF" stroke="{c}" stroke-width="1.4"/>'
         f'<line x1="{cx}" y1="{cy+8}" x2="{cx}" y2="{cy+30}" stroke="{c}" stroke-width="1.4"/>'
         f'<line x1="{cx-13}" y1="{cy+15}" x2="{cx+13}" y2="{cy+15}" stroke="{c}" stroke-width="1.4"/>'
         f'<line x1="{cx}" y1="{cy+30}" x2="{cx-11}" y2="{cy+46}" stroke="{c}" stroke-width="1.4"/>'
         f'<line x1="{cx}" y1="{cy+30}" x2="{cx+11}" y2="{cy+46}" stroke="{c}" stroke-width="1.4"/>')
    for i, ln in enumerate(actor_lines(a)):
        s += T(cx, cy + 60 + i * 13, ln, 11.5, True, True, "middle", "#2B2B2B")
    return s


def oval(cx, cy, lines, rx, ry, cid=""):
    s = f'<ellipse cx="{cx:.1f}" cy="{cy:.1f}" rx="{rx}" ry="{ry}" fill="url(#gOval)" stroke="#6E8FB5" stroke-width="1.3"/>'
    y0 = cy - (len(lines) - 1) * 6.5
    for i, ln in enumerate(lines):
        yy = y0 + i * 13
        d = abs(yy - cy) + 5
        disp = 2 * rx * math.sqrt(max(0.0, 1 - (d / ry) ** 2)) - 12
        if tw(ln) > disp:
            aviso(f"{cid}: la linea '{ln}' no entra en el ovalo")
        s += T(cx, yy + 4, ln, 11.5, True, True, "middle", "#17375E")
    return s


def edge_ellipse(cx, cy, rx, ry, tx, ty):
    dx, dy = tx - cx, ty - cy
    if dx == 0 and dy == 0:
        return cx, cy
    t = 1.0 / math.sqrt((dx / rx) ** 2 + (dy / ry) ** 2)
    return cx + dx * t, cy + dy * t


def clip_rect(x, y, w, h, tx, ty):
    cx, cy = x + w / 2, y + h / 2
    dx, dy = tx - cx, ty - cy
    if dx == 0 and dy == 0:
        return cx, cy
    sx = (w / 2) / abs(dx) if dx else float("inf")
    sy = (h / 2) / abs(dy) if dy else float("inf")
    s = min(sx, sy)
    return cx + dx * s, cy + dy * s


def _choca(r, obst):
    x, y, w, h = r
    return any(x < ox + ow and ox < x + w and y < oy + oh and oy < y + h for ox, oy, ow, oh in obst)


def dep_line(p1, p2, label=None, color="#7A6A50", marker="arrOpen", dash=True, obst=()):
    (x1, y1), (x2, y2) = p1, p2
    d = ' stroke-dasharray="5,4"' if dash else ""
    m = f' marker-end="url(#{marker})"' if marker else ""
    s = f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{color}" stroke-width="1.1"{d}{m}/>'
    if label:
        w0 = tw(label, 10, False) + 8
        mx, my = (x1 + x2) / 2, (y1 + y2) / 2
        for t in (0.5, 0.4, 0.6, 0.3, 0.7, 0.2, 0.8):
            cx, cy = x1 + (x2 - x1) * t, y1 + (y2 - y1) * t
            if not _choca((cx - w0 / 2, cy - 15, w0, 13), obst):
                mx, my = cx, cy
                break
        w = tw(label, 10, False) + 8
        s += f'<rect x="{mx-w/2:.1f}" y="{my-15:.1f}" width="{w:.1f}" height="13" fill="#FFFFFF" opacity="0.9"/>'
        s += T(mx, my - 5, label, 10, False, True, "middle", color)
    return s


R_SYM = 24


def comunicacion_rica(titulo, actor_dict, nodos, mensajes, W=1200, H=680):
    """Comunicacion con N participantes y N mensajes. `nodos`: lista de
    {id, tipo: boundary|control|entity, nombre, x, y}. `mensajes`:
    [{num, de, a, texto}]. Posiciones en coordenadas de pixel absolutas."""
    b = frame(W, H, titulo)
    ax = actor_dict.get("x", 70)
    ay = actor_dict.get("y", H / 2)
    b += actor(ax, ay - 22, {"nombre": actor_dict["nombre"]})
    pos = {"A": (ax + 14, ay + 22)}
    for n in nodos:
        pos[n["id"]] = (n["x"], n["y"])
    conect = set()
    for m in mensajes:
        d, a = m["de"], m["a"]
        conect.add((d, a) if d < a else (a, d))
    for (d, a) in conect:
        x1, y1 = pos[d]
        x2, y2 = pos[a]
        dx, dy = x2 - x1, y2 - y1
        L = math.hypot(dx, dy) or 1
        ux, uy = dx / L, dy / L
        if d != "A":
            x1 += ux * (R_SYM + 2)
            y1 += uy * (R_SYM + 2)
        if a != "A":
            x2 -= ux * (R_SYM + 2)
            y2 -= uy * (R_SYM + 2)
        b += f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="#7A7A7A" stroke-width="1.2"/>'
    # simbolos
    for n in nodos:
        b += sym(n["tipo"], n["x"], n["y"], n["nombre"])
    # pre-contar mensajes por cable
    totales = defaultdict(int)
    for m in mensajes:
        totales[tuple(sorted([m["de"], m["a"]]))] += 1
    indices = defaultdict(int)
    for m in mensajes:
        d, a = m["de"], m["a"]
        key = tuple(sorted([d, a]))
        # tomo coordenadas desde el key ordenado (consistente para todos los mensajes
        # de la arista, sin importar la direccion d->a de cada uno)
        p1, p2 = pos[key[0]], pos[key[1]]
        x1, y1 = p1
        x2, y2 = p2
        total = totales[key]
        k = indices[key]
        indices[key] = k + 1
        dx, dy = x2 - x1, y2 - y1
        L = math.hypot(dx, dy) or 1
        ux, uy = dx / L, dy / L
        # perpendicular unitario; eligo la componente que apunte HACIA ARRIBA de la pagina
        nx, ny = -uy, ux
        if ny > 0:
            nx, ny = -nx, -ny
        # Stack perpendicular: cada mensaje se separa 20px del anterior.
        # Pequeno avance longitudinal para evitar que las flechas se toquen.
        paso_perp = 20
        paso_long = 0.08  # 8% de la longitud entre mensajes consecutivos
        offset_perp = (k - (total - 1) / 2) * paso_perp
        offset_long = (k - (total - 1) / 2) * paso_long
        mx = x1 + ux * (0.5 + offset_long) * L + nx * offset_perp
        my = y1 + uy * (0.5 + offset_long) * L + ny * offset_perp
        # ajusto ux,uy a la direccion REAL del mensaje para la flecha
        if d != key[0]:
            ux, uy = -ux, -uy
        # Offset perpendicular pequeño para que la flecha no pise el cable.
        mx += nx * 12
        my += ny * 12
        text = f"{m['num']}: {m['texto']}"
        wmsg = tw(text, 10.5, False) + 12
        b += f'<rect x="{mx-wmsg/2:.1f}" y="{my-14:.1f}" width="{wmsg:.1f}" height="16" fill="#FFFFFF" opacity="0.95"/>'
        b += T(mx, my - 2, text, 10.5, False, True, "middle", "#1A1A1A")
        # flecha debajo del texto, paralela al cable
        sx = mx - 22 * ux
        sy = my + 10 - 22 * uy
        ex = mx + 22 * ux
        ey = my + 10 + 22 * uy
        b += f'<line x1="{sx:.1f}" y1="{sy:.1f}" x2="{ex:.1f}" y2="{ey:.1f}" stroke="#1A1A1A" stroke-width="1.5" marker-end="url(#arrSolid)"/>'
    return svg(W, H, b)


def _sym_label(cx, y, label):
    lines = label if isinstance(label, list) else [label]
    return "".join(T(cx, y + i * 13, ln, 11.5, True, True, "middle", "#2B2B2B") for i, ln in enumerate(lines))


def sym(tipo, cx, cy, label):
    R = R_SYM
    st = 'stroke="#4E7A76" stroke-width="1.6"'
    circ = f'<circle cx="{cx}" cy="{cy}" r="{R}" fill="url(#gTeal)" stroke="#4E7A76" stroke-width="1.5"/>'
    if tipo == "boundary":
        return (f'<line x1="{cx-R-16}" y1="{cy-14}" x2="{cx-R-16}" y2="{cy+14}" {st}/>'
                f'<line x1="{cx-R-16}" y1="{cy}" x2="{cx-R}" y2="{cy}" {st}/>' + circ + _sym_label(cx, cy + R + 18, label))
    if tipo == "control":
        return (circ + f'<path d="M{cx-9},{cy-R-6} L{cx+3},{cy-R+2} M{cx-9},{cy-R-6} L{cx+1},{cy-R-11}" fill="none" {st}/>'
                + _sym_label(cx, cy + R + 18, label))
    return (circ + f'<line x1="{cx-R}" y1="{cy+R+3}" x2="{cx+R}" y2="{cy+R+3}" {st}/>'
            + _sym_label(cx, cy + R + 21, label))


def msg(x, y, text, direction):
    s = T(x, y, text, 10.5, False, True, fill="#1A1A1A")
    ax = x + tw(text, 10.5, False) + 8
    if direction == ">":
        s += f'<line x1="{ax:.1f}" y1="{y-4}" x2="{ax+24:.1f}" y2="{y-4}" stroke="#1A1A1A" stroke-width="1.6" marker-end="url(#arrSolid)"/>'
    else:
        s += f'<line x1="{ax+24:.1f}" y1="{y-4}" x2="{ax:.1f}" y2="{y-4}" stroke="#1A1A1A" stroke-width="1.6" marker-end="url(#arrSolid)"/>'
    return s


def comunicacion(titulo, act, d, W=940):
    R = R_SYM
    nodes = [("boundary", d["boundary"]), ("control", d["control"]), ("entity", d["entity"])]
    ms = list(d["mensajes"])
    if len(ms) != 6:
        aviso(f"{titulo}: 'mensajes' debe tener 6 textos")
        ms = (ms + ["..."] * 6)[:6]
    ax, cy = 95, 130
    xs = [ax] + [320 + i * 245 for i in range(3)]
    half = [max(40, max(tw(x) for x in actor_lines(act)) / 2)]
    for _t, lbl in nodes:
        half.append(max(R + 4, max(tw(x) for x in (lbl if isinstance(lbl, list) else [lbl])) / 2))
    plan = [(0, ">", 1), (0, ">", 0), (1, ">", 0), (2, ">", 0), (2, "<", -1), (1, "<", -1)]
    nums = ["1", "1.1", "1.2", "1.3", "1.4", "1.5"]
    starts = {0: ax + 44, 1: xs[1] + R + 10, 2: xs[2] + R + 10}
    colocados, baja = [], False
    for (link, dr, row), n_, t in zip(plan, nums, ms):
        text = f"{n_}: {t}"
        wmsg = tw(text, 10.5, False) + 34
        if row >= 0:
            fin = starts.get(link + 1, W - 12) - 10 if row == 0 else W - 12
            if starts[link] + wmsg > fin:
                aviso(f"{titulo}: mensaje {n_} pisa al siguiente; acortalo")
            colocados.append((starts[link], cy - 30 - row * 17, text, dr))
        else:
            izq = xs[link] + half[link] + 10
            der = xs[link + 1] - half[link + 1] - 10
            if wmsg <= der - izq:
                colocados.append((izq + (der - izq - wmsg) / 2, cy + 42, text, dr))
            else:
                baja = True
                mid = (xs[link] + xs[link + 1]) / 2
                colocados.append((max(ax + 30, min(W - 12 - wmsg, mid - wmsg / 2)), cy + 70, text, dr))
    H = 262 if baja else 238
    b = frame(W, H, titulo)
    b += f'<line x1="{ax+14}" y1="{cy}" x2="{xs[1]-R-34}" y2="{cy}" stroke="#7A7A7A" stroke-width="1.2"/>'
    for i in range(1, 3):
        b += f'<line x1="{xs[i]+R}" y1="{cy}" x2="{xs[i+1]-R}" y2="{cy}" stroke="#7A7A7A" stroke-width="1.2"/>'
    b += actor(ax, cy - 52, act)
    for (tipo, lbl), x in zip(nodes, xs[1:]):
        b += sym(tipo, x, cy, lbl)
    for x, y, text, dr in colocados:
        b += msg(x, y, text, dr)
    return svg(W, H, b)


def class_box(x, y, w, estereotipo, nombre, attrs, ops, externa=False, destacada=False):
    hh = 34 if estereotipo else 24
    ah = len(attrs) * 13.5 + (8 if attrs else 0)
    oh = len(ops) * 13.5 + (8 if ops else 0)
    h = hh + ah + oh
    dash = ' stroke-dasharray="4,3"' if externa else ""
    if destacada:
        fill, stroke, sw = "#FCE4D6", "#D45500", "2.2"
    else:
        fill, stroke, sw = "url(#gCls)", "#B0925A", "1.2"
    s = f'<rect x="{x:.1f}" y="{y:.1f}" width="{w}" height="{h:.1f}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"{dash}/>'
    if estereotipo:
        s += T(x + w / 2, y + 13, f"«{estereotipo}»", 10, fill="#6B5A34", anchor="middle")
        s += T(x + w / 2, y + 27, nombre, 11.5, True, True, "middle", "#3F2F14")
    else:
        s += T(x + w / 2, y + 16.5, nombre, 11.5, True, externa, "middle", "#7A6A50" if externa else "#3F2F14")
    if attrs or ops:
        s += f'<line x1="{x:.1f}" y1="{y+hh:.1f}" x2="{x+w:.1f}" y2="{y+hh:.1f}" stroke="#B0925A" stroke-width="1"/>'
    yy = y + hh + 12
    for a in attrs:
        s += T(x + 8, yy, f"- {a}", 10.5, False, True, fill="#33301F")
        yy += 13.5
    if attrs and ops:
        s += f'<line x1="{x:.1f}" y1="{y+hh+ah:.1f}" x2="{x+w:.1f}" y2="{y+hh+ah:.1f}" stroke="#B0925A" stroke-width="1"/>'
        yy = y + hh + ah + 12
    for o in ops:
        s += T(x + 8, yy, f"+ {o}", 10.5, False, True, fill="#33301F")
        yy += 13.5
    return s, h


def analisis(titulo, act, d, W=1040):
    bd, cd, ents = d["boundary"], d["control"], d["entidades"]
    bx, bw, cx_, cw, ex, ew = 190, 230, 500, 230, 790, 220
    _s, bh = class_box(0, 0, bw, "boundary", bd["nombre"], bd.get("atributos", []), bd.get("operaciones", []))
    _s, ch = class_box(0, 0, cw, "control", cd["nombre"], cd.get("atributos", []), cd.get("operaciones", []))
    ehs = [class_box(0, 0, ew, "entity", e["nombre"], e.get("atributos", []), [])[1] for e in ents]
    stack = sum(ehs) + 26 * (len(ents) - 1)
    H = int(max(bh + 160, stack + 150, ch + 190))
    b = frame(W, H, titulo)
    by, cy_, ey = (H - bh) / 2 + 12, (H - ch) / 2 + 12, (H - stack) / 2 + 12
    ax, ay = 85, H / 2 - 30
    b += f'<line x1="{ax}" y1="{ay+22:.1f}" x2="{bx}" y2="{by+bh/2:.1f}" stroke="#7A7A7A" stroke-width="1.1"/>'
    b += f'<line x1="{bx+bw}" y1="{by+bh/2:.1f}" x2="{cx_}" y2="{cy_+ch/2:.1f}" stroke="#7A7A7A" stroke-width="1.1"/>'
    yy = ey
    for h in ehs:
        b += f'<line x1="{cx_+cw}" y1="{cy_+ch/2:.1f}" x2="{ex}" y2="{yy+h/2:.1f}" stroke="#7A7A7A" stroke-width="1.1"/>'
        yy += h + 26
    b += class_box(bx, by, bw, "boundary", bd["nombre"], bd.get("atributos", []), bd.get("operaciones", []))[0]
    b += class_box(cx_, cy_, cw, "control", cd["nombre"], cd.get("atributos", []), cd.get("operaciones", []))[0]
    yy = ey
    for e, h in zip(ents, ehs):
        b += class_box(ex, yy, ew, "entity", e["nombre"], e.get("atributos", []), [])[0]
        yy += h + 26
    b += actor(ax, ay - 22, act)
    return svg(W, H, b)


def secuencia(titulo, parts, pasos, marcos, W=1100):
    k = len(parts)
    if k >= 8:
        W = max(W, 78 + (k - 1) * 125 + 110)
    sp = (W - 110 - 78) / max(1, k - 1)
    X = {p[0]: 78 + i * sp for i, p in enumerate(parts)}
    bw = min(132, sp - 10)
    maxc = int((bw - 8) / (9.6 * 0.52))
    fixed = []
    for pid, kind, lines in parts:
        if kind == "box":
            nl = []
            for ln in lines:
                nl += wrap(ln.replace(",", ", ").replace(",  ", ", "), maxc) if tw(ln, 9.6, False) > bw - 8 else [ln]
            lines = nl
        fixed.append((pid, kind, lines))
    parts = fixed
    nh = max([len(l) for _p, k, l in parts if k == "box"] or [2])
    y0, dy, n = max(128, 46 + 16 + nh * 12.5 + 26), 34, len(pasos)
    off = [0.0] * n
    for _kind, _g, i0, i1, ei in marcos:
        for i in range(n):
            if i >= i0:
                off[i] += 26
            if ei is not None and i >= ei:
                off[i] += 16
            if i > i1:
                off[i] += 10
    Y = [y0 + i * dy + off[i] for i in range(n)]
    H = int((Y[-1] if n else y0) + 70)
    b = frame(W, H, titulo)
    kinds = {p[0]: p[1] for p in parts}
    for pid, kind, _l in parts:
        b += f'<line x1="{X[pid]:.1f}" y1="{46 + 16 + nh * 12.5 if kind == "box" else 104}" x2="{X[pid]:.1f}" y2="{H-28}" stroke="#9A9A9A" stroke-width="1" stroke-dasharray="4,4"/>'
    first, last = {}, {}
    for i, (f_, t, _lbl, kd) in enumerate(pasos):
        for pid in ([f_, t] if kd != "self" else [f_]):
            if pid not in X:
                aviso(f"{titulo}: paso {i+1} usa participante '{pid}' inexistente")
                continue
            first.setdefault(pid, i)
            last[pid] = i
    for pid in first:
        if kinds.get(pid) == "actor":
            continue
        ya, yb = Y[first[pid]] - 14, Y[last[pid]] + 12
        b += f'<rect x="{X[pid]-5:.1f}" y="{ya:.1f}" width="10" height="{yb-ya:.1f}" fill="#F6F1DE" stroke="#8C8C8C" stroke-width="1"/>'
    for kind, guard, i0, i1, ei in marcos:
        xs = []
        for i in range(i0, i1 + 1):
            f_, t, _lbl, kd = pasos[i]
            xs += [X.get(f_, 0), X.get(f_, 0) + 195] if kd == "self" else [X.get(f_, 0), X.get(t, 0)]
        x0, x1 = max(4, min(xs) - 58), min(W - 4, max(xs) + 64)
        ya, yb = Y[i0] - 44, Y[i1] + 14
        b += f'<rect x="{x0:.1f}" y="{ya:.1f}" width="{x1-x0:.1f}" height="{yb-ya:.1f}" fill="none" stroke="#8C8C8C" stroke-width="1.2"/>'
        b += (f'<path d="M{x0:.1f},{ya:.1f} L{x0+42:.1f},{ya:.1f} L{x0+42:.1f},{ya+13:.1f} L{x0+34:.1f},{ya+19:.1f} L{x0:.1f},{ya+19:.1f} Z" fill="#EDEDED" stroke="#8C8C8C" stroke-width="1"/>'
              + T(x0 + 7, ya + 14, kind, 10, True, fill="#333333") + T(x0 + 52, ya + 14, guard, 10, False, True, fill="#333333"))
        if ei is not None:
            ye = Y[ei] - 26
            b += f'<line x1="{x0:.1f}" y1="{ye:.1f}" x2="{x1:.1f}" y2="{ye:.1f}" stroke="#8C8C8C" stroke-width="1" stroke-dasharray="5,4"/>'
            b += T(x0 + 8, ye + 12, "[else]", 10, False, True, fill="#333333")
    for i, (f_, t, lbl, kd) in enumerate(pasos):
        if f_ not in X or (kd != "self" and t not in X):
            continue
        y, x1_, x2_ = Y[i], X[f_], X.get(t, X[f_])
        if kd == "self":
            b += (f'<path d="M{x1_+5:.1f},{y-8} L{x1_+40:.1f},{y-8} L{x1_+40:.1f},{y+6} L{x1_+11:.1f},{y+6}" fill="none" stroke="#3A3A3A" stroke-width="1.2" marker-end="url(#arrSolid)"/>'
                  + T(x1_ + 48, y - 3, lbl, 10, False, True, fill="#1A1A1A"))
            continue
        o = 6 if x2_ > x1_ else -6
        dash = ' stroke-dasharray="5,4"' if kd == "ret" else ""
        mk, col = ("arrRet", "#5A5A5A") if kd == "ret" else ("arrSolid", "#3A3A3A")
        b += f'<line x1="{x1_+o:.1f}" y1="{y}" x2="{x2_-o:.1f}" y2="{y}" stroke="{col}" stroke-width="1.2"{dash} marker-end="url(#{mk})"/>'
        b += T(min(x1_, x2_) + 16, y - 5, lbl, 10, False, True, fill="#1A1A1A")
    for pid, kind, lines in parts:
        x = X[pid]
        if kind == "actor":
            b += actor(x, 40, lines)
        else:
            bh2 = 16 + nh * 12.5
            b += f'<rect x="{x-bw/2:.1f}" y="46" width="{bw:.1f}" height="{bh2}" fill="url(#gTealBox)" stroke="#7A9B98" stroke-width="1.2"/>'
            for j, ln in enumerate(lines):
                if tw(ln, 9.6, False) > bw - 4:
                    aviso(f"{titulo}: cabecera '{ln}' mas ancha que la caja")
                b += T(x, 60 + (nh - len(lines)) * 6.25 + j * 12.5, ln, 9.6, anchor="middle", fill="#20403D")
    return svg(W, H, b)


def clases_diag(titulo, clases, rels, columnas=None, compactas=(), destacadas=()):
    names = [c["nombre"] for c in clases]
    by = {c["nombre"]: c for c in clases}
    adj = defaultdict(set)
    for r in rels:
        if r["de"] in by and r["a"] in by:
            adj[r["de"]].add(r["a"])
            adj[r["a"]].add(r["de"])
    grupos = []
    for c in clases:
        g = c.get("grupo", "")
        if g not in grupos:
            grupos.append(g)
    orden = []
    for g in grupos:
        mem = [c["nombre"] for c in clases if c.get("grupo", "") == g]
        pend = list(mem)
        while pend:
            start = max(pend, key=lambda n: (len(adj[n]), -mem.index(n)))
            cola = [start]
            while cola:
                x = cola.pop(0)
                if x in pend:
                    pend.remove(x)
                    orden.append(x)
                    cola += sorted([y for y in adj[x] if y in pend], key=mem.index)
    n = len(orden)
    C = columnas or (6 if n > 20 else 5 if n > 12 else 4 if n > 6 else 3)

    def dims(nm):
        c = by[nm]
        if nm in compactas:
            return max(110, tw(nm, 11.5) + 24), 26
        attrs = c.get("atributos", [])
        w = max(118, tw(nm, 11.5) + 24, max([tw(f"- {a}", 10.5, False) for a in attrs] or [0]) + 20)
        return w, 24 + len(attrs) * 13.5 + (8 if attrs else 0)

    celdas, fijas = {}, set()
    for nm in orden:
        p = by[nm].get("pos")
        if p:
            celdas[nm] = tuple(p)
            fijas.add(nm)
    nrow0 = math.ceil(n / C) + (1 if n % C == 0 and n > C else 0)
    libres = [(c, r) for r in range(nrow0) for c in range(C) if (c, r) not in celdas.values()]
    for nm in orden:
        if nm not in celdas:
            celdas[nm] = libres.pop(0)
    aristas = [(r["de"], r["a"]) for r in rels if r["de"] in celdas and r["a"] in celdas]

    def seg_rect(p, q, c):
        x0, y0, x1, y1 = c[0] + 0.18, c[1] + 0.2, c[0] + 0.82, c[1] + 0.8
        (ax, ay), (bx, by_) = p, q
        for t in (0.25, 0.4, 0.5, 0.6, 0.75):
            x, y = ax + (bx - ax) * t, ay + (by_ - ay) * t
            if x0 < x < x1 and y0 < y < y1:
                return True
        return False

    def costo(cel):
        tot = 0.0
        ocup = list(cel.items())
        for a_, b_ in aristas:
            (ca, ra), (cb, rb) = cel[a_], cel[b_]
            p, q = (ca + 0.5, ra + 0.5), (cb + 0.5, rb + 0.5)
            dist = math.hypot(ca - cb, (ra - rb) * 1.3)
            tot += dist * dist
            for nm2, c2 in ocup:
                if nm2 not in (a_, b_) and abs(c2[0] + 0.5 - (p[0] + q[0]) / 2) <= abs(p[0] - q[0]) / 2 + 1 \
                        and abs(c2[1] + 0.5 - (p[1] + q[1]) / 2) <= abs(p[1] - q[1]) / 2 + 1 and seg_rect(p, q, c2):
                    tot += 6
        return tot

    if aristas and len(celdas) > 3:
        rnd = random.Random(7)
        movibles = [nm for nm in orden if nm not in fijas]
        todas = [(c, r) for r in range(nrow0) for c in range(C)]
        actual = costo(celdas)
        for _it in range(2500 if n > 12 else 1200):
            if not movibles:
                break
            a_ = rnd.choice(movibles)
            destino = rnd.choice(todas)
            if destino == celdas[a_]:
                continue
            otro = next((k for k, v in celdas.items() if v == destino), None)
            if otro in fijas:
                continue
            viejo = celdas[a_]
            celdas[a_] = destino
            if otro:
                celdas[otro] = viejo
            nuevo = costo(celdas)
            if nuevo <= actual:
                actual = nuevo
            else:
                celdas[a_] = viejo
                if otro:
                    celdas[otro] = destino
        usadas_r = sorted({r for _c, r in celdas.values()})
        usadas_c = sorted({c for c, _r in celdas.values()})
        celdas = {k: (usadas_c.index(c), usadas_r.index(r)) for k, (c, r) in celdas.items()}
    ncols = max(c for c, _r in celdas.values()) + 1
    nrows = max(r for _c, r in celdas.values()) + 1
    colw = max(dims(nm)[0] for nm in orden) + 46
    rowh = [0] * nrows
    for nm, (c, r) in celdas.items():
        rowh[r] = max(rowh[r], dims(nm)[1])
    rowh = [h + 58 for h in rowh]
    W = int(40 + ncols * colw)
    H = int(58 + sum(rowh) + 10)
    rect = {}
    for nm, (c, r) in celdas.items():
        w, h = dims(nm)
        rect[nm] = (20 + c * colw + (colw - w) / 2, 58 + sum(rowh[:r]) + 18, w, h)
    b = frame(W, H, titulo)
    for r in rels:
        if r["de"] not in rect or r["a"] not in rect:
            continue
        x, y, w, h = rect[r["de"]]
        x2, y2, w2, h2 = rect[r["a"]]
        p1 = clip_rect(x, y, w, h, x2 + w2 / 2, y2 + h2 / 2)
        p2 = clip_rect(x2, y2, w2, h2, x + w / 2, y + h / 2)
        tipo = r.get("tipo", "asociacion")
        ms = ""
        if tipo in ("composicion", "agregacion"):
            ms = f' marker-start="url(#{"mComp" if tipo == "composicion" else "mAgr"})"'
        me = ' marker-end="url(#mHer)"' if tipo == "herencia" else ""
        b += f'<line x1="{p1[0]:.1f}" y1="{p1[1]:.1f}" x2="{p2[0]:.1f}" y2="{p2[1]:.1f}" stroke="#555555" stroke-width="1.1"{ms}{me}/>'
        mult = r.get("mult")
        if mult and tipo != "herencia":
            L = math.hypot(p2[0] - p1[0], p2[1] - p1[1]) or 1
            ux, uy = (p2[0] - p1[0]) / L, (p2[1] - p1[1]) / L
            nx, ny = -uy, ux
            for (px, py), s_, sg in ((p1, mult[0], 1), (p2, mult[1], -1)):
                d0 = 24 if (sg == 1 and ms) else 15
                tx, ty = px + ux * d0 * sg + nx * 10 * sg, py + uy * d0 * sg + ny * 10 * sg + 4
                b += T(tx, ty, s_, 10.5, False, False, "middle", "#333333")
    for nm in orden:
        x, y, w, h = rect[nm]
        attrs = [] if nm in compactas else by[nm].get("atributos", [])
        b += class_box(x, y, w, None, nm, attrs, [], externa=nm in compactas, destacada=nm in destacadas)[0]
    # leyenda si hay destacadas
    if destacadas:
        lx, ly = 20, H - 36
        b += f'<rect x="{lx}" y="{ly}" width="22" height="14" fill="#FCE4D6" stroke="#D45500" stroke-width="2"/>'
        b += T(lx + 30, ly + 11, "Clases involucradas en CU-20 Venta de contado sin conexion",
               10.5, True, True, fill="#8B3A00")
    return svg(W, H, b)


PLAT = {"web": "Web", "movil": "Móvil", "móvil": "Móvil", "web+movil": "Web y Móvil", "web+móvil": "Web y Móvil"}


def cargar(path):
    with open(path, encoding="utf-8") as f:
        spec = json.load(f)
    ACT = {a["id"]: a for a in spec.get("actores", [])}
    CU = spec.get("cus", [])
    return spec, ACT, CU


def actor_de(cu, d, ACT):
    a = d.get("actor")
    if a in ACT:
        return ACT[a]
    if isinstance(a, str) and a:
        return {"nombre": a}
    acts = [x for x in cu.get("actores", []) if x in ACT]
    p = next((x for x in acts if not ACT[x].get("externo")), acts[0] if acts else None)
    return ACT[p] if p else {"nombre": "Usuario"}


def partes_de_cadena(spec, c, act):
    st = spec.get("stack", {})
    plat = "movil" if c.get("plataforma", "web") in ("movil", "móvil") else "web"
    pl = st.get(plat, {})
    defaults = {"web": {"ui": ": Angular", "servicio": ": HttpClient"},
                "movil": {"ui": ": Flutter", "servicio": ": dio + JWT", "servicio_nombre": "ApiService"}}[plat]
    ui_t = pl.get("ui", defaults["ui"])
    sv_t = pl.get("servicio", defaults["servicio"])
    sv_n = c.get("servicio") or pl.get("servicio_nombre") or defaults.get("servicio_nombre", "api.service")
    parts = [("A", "actor", act),
             ("U", "box", [f"UI: {c['ui']}", ui_t]),
             ("S", "box", [f"S: {sv_n}", sv_t]),
             ("R", "box", [f"R: {c['ruta']}", st.get("router", ": FastAPI Router")]),
             ("V", "box", [f"SV: {c['service_py']}", st.get("service", ": service.py")])]
    if c.get("externo"):
        parts.append(("X", "box", c["externo"]))
    parts.append(("B", "box", [f"BD: {c['tablas']}", st.get("bd", ": PostgreSQL")]))
    return parts


def generar(spec, ACT, CU, out, solo=None, ciclo=None):
    os.makedirs(out, exist_ok=True)
    CUd = {c["id"]: c for c in CU}
    hechos = []

    def quiere(t):
        return not solo or t in solo

    def guardar(nombre, contenido, seccion, titulo):
        with open(os.path.join(out, nombre), "w", encoding="utf-8") as f:
            f.write(contenido)
        hechos.append((seccion, titulo, nombre))

    def nom_cu(cid):
        c = CUd.get(cid, {"nombre": "?"})
        p = PLAT.get(str(c.get("plataforma", "")).lower())
        return f"{cid}: {c['nombre']}" + (f" ({p})" if p else "")

    per_cu = [c["id"] for c in sorted(CU, key=lambda c: (c.get("ciclo") or 0, num(c["id"])))]
    for tipo in ("comunicacion", "analisis", "secuencia"):
        if not quiere(tipo):
            continue
        datos = spec.get(tipo, {})
        for cid in per_cu:
            if cid not in datos:
                continue
            d, cu = datos[cid], CUd[cid]
            act = actor_de(cu, d, ACT)
            sec = {"comunicacion": "Comunicación", "analisis": "Robustez / Análisis", "secuencia": "Secuencia"}[tipo]
            if tipo == "comunicacion":
                cont = comunicacion(f"sd {cid}: {cu['nombre']}", act, d)
            elif tipo == "analisis":
                cont = analisis(f"class {nom_cu(cid)}", act, d)
            else:
                parts = partes_de_cadena(spec, {**d["cadena"], "plataforma": d["cadena"].get("plataforma", cu.get("plataforma", "web"))}, act)
                num_on = spec.get("numerar_pasos", True)
                pasos = [(p[0], p[1], (f"{i+1}: {p[2]}" if num_on else p[2]), p[3] if len(p) > 3 else "call")
                         for i, p in enumerate(d["pasos"])]
                marcos = []
                for m in d.get("marcos", []):
                    kind, guard, i0, i1 = m[0], m[1], m[2] - 1, m[3] - 1
                    ei = (m[4] - 1) if len(m) > 4 and m[4] else None
                    if not (0 <= i0 <= i1 < len(pasos)):
                        aviso(f"{cid}: marco {m} fuera de rango")
                        continue
                    marcos.append((kind, guard, i0, i1, ei))
                cont = secuencia(f"sd {nom_cu(cid)}", parts, pasos, marcos)
            guardar(f"{cid}_{tipo}.svg", cont, sec, nom_cu(cid))
    if quiere("clases") and spec.get("clases"):
        cls, rels = spec["clases"], spec.get("relaciones", [])
        guardar("clases.svg", clases_diag(f"class Diagrama de Clases — {spec.get('proyecto', '')}".rstrip(" —"), cls, rels,
                                          spec.get("columnas_clases"),
                                          destacadas=set(spec.get("clases_destacadas", []))),
                "Clases", f"Diagrama de clases ({len(cls)} clases)")
    if quiere("comunicacion_rica") and spec.get("comunicacion_rica"):
        for cid, d in spec["comunicacion_rica"].items():
            cu = CUd.get(cid, {"nombre": cid})
            guardar(f"{cid}_comunicacion_rica.svg",
                    comunicacion_rica(f"sd {cid}: {cu['nombre']} — comunicacion",
                                      d["actor"], d["nodos"], d["mensajes"],
                                      d.get("W", 1200), d.get("H", 700)),
                    "Comunicación", f"{cid}: {cu['nombre']} (rica)")
    return hechos


def exportar_png(out, hechos):
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("PNG omitido: instala playwright")
        return False
    os.makedirs(os.path.join(out, "png"), exist_ok=True)
    with sync_playwright() as p:
        br = p.chromium.launch()
        pg = br.new_page(viewport={"width": 1400, "height": 1000}, device_scale_factor=2)
        for _s, _t, arch in hechos:
            pg.goto("file:///" + os.path.abspath(os.path.join(out, arch)).replace("\\", "/"))
            pg.locator("svg").first.screenshot(path=os.path.join(out, "png", arch.replace(".svg", ".png")))
        br.close()
    return True


def main():
    try:
        sys.stdout.reconfigure(errors="replace")
    except Exception:
        pass
    ap = argparse.ArgumentParser()
    ap.add_argument("spec")
    ap.add_argument("salida")
    ap.add_argument("--solo")
    ap.add_argument("--png", action="store_true")
    a = ap.parse_args()
    spec, ACT, CU = cargar(a.spec)
    solo = set(a.solo.split(",")) if a.solo else None
    hechos = generar(spec, ACT, CU, a.salida, solo)
    ok = exportar_png(a.salida, hechos) if a.png else False
    print(f"{len(hechos)} diagramas en {a.salida}" + (" + png/" if ok else ""))
    for s, t, f in hechos:
        print(f"  - {f}")
    if AVISOS:
        print("\nAVISOS:")
        for m in dict.fromkeys(AVISOS):
            print("  *", m)


if __name__ == "__main__":
    main()
