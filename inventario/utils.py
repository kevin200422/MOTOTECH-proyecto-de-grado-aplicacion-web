from django.db import connection

def tabla_existe(tabla: str) -> bool:
    try:
        return tabla in connection.introspection.table_names()
    except Exception:
        return False
