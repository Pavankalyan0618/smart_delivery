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

def fetch_one(sql, params=None):
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(sql, params or ())
        return cur.fetchone()

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
        return False


# --- Admin helpers ---

def list_customers():
    return fetch_all("""
        SELECT customer_id, full_name, plan_name, is_active
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
    """Insert customer matching DB schema where phone column is named phone_number."""
    execute(
        """
        INSERT INTO customers (full_name, phone_number, address, plan_name, is_active)
        VALUES (%s, %s, %s, %s, %s);
        """,
        (full_name, phone or "", address, plan_name, is_active),
    )

def add_driver(full_name, phone):
    execute("""
        INSERT INTO drivers (full_name, phone)
        VALUES (%s, %s);
    """, (full_name, phone))

def create_assignment(assign_date, customer_id, driver_id, created_by=None):
    execute("""
        INSERT INTO assignments (assign_date, customer_id, driver_id, created_by)
        VALUES (%s, %s, %s, %s);
    """, (assign_date, customer_id, driver_id, created_by))

# --- Delivery helpers 

def list_assignments_for_date(assign_date):
    sql = """
    SELECT a.assignment_id, a.assign_date, a.customer_id, a.driver_id,
           c.full_name AS customer_name,
           d.full_name AS driver_name
    FROM assignments a
    JOIN customers c ON c.customer_id = a.customer_id
    JOIN drivers   d ON d.driver_id   = a.driver_id
    WHERE a.assign_date = %s
    ORDER BY c.full_name;
    """
    return fetch_all(sql, (assign_date,))


def upsert_delivery(assignment_id, delivery_date, status, marked_by=None):
    """Insert or update a delivery row for (assignment_id, delivery_date).
    Status is saved in lowercase to satisfy CHECK(status in ('delivered','missed'))."""
    sql = """
    INSERT INTO deliveries (assignment_id, delivery_date, status, marked_by)
    VALUES (%s, %s, LOWER(%s), %s)
    ON CONFLICT (assignment_id, delivery_date)
    DO UPDATE SET status    = EXCLUDED.status,
                  marked_by = COALESCE(EXCLUDED.marked_by, deliveries.marked_by);
    """
    execute(sql, (assignment_id, delivery_date, status, marked_by))

def copy_missed_to_date(prev_date, new_date):
    """Carry over yesterday's MISSED deliveries to a new date."""
    sql = """
    INSERT INTO deliveries (assignment_id, delivery_date, status, marked_by)
    SELECT d.assignment_id, %s, 'missed', NULL
    FROM deliveries d
    WHERE d.delivery_date = %s AND d.status = 'missed'
      AND NOT EXISTS (
        SELECT 1 FROM deliveries d2
        WHERE d2.assignment_id = d.assignment_id
          AND d2.delivery_date = %s
      );
    """
    execute(sql, (new_date, prev_date, new_date))


def delivery_kpis_for_date(delivery_date):
    sql = """
    SELECT
      COUNT(*) FILTER (WHERE status = 'delivered') AS delivered,
      COUNT(*) FILTER (WHERE status = 'missed')    AS missed,
      0::int                                       AS pending,
      COUNT(*)                                     AS total
    FROM deliveries
    WHERE delivery_date = %s;
    """
    row = fetch_one(sql, (delivery_date,))
    return row or {"delivered": 0, "missed": 0, "pending": 0, "total": 0}



