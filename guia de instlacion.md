# Guía rápida: ejecutar Taller Mecánico en otra máquina usando VS Code

Pensada para que un tercero levante el proyecto sin conocerlo.

## Requisitos
- Python 3.10 o superior con `pip`.
- (Opcional) Git para clonar.
- Visual Studio Code (o cualquier editor) con acceso a una terminal.

## Pasos en VS Code (Windows, macOS o Linux)
1) Abre VS Code y selecciona **File > Open Folder** sobre la carpeta `taller_mecanico`.
2) Abre la terminal integrada (View > Terminal) y crea un entorno virtual:
   - Windows PowerShell: `python -m venv .venv; .\\.venv\\Scripts\\Activate.ps1`
   - macOS/Linux: `python3 -m venv .venv && source .venv/bin/activate`
3) Instala dependencias: `pip install -r requirements.txt`
4) Ejecuta migraciones: `python manage.py migrate`
5) (Opcional) Crea un superusuario para el admin: `python manage.py createsuperuser`
6) Levanta el servidor de desarrollo: `python manage.py runserver`
7) Abre el navegador en `http://localhost:8000/`

## Notas rápidas
- La base es SQLite; no requiere configuración adicional.
- Si accederás desde otra IP/host, agrega ese host en `ALLOWED_HOSTS` dentro de `taller_mecanico/settings.py`.
- Para parar el servidor, usa `Ctrl+C` en la terminal.
