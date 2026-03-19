import os
from app import create_app

# Crea la aplicación con la configuración de producción
app = create_app('production')

if __name__ == "__main__":
    app.run()
