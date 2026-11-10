"""Generador del PDF del comprobante de venta (CU15/17)."""
import io
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle


def generar_pdf_comprobante(datos: dict) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )

    styles = getSampleStyleSheet()
    titulo_style = ParagraphStyle(
        'TituloComprobante',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=18,
        leading=22,
        textColor=colors.HexColor('#ed0b56')
    )
    subtitulo_style = ParagraphStyle(
        'SubtituloComprobante',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#475569')
    )
    celda_bold = ParagraphStyle(
        'CeldaBold',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9,
        leading=12
    )
    celda_normal = ParagraphStyle(
        'CeldaNormal',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=12
    )

    story = []

    # Encabezado con Logo y Datos de Tienda
    empresa = datos.get('empresa') or 'GangaClothes SaaS'
    sucursal = datos.get('sucursal') or {}
    sucursal_nombre = sucursal.get('nombre') or 'Sucursal Principal'
    sucursal_dir = sucursal.get('direccion') or 'Bolivia'

    header_data = [
        [
            Paragraph(f"<b>GANGA</b><font color='#ed0b56'><b>CLOTHES</b></font><br/><font size=9 color='#64748b'>{empresa}</font>", titulo_style),
            Paragraph(f"<b>COMPROBANTE DE VENTA</b><br/><b>N°:</b> {datos.get('codigo', '—')}<br/><b>Fecha:</b> {datos.get('fecha_formateada', '—')}", subtitulo_style)
        ]
    ]
    t_header = Table(header_data, colWidths=[300, 240])
    t_header.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
    ]))
    story.append(t_header)
    story.append(Spacer(1, 10))

    # Datos de la sucursal y del cliente
    cliente = datos.get('cliente') or {}
    cliente_nombre = cliente.get('nombre') or 'Cliente General'
    cliente_doc = cliente.get('documento') or '—'
    cajero = datos.get('cajero') or {}
    cajero_nombre = cajero.get('nombre') or (cajero.get('email') if cajero else 'Sistema en línea')

    info_data = [
        [
            Paragraph(f"<b>Sucursal:</b> {sucursal_nombre}<br/><b>Dirección:</b> {sucursal_dir}<br/><b>Atendido por:</b> {cajero_nombre}", celda_normal),
            Paragraph(f"<b>Cliente:</b> {cliente_nombre}<br/><b>Documento:</b> {cliente_doc}<br/><b>Forma de Pago:</b> {datos.get('forma_pago', 'Contado')}", celda_normal)
        ]
    ]
    t_info = Table(info_data, colWidths=[270, 270])
    t_info.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F8FAFC')),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#E2E8F0')),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('LEFTPADDING', (0, 0), (-1, -1), 10),
        ('RIGHTPADDING', (0, 0), (-1, -1), 10),
    ]))
    story.append(t_info)
    story.append(Spacer(1, 15))

    # Tabla de Items
    items_header = [
        Paragraph("<b>PRENDA / DESCRIPCIÓN</b>", celda_bold),
        Paragraph("<b>TALLA / COLOR</b>", celda_bold),
        Paragraph("<b>CANT.</b>", celda_bold),
        Paragraph("<b>P. UNIT.</b>", celda_bold),
        Paragraph("<b>SUBTOTAL</b>", celda_bold)
    ]
    tabla_items_data = [items_header]

    for item in datos.get('items', []):
        tabla_items_data.append([
            Paragraph(str(item.get('prenda', '—')), celda_normal),
            Paragraph(f"{item.get('talla', '—')} / {item.get('color', '—')}", celda_normal),
            Paragraph(str(item.get('cantidad', 1)), celda_normal),
            Paragraph(f"Bs {float(item.get('precio_unitario', 0)):.2f}", celda_normal),
            Paragraph(f"Bs {float(item.get('subtotal', 0)):.2f}", celda_bold),
        ])

    t_items = Table(tabla_items_data, colWidths=[200, 110, 50, 90, 90])
    t_items.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1E293B')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
        ('TOPPADDING', (0, 0), (-1, 0), 6),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
        ('ALIGN', (2, 1), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F8FAFC')]),
    ]))
    story.append(t_items)
    story.append(Spacer(1, 12))

    # Totales
    total = float(datos.get('total', 0))
    descuento = float(datos.get('descuento', 0))
    subtotal = total + descuento

    totales_data = [
        ["", Paragraph("<b>Subtotal:</b>", celda_normal), Paragraph(f"Bs {subtotal:.2f}", celda_normal)],
        ["", Paragraph("<b>Descuento:</b>", celda_normal), Paragraph(f"- Bs {descuento:.2f}", celda_normal)],
        ["", Paragraph("<b>TOTAL PAGADO:</b>", celda_bold), Paragraph(f"<b>Bs {total:.2f}</b>", celda_bold)],
    ]
    t_totales = Table(totales_data, colWidths=[330, 110, 100])
    t_totales.setStyle(TableStyle([
        ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('LINEABOVE', (1, 2), (2, 2), 1, colors.HexColor('#ed0b56')),
    ]))
    story.append(t_totales)
    story.append(Spacer(1, 20))

    # Nota al pie
    nota_style = ParagraphStyle(
        'NotaPie',
        parent=styles['Normal'],
        fontName='Helvetica-Oblique',
        fontSize=8,
        leading=10,
        textColor=colors.HexColor('#94A3B8'),
        alignment=1  # Centrado
    )
    story.append(Paragraph("Este documento es un comprobante de entrega y compra generado por GangaClothes SaaS.<br/>No tiene validez como factura fiscal. ¡Gracias por su preferencia!", nota_style))

    doc.build(story)
    return buffer.getvalue()

