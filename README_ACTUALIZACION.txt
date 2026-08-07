CAMELIA V12 - SUPABASE NATIVO - BUILD 2026-08-07.3

CAMBIO PRINCIPAL
- Todas las lecturas tabulares usan query_df() nativo de PostgreSQL.
- Corrige el problema donde la app mostraba 106 registros pero quantity=0 y textos como "category" o "item_name".
- Conserva escritura, edición, borrado, fotos, ubicaciones, destinos, historial, PDF, Excel y respaldos.
- No requiere volver a migrar los datos.

PARA GITHUB
1. Reemplaza app.py.
2. Reemplaza modules/database.py.
3. Conserva los demás archivos y assets.
4. Haz Commit changes.
5. En Streamlit no cambies Secrets.

VALIDACION ESPERADA
- Registros: 106.
- Unidades: debe mostrar la suma real de quantity.
- Valor estimado: debe mostrar la suma real.
- Categorías: deben aparecer nombres reales.
- Artículos: deben mostrar item_name reales.

Si aparece la leyenda "Camelia V12 · 2026-08-07.3 · Supabase nativo", Streamlit ya está ejecutando esta build.
