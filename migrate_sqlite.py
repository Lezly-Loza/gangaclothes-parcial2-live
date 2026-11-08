import sqlite3

for db_path in [r'ganga_saas.db', r'parcial2\backend\ganga_saas.db']:
    try:
        con = sqlite3.connect(db_path)
        cur = con.cursor()
        cur.execute("ALTER TABLE tenants ADD COLUMN plazo_cambio_dias INTEGER DEFAULT 7")
        con.commit()
        print(f"Added plazo_cambio_dias to {db_path}")
        con.close()
    except Exception as e:
        print(f"{db_path}: {e}")
