from app.core.database import SessionLocal
from app.models import Tenant, Sucursal, PlanSuscripcion, User, Categoria, Producto, Variante, Inventario, Venta, Reserva, Proveedor, BitacoraSeguridad

db = SessionLocal()
print("=== PLANES ===")
for p in db.query(PlanSuscripcion).all():
    print(f"ID {p.id}: {p.nombre} ({p.codigo}) - max_sucursales: {p.max_sucursales}, max_usuarios: {p.max_usuarios}")

print("\n=== TENANTS ===")
for t in db.query(Tenant).all():
    plan = db.query(PlanSuscripcion).filter_by(id=t.plan_suscripcion_id).first()
    plan_nombre = plan.nombre if plan else "Sin plan"
    sucs = db.query(Sucursal).filter_by(tenant_id=t.id).all()
    print(f"Tenant ID {t.id}: {t.codigo} - {t.razon_social} | Plan: {plan_nombre} | Sucursales: {[s.nombre for s in sucs]}")

print("\n=== RESUMEN POR TENANT ===")
for t in db.query(Tenant).all():
    prods = db.query(Producto).filter_by(tenant_id=t.id).count()
    vars_ = db.query(Variante).filter_by(tenant_id=t.id).count()
    invs = db.query(Inventario).filter_by(tenant_id=t.id).count()
    ventas = db.query(Venta).filter_by(tenant_id=t.id).count()
    reservas = db.query(Reserva).filter_by(tenant_id=t.id).count()
    provs = db.query(Proveedor).filter_by(tenant_id=t.id).count()
    users = db.query(User).filter_by(tenant_id=t.id).count()
    logs = db.query(BitacoraSeguridad).filter_by(tenant_id=t.id).count()
    print(f"[{t.codigo}] Productos: {prods}, Variantes: {vars_}, Inventarios: {invs}, Ventas: {ventas}, Reservas: {reservas}, Proveedores: {provs}, Usuarios: {users}, Bitácora: {logs}")
