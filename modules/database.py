"""Conexión PostgreSQL/Supabase para Camelia.

Mantiene una interfaz compatible con las consultas heredadas de SQLite para
poder migrar la aplicación gradualmente sin reescribir toda la UI de golpe.
"""
from __future__ import annotations

import os
from contextlib import contextmanager

import psycopg
import pandas as pd
import streamlit as st


class HybridRow(dict):
    """Fila compatible con row["campo"] y row[0]."""
    def __getitem__(self, key):
        if isinstance(key, int):
            return list(self.values())[key]
        return super().__getitem__(key)


def _hybrid_row_factory(cursor):
    """Crea filas híbridas solo cuando la consulta devuelve columnas.

    PostgreSQL no expone ``cursor.description`` en sentencias DDL como
    CREATE TABLE / CREATE INDEX. Psycopg invoca igualmente el row_factory al
    procesar esos resultados, por lo que debemos aceptar ``description=None``.
    """
    description = cursor.description or ()
    columns = [column.name for column in description]

    if not columns:
        def make_empty_row(values):
            return HybridRow()
        return make_empty_row

    def make_row(values):
        return HybridRow(zip(columns, values))

    return make_row


def database_url() -> str:
    """Obtiene la cadena PostgreSQL sin exponerla en GitHub."""
    try:
        return st.secrets["database"]["url"]
    except Exception:
        value = os.getenv("DATABASE_URL") or os.getenv("SUPABASE_DATABASE_URL")
        if value:
            return value
        raise RuntimeError(
            "Falta configurar [database] url en los Secrets de Streamlit."
        )


def _convert_placeholders(sql: str) -> str:
    """Convierte marcadores SQLite ? a PostgreSQL %s."""
    return sql.replace("?", "%s")


class PgCursorAdapter:
    def __init__(self, cursor):
        self._cursor = cursor

    @property
    def description(self):
        return self._cursor.description

    @property
    def rowcount(self):
        return self._cursor.rowcount

    def execute(self, sql, params=None):
        self._cursor.execute(_convert_placeholders(sql), params or ())
        return self

    def executemany(self, sql, params_seq):
        self._cursor.executemany(_convert_placeholders(sql), params_seq)
        return self

    def fetchone(self):
        return self._cursor.fetchone()

    def fetchall(self):
        return self._cursor.fetchall()

    def close(self):
        self._cursor.close()

    def __iter__(self):
        return iter(self._cursor)


class PgConnectionAdapter:
    """Adaptador DB-API para conservar el código heredado de la app."""
    def __init__(self, connection):
        self._connection = connection

    def cursor(self):
        return PgCursorAdapter(self._connection.cursor())

    def execute(self, sql, params=None):
        return self.cursor().execute(sql, params)

    def executemany(self, sql, params_seq):
        return self.cursor().executemany(sql, params_seq)

    def executescript(self, script):
        with self._connection.cursor() as cur:
            for statement in [part.strip() for part in script.split(";") if part.strip()]:
                cur.execute(statement)

    def commit(self):
        self._connection.commit()

    def rollback(self):
        self._connection.rollback()

    def close(self):
        self._connection.close()


@contextmanager
def db():
    raw = psycopg.connect(
        database_url(),
        row_factory=_hybrid_row_factory,
        autocommit=False,
        connect_timeout=15,
    )
    connection = PgConnectionAdapter(raw)
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def query_df(sql: str, params=None) -> pd.DataFrame:
    """Ejecuta una consulta SELECT y devuelve un DataFrame real.

    Esta función evita que pandas interprete las filas híbridas del adaptador
    como nombres de columnas. Se usa para todas las lecturas tabulares de la UI.
    """
    converted = _convert_placeholders(sql)
    with psycopg.connect(
        database_url(),
        autocommit=True,
        connect_timeout=15,
    ) as raw:
        with raw.cursor() as cur:
            cur.execute(converted, params or ())
            if cur.description is None:
                return pd.DataFrame()
            columns = [col.name for col in cur.description]
            rows = cur.fetchall()
    return pd.DataFrame(rows, columns=columns)


def query_one(sql: str, params=None):
    """Devuelve una fila híbrida para lecturas puntuales."""
    converted = _convert_placeholders(sql)
    with psycopg.connect(
        database_url(),
        row_factory=_hybrid_row_factory,
        autocommit=True,
        connect_timeout=15,
    ) as raw:
        with raw.cursor() as cur:
            cur.execute(converted, params or ())
            return cur.fetchone()

def init_db():
    """Crea/valida el esquema mínimo necesario en Supabase."""
    with db() as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS inventory(
          id BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
          category TEXT NOT NULL, subcategory TEXT NOT NULL,
          item_name TEXT NOT NULL, description TEXT DEFAULT '', quantity DOUBLE PRECISION NOT NULL DEFAULT 1,
          unit TEXT NOT NULL DEFAULT 'pieza(s)', brand TEXT DEFAULT '', condition_status TEXT DEFAULT 'Bueno',
          current_area TEXT DEFAULT '', expiration_date TEXT, lot_number TEXT DEFAULT '',
          estimated_unit_value DOUBLE PRECISION DEFAULT 0, destination TEXT NOT NULL DEFAULT 'Por definir',
          destination_detail TEXT DEFAULT '', transfer_status TEXT NOT NULL DEFAULT 'Pendiente',
          responsible_person TEXT DEFAULT '', transfer_date TEXT, notes TEXT DEFAULT '', photo BYTEA,
          photo_name TEXT DEFAULT '', created_at TEXT NOT NULL, updated_at TEXT NOT NULL, created_by TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS audit_log(
          id BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY, inventory_id BIGINT,
          action TEXT NOT NULL, detail TEXT DEFAULT '', user_name TEXT NOT NULL, created_at TEXT NOT NULL,
          CONSTRAINT audit_log_inventory_fk FOREIGN KEY (inventory_id)
            REFERENCES inventory(id) ON DELETE SET NULL
        );
        CREATE TABLE IF NOT EXISTS item_locations(
          id BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY, inventory_id BIGINT NOT NULL,
          area_name TEXT NOT NULL, quantity DOUBLE PRECISION NOT NULL DEFAULT 0,
          CONSTRAINT item_locations_inventory_fk FOREIGN KEY (inventory_id)
            REFERENCES inventory(id) ON DELETE CASCADE,
          UNIQUE(inventory_id, area_name)
        );
        CREATE TABLE IF NOT EXISTS item_destinations(
          id BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY, inventory_id BIGINT NOT NULL,
          destination_name TEXT NOT NULL, quantity DOUBLE PRECISION NOT NULL DEFAULT 0,
          CONSTRAINT item_destinations_inventory_fk FOREIGN KEY (inventory_id)
            REFERENCES inventory(id) ON DELETE CASCADE,
          UNIQUE(inventory_id, destination_name)
        );
        CREATE INDEX IF NOT EXISTS idx_inventory_updated_at ON inventory(updated_at);
        CREATE INDEX IF NOT EXISTS idx_locations_inventory_id ON item_locations(inventory_id);
        CREATE INDEX IF NOT EXISTS idx_destinations_inventory_id ON item_destinations(inventory_id);
        CREATE INDEX IF NOT EXISTS idx_audit_inventory_id ON audit_log(inventory_id);
        """)


def healthcheck() -> dict:
    """Verificación pequeña para diagnóstico desde la app o terminal."""
    with db() as conn:
        result = {}
        for table in ("inventory", "audit_log", "item_locations", "item_destinations"):
            row = conn.execute(f"SELECT COUNT(*) AS total FROM {table}").fetchone()
            result[table] = int(row["total"])
        return result
