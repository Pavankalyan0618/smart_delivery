import streamlit as st
import psycopg2
from psycopg2.extras import RealDictCursor
from psycopg2 import errors
import logging

# ---------- Database connection ----------
def get_conn():
    return psycopg2.connect(
        host=st.secrets["DB_HOST"],
        dbname=st.secrets["DB_NAME"],
        user=st.secrets["DB_USER"],
        password=st.secrets["DB_PASSWORD"],
        sslmode=st.secrets["DB_SSLMODE"],
        cursor_factory=RealDictCursor
    )

# ---------- Helper functions ----------
def fetch_all(sql, params=None):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params or ())
            return cur.fetchall()

def fetch_one(sql, params=None):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params or ())
            return cur.fetchone()

def execute(sql, params=None):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params or ())
            conn.commit()

# ---------- Healthcheck ----------
def db_healthcheck():
    try:
        result = fetch_one("SELECT 1 AS ok;")
        return bool(result)
    except Exception as e:
        logging.error(f"DB healthcheck failed: {e}")
        return False

# ---------- Admin functions ----------
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
    execute("""
        INSERT INTO customers (full_name, phone_number, address, plan_name, is_active)
        VALUES (%s, %s, %s, %s, %s);
    """, (full_name, phone or "", address, plan_name, is_active))

def add_driver(full_name, phone):
    execute("""
        INSERT INTO drivers (full_name, phone)
        VALUES (%s, %s);
    """, (full_name, phone))

def create_assignment(assign_date, customer_id, driver_id, created_by=None):
    try:
        execute("""
            INSERT INTO assignments (assign_date, customer_id, driver_id, created_by)
            VALUES (%s, %s, %s, %s);
            """, (assign_date, customer_id, driver_id, created_by))
    except psycopg2.errors.UniqueViolation:
            raise ValueError("This customer already has an assignment")
    except Exception as e:
        raise   
            

def update_owed_deliveries(customer_id, status):
    row = fetch_one("SELECT owed FROM customers WHERE customer_id = %s;", (customer_id,))
    owed = (row["owed"] if row else 0) or 0

    # 🔍 Prevent duplicate owed increments
    existing = fetch_one("""
        SELECT 1 FROM deliveries d
        JOIN assignments a ON d.assignment_id = a.assignment_id
        WHERE a.customer_id = %s AND d.status = 'missed'
        AND d.delivery_date = CURRENT_DATE;
    """, (customer_id,))

    if status == "missed" and not existing:
        owed += 1
    elif status == "delivered" and owed > 0:
        owed -= 1

    execute("UPDATE customers SET owed = %s WHERE customer_id = %s;", (owed, customer_id))


# ---------- Delivery functions ----------
def list_assignments_for_date(assign_date):
    return fetch_all("""
        SELECT a.assignment_id, a.customer_id, c.full_name AS customer_name,
               a.driver_id, d.full_name AS driver_name
        FROM assignments a
        JOIN customers c ON a.customer_id = c.customer_id
        JOIN drivers d ON a.driver_id = d.driver_id
        WHERE a.assign_date = %s
        ORDER BY c.full_name;
    """, (assign_date,))

def upsert_delivery(assignment_id, delivery_date, status, marked_by=None):
    execute("""
        INSERT INTO deliveries (assignment_id, delivery_date, status, marked_by)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (assignment_id, delivery_date)
        DO UPDATE SET status = excluded.status, marked_by = excluded.marked_by;
    """, (assignment_id, delivery_date, status, marked_by))

def copy_missed_to_date(prev_date, new_date):
    execute("""
        INSERT INTO deliveries (assignment_id, delivery_date, status, marked_by)
        SELECT assignment_id, %s, 'missed', marked_by
        FROM deliveries
        WHERE delivery_date = %s AND status = 'missed'
        AND assignment_id NOT IN (
            SELECT assignment_id FROM deliveries WHERE delivery_date = %s
        );
    """, (new_date, prev_date, new_date))

def delivery_kpis_for_date(delivery_date):
    return fetch_one("""
        SELECT
          COUNT(*) FILTER (WHERE status = 'delivered') AS delivered,
          COUNT(*) FILTER (WHERE status = 'missed') AS missed,
          COUNT(*) FILTER (WHERE status NOT IN ('delivered','missed')) AS pending,
          COUNT(*) AS total
        FROM deliveries
        WHERE delivery_date = %s;
    """, (delivery_date,))

# ---------- Authentication ----------
def authenticate_user(username, password):
    sql = """
    SELECT u.user_id, u.username, u.role, d.driver_id
    FROM users u
    LEFT JOIN drivers d ON d.user_id = u.user_id
    WHERE u.username = %s AND u.password_hash = %s;
    """
    result = fetch_one(sql, (username, password))
    print("DEBUG LOGIN:", username, password, "=>", result)
    return result
