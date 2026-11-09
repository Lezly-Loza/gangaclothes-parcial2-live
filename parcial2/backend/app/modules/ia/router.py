"""Módulo de Inteligencia Artificial y Asistente de Compras Multitenant (CU-28)."""
import json
import os
import urllib.request
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ...core.database import TenantScope
from ...core.deps import get_db, require_tenant
from ...models import Categoria, Color, Inventario, Producto, Talla, Variante
from ..productos.promociones import precio_promocional

router = APIRouter(prefix="/ia", tags=["Inteligencia Artificial y Asistente"])


class ChatIn(BaseModel):
    mensaje: str = Field(min_length=1, max_length=1000)
    conversacion_id: int | None = None
    origen: str | None = None
    sucursal_id: int | None = None


@router.get("/estado")
def estado():
    clave = os.environ.get("GEMINI_API") or os.environ.get("GEMINI_API_KEY")
    return {
        "motor": "gemini" if clave else "sin_modelo",
        "modelo": os.environ.get("GEMINI_MODELO", "gemini-flash-latest") if clave else None,
        "disponible": True,
    }


@router.post("/chat")
def chat(body: ChatIn, scope: TenantScope = Depends(require_tenant), db: Session = Depends(get_db)):
    tid = scope.tenant_id
    productos = db.query(Producto).filter_by(tenant_id=tid, activo=True).all()

    sugerencias = []
    for p in productos:
        cat = db.query(Categoria).filter_by(tenant_id=tid, id=p.categoria_id).first() if p.categoria_id else None
        variantes = db.query(Variante).filter_by(tenant_id=tid, producto_id=p.id, activo=True).all()

        tallas = set()
        colores = set()
        for v in variantes:
            if v.talla_id:
                t = db.query(Talla).filter_by(tenant_id=tid, id=v.talla_id).first()
                if t:
                    tallas.add(t.nombre)
            if v.color_id:
                c = db.query(Color).filter_by(tenant_id=tid, id=v.color_id).first()
                if c:
                    colores.add(c.nombre)

        precio_final, promo = precio_promocional(db, tid, p.id, p.precio_base)
        sugerencias.append({
            "id": p.id,
            "nombre": p.nombre,
            "precio": float(precio_final),
            "categoria": cat.nombre if cat else "Prendas",
            "colores_disponibles": sorted(list(colores)) or ["Estándar"],
            "tallas_disponibles": sorted(list(tallas)) or ["Única"],
            "promocion": promo.get("nombre") if promo else None,
            "por_que_se_sugiere": f"Prenda destacada de {cat.nombre if cat else 'temporada'}",
        })

    msg = body.mensaje.lower()
    palabras = [w for w in msg.split() if len(w) > 3]
    prendas_filtradas = [
        s for s in sugerencias
        if any(w in s["nombre"].lower() or (s["categoria"] and w in s["categoria"].lower()) for w in palabras)
    ]
    if not prendas_filtradas:
        prendas_filtradas = sugerencias[:4]
    else:
        prendas_filtradas = prendas_filtradas[:4]

    clave = os.environ.get("GEMINI_API") or os.environ.get("GEMINI_API_KEY")
    modo = "sin_modelo"
    respuesta_texto = ""

    if clave:
        try:
            modelo = os.environ.get("GEMINI_MODELO", "gemini-flash-latest")
            cuerpo = {
                "systemInstruction": {
                    "parts": [{
                        "text": (
                            "Eres el Asistente de compras virtual de una tienda de ropa exclusiva. "
                            "Habla en español boliviano de manera amable, cordial y concisa. "
                            "Recomienda amablemente las prendas disponibles dadas en los datos, mencionando sus precios en Bs."
                        )
                    }]
                },
                "contents": [{
                    "role": "user",
                    "parts": [{
                        "text": json.dumps({"pregunta": body.mensaje, "prendas_disponibles": prendas_filtradas}, ensure_ascii=False)
                    }]
                }],
                "generationConfig": {"temperature": 0.4, "maxOutputTokens": 350}
            }
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{modelo}:generateContent"
            req = urllib.request.Request(
                url, data=json.dumps(cuerpo).encode("utf-8"),
                headers={"Content-Type": "application/json", "x-goog-api-key": clave},
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.load(resp)
            parts = data.get("candidates", [{}])[0].get("content", {}).get("parts", [])
            texto = "\n".join(p.get("text", "") for p in parts).strip()
            if texto:
                respuesta_texto = texto
                modo = "gemini"
        except Exception:
            modo = "sin_modelo"

    if not respuesta_texto:
        nombres = ", ".join(f"'{p['nombre']}' (Bs {p['precio']:.2f})" for p in prendas_filtradas[:2])
        respuesta_texto = (
            f"¡Hola! Te recomiendo especialmente nuestras opciones destacadas: {nombres}. "
            "Podés probarlas en el vestidor virtual o reservarlas para tu visita a la sucursal."
        )

    return {
        "conversacion_id": body.conversacion_id or 1,
        "titulo": "Recomendaciones de compra",
        "respuesta": respuesta_texto,
        "modo": modo,
        "consultas": [{"herramienta": "buscar_prendas", "argumentos": {"mensaje": body.mensaje}}],
        "prendas": prendas_filtradas,
    }


@router.get("/conversaciones")
def listar_conversaciones():
    return []


@router.get("/conversaciones/{id}")
def obtener_conversacion(id: int):
    return {"id": id, "mensajes": []}


@router.delete("/conversaciones/{id}")
def borrar_conversacion(id: int):
    return {"ok": True, "conversacion_id": id}
