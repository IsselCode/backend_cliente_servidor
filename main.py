"""
Punto de entrada ASGI del backend.

Importa la fabrica de la aplicacion y expone `app` para que FastAPI/Uvicorn
puedan arrancar el servidor.
"""

from core.app.factory import create_app

app = create_app()
