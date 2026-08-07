# Camelia V12 Modular · Supabase

Esta versión conserva la aplicación actual, pero separa las dos piezas más
sensibles en módulos: **conexión a Supabase** y **autenticación**.

## Estructura

```text
app.py
requirements.txt
modules/
  database.py
  auth.py
  inventory.py
  dashboard.py
  reports.py
  backup.py
  audit.py
  utils.py
.streamlit/
  secrets.toml.example
```

## Streamlit Secrets

En Streamlit Cloud > Manage app > Settings > Secrets agrega:

```toml
[database]
url = "TU CADENA SESSION POOLER COMPLETA"
```

Nunca subas la contraseña real a GitHub.

## Despliegue de prueba

1. Sube todos los archivos y la carpeta `modules` a tu repositorio de prueba.
2. En Streamlit selecciona `app.py` como Main file path.
3. Configura el Secret anterior.
4. Prueba Administrador, Camelia e Invitado.
5. Verifica que aparezcan tus 106 artículos y fotografías.
6. Crea un artículo de prueba, reinicia la app y confirma que persista.

## Importante

`camelia_inventory.db` ya no es la base principal. SQLite se conserva únicamente
para las funciones de importación/exportación de respaldo que todavía existen en
la interfaz actual.

La modularización se hará por etapas para evitar romper una aplicación que ya
está operativa. La siguiente etapa será extraer inventario y reportes.
