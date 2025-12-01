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
        SELECT 
            customer_id, full_name, phone_number, address, plan_name, is_active, location, owed, subscription_start,
            subscription_days, subscription_end
        FROM customers
        ORDER BY customer_id;
    """)

def list_drivers():
    return fetch_all("""
        SELECT driver_id, full_name, phone
        FROM drivers
        ORDER BY full_name;
    """)

def add_customer(full_name, phone, address, plan_name, is_active, location, subscription_start, subscription_days):
    execute("""
        INSERT INTO customers (full_name, phone_number, address, plan_name, is_active, location, subscription_start, subscription_days)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s);
    """, (full_name, phone or "", address, plan_name, is_active, location, subscription_start, subscription_days))

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
            

def update_owed_deliveries(assignment_id, customer_id, new_status, delivery_date):
    row = fetch_one("SELECT owed FROM customers WHERE customer_id = %s;", (customer_id,))
    owed = row["owed"] if row else 0

    existing = fetch_one("""
        SELECT status
        FROM deliveries
        WHERE assignment_id = %s AND delivery_date = %s
        LIMIT 1;
    """, (assignment_id, delivery_date))

    old_status = existing["status"] if existing else None


    # ---  owed logic ---
    if old_status is None:
        if new_status == "missed":
            owed += 1
    else:
        if old_status == "missed" and new_status == "missed":
            pass
        
        elif old_status == "missed" and new_status == "delivered":
            if owed > 0:
                owed -= 1

        elif old_status == "delivered" and new_status == "missed":
            owed += 1

    
    execute("""UPDATE customers SET owed = %s,
                subscription_end = subscription_start + (subscription_days + %s) * INTERVAL '1 day' 
             WHERE customer_id = %s;
             """,  (owed, owed, customer_id))

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
