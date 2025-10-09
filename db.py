import streamlit as st
import psycopg2
from psycopg2.extras import RealDictCursor
import logging

def get_conn():
    return psycopg2.connect(
        host=st.secrets["DB_HOST"],
        dbname=st.secrets["DB_NAME"],
        user=st.secrets["DB_USER"],
        password=st.secrets["DB_PASSWORD"],
        sslmode=st.secrets["DB_SSLMODE"],
        cursor_factory=RealDictCursor
    )

def fetch_all(sql, params=None):
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(sql, params or ())
        return cur.fetchall()

def execute(sql, params=None):
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(sql, params or ())
        conn.commit()


# --- Healthcheck helper ---

def db_healthcheck():
    """Return True if the database is reachable and responds to SELECT 1."""
    try:
        with get_conn() as conn, conn.cursor() as cur:
            cur.execute("SELECT 1 AS ok;")
            row = cur.fetchone()
            if row is None:
                return False
            # RealDictCursor returns a dict; fall back if it's a tuple
            try:
                val = next(iter(row.values()))
            except AttributeError:
                val = row[0]
            return val == 1
    except Exception:
        # Keep this silent for UI; detailed logging can be added if needed
        return False




 # --- Admin helpers ---

def list_customers():
    return fetch_all("""
        SELECT customer_id, full_name, phone, plan_name, is_active
        FROM customers
        ORDER BY full_name;
    """)

def list_drivers():
    return fetch_all("""
        SELECT driver_id, full_name, phone
        FROM drivers
        ORDER BY full_name;
    """)

def add_customer(full_name, phone, address, plan_name, is_active=True):
    execute("""
        INSERT INTO customers (full_name, phone, address, plan_name, is_active)
        VALUES (%s, %s, %s, %s, %s);
    """, (full_name, phone, address, plan_name, is_active))

def add_driver(full_name, phone):
    execute("""
        INSERT INTO drivers (full_name, phone)
        VALUES (%s, %s);
    """, (full_name, phone))

def create_assignment(assign_date, customer_id, driver_id, created_by='admin'):
    execute("""
        INSERT INTO assignments (assign_date, customer_id, driver_id, created_by)
        VALUES (%s, %s, %s, %s);
    """, (assign_date, customer_id, driver_id, created_by))       