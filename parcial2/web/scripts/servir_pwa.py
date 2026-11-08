"""Servidor local de la compilación PWA con rutas de Angular.

Ejecutar desde parcial2/web: python scripts/servir_pwa.py
Solo escucha en localhost; no sustituye un servidor de producción.
"""
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit


class AngularHandler(SimpleHTTPRequestHandler):
    def send_head(self):
        ruta = urlsplit(self.path).path
        # Las rutas de la aplicación necesitan index.html al recargar con red.
        if ruta != '/' and not Path(ruta).suffix:
            self.path = '/index.html'
        return super().send_head()


if __name__ == '__main__':
    carpeta = Path(__file__).resolve().parent.parent / 'dist' / 'gangaclothes-web' / 'browser'
    if not (carpeta / 'index.html').is_file():
        raise SystemExit('Primero ejecuta npm run build -- --configuration production')
    servidor = ThreadingHTTPServer(('127.0.0.1', 4300), partial(AngularHandler, directory=str(carpeta)))
    print('PWA local: http://127.0.0.1:4300', flush=True)
    servidor.serve_forever()
