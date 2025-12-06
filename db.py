import streamlit as st
import psycopg2
from psycopg2.extras import RealDictCursor

# -------------------------------
# DATABASE CONNECTION
# -------------------------------
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

# -------------------------------
# HEALTH CHECK
# -------------------------------
def db_healthcheck():
    try:
        fetch_one("SELECT 1;")
        return True
    except:
        return False

# -------------------------------
# CUSTOMER FUNCTIONS
# -------------------------------
def list_customers():
    return fetch_all("""
        SELECT customer_id, full_name, phone_number, address, plan_name,
               location, owed, subscription_start, subscription_days
        FROM customers
        ORDER BY customer_id;
    """)

def add_customer(full_name, phone, address, plan_name, location, subscription_start, subscription_days):
    execute("""
        INSERT INTO customers (full_name, phone_number, address, plan_name, location,
                               subscription_start, subscription_days)
        VALUES (%s, %s, %s, %s, %s, %s, %s);
    """, (full_name, phone or "", address, plan_name, location, subscription_start, subscription_days))

def update_customer(customer_id, full_name, phone, address, plan_name, location, subscription_start, subscription_days):
    execute("""
        UPDATE customers
        SET full_name = %s,
            phone_number = %s,
            address = %s,
            plan_name = %s,
            location = %s,
            subscription_start = %s,
            subscription_days = %s
        WHERE customer_id = %s;
    """, (full_name, phone or "", address, plan_name, location, subscription_start, subscription_days, customer_id))

# -------------------------------
# RENEWAL (NETFLIX R1 MODEL)
# -------------------------------
def renew_subscription(customer_id, extra_days):
    from datetime import date
    today = date.today()

    row = fetch_one("SELECT owed FROM customers WHERE customer_id = %s;", (customer_id,))
    if not row:
        raise ValueError("Customer not found.")
    if row["owed"] > 0:
        raise ValueError("Cannot renew: customer has pending owed deliveries.")

    execute("""
        UPDATE customers
        SET subscription_start = %s,
            subscription_days = %s,
            owed = 0
        WHERE customer_id = %s;
    """, (today, extra_days, customer_id))

def delete_customer(customer_id):
    execute("DELETE FROM deliveries WHERE assignment_id IN (SELECT assignment_id FROM assignments WHERE customer_id = %s);", (customer_id,))
    execute("DELETE FROM assignments WHERE customer_id = %s;", (customer_id,))
    execute("DELETE FROM customers WHERE customer_id = %s;", (customer_id,))

# -------------------------------
# DRIVER FUNCTIONS
# -------------------------------
def list_drivers():
    return fetch_all("""
        SELECT driver_id, full_name, phone
        FROM drivers
        ORDER BY full_name;
    """)

def add_driver(full_name, phone):
    row = fetch_all("""
        INSERT INTO drivers (full_name, phone)
        VALUES (%s, %s)
        RETURNING driver_id;
    """, (full_name, phone))
    return row[0]["driver_id"]

def delete_driver(driver_id):
    """Fully delete a driver and all linked records including user account."""

    # 1. Delete deliveries for this driver's assignments
    execute("""
        DELETE FROM deliveries
        WHERE assignment_id IN (
            SELECT assignment_id FROM assignments WHERE driver_id = %s
        );
    """, (driver_id,))

    # 2. Delete assignments
    execute("""
        DELETE FROM assignments
        WHERE driver_id = %s;
    """, (driver_id,))

    # 3. Delete linked user
    execute("""
        DELETE FROM users
        WHERE driver_id = %s;
    """, (driver_id,))

    # 4. Delete driver
    execute("""
        DELETE FROM drivers
        WHERE driver_id = %s;
    """, (driver_id,))

def create_driver_user(username, password, driver_id):
    execute("""
        INSERT INTO users (username, password, role, driver_id)
        VALUES (%s, %s, 'driver', %s);
    """, (username, password, driver_id))

# -------------------------------
# ASSIGNMENTS
# -------------------------------
def create_assignment(assign_date, customer_id, driver_id, created_by=None):
    execute("""
        INSERT INTO assignments (assign_date, customer_id, driver_id, created_by)
        VALUES (%s, %s, %s, %s);
    """, (assign_date, customer_id, driver_id, created_by))

def delete_assignment(assignment_id):
    execute("DELETE FROM assignments WHERE assignment_id = %s;", (assignment_id,))

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

# -------------------------------
# DELIVERY + OWED LOGIC
# -------------------------------
def pause_delivery_for_customer(customer_id, pause_date, marked_by=None):
    row = fetch_one("""
        SELECT assignment_id
        FROM assignments
        WHERE customer_id = %s AND assign_date = %s
        LIMIT 1;
    """, (customer_id, pause_date))

    if not row:
        raise ValueError("No assignment exists for this customer on the selected date.")

    assignment_id = row["assignment_id"]

    execute("""
        INSERT INTO deliveries (assignment_id, delivery_date, status, marked_by)
        VALUES (%s, %s, 'paused', %s)
        ON CONFLICT (assignment_id, delivery_date)
        DO UPDATE SET status='paused', marked_by = excluded.marked_by;
    """, (assignment_id, pause_date, marked_by))

def upsert_delivery(assignment_id, delivery_date, status, marked_by=None):
    execute("""
        INSERT INTO deliveries (assignment_id, delivery_date, status, marked_by)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (assignment_id, delivery_date)
        DO UPDATE SET status = excluded.status, marked_by = excluded.marked_by;
    """, (assignment_id, delivery_date, status, marked_by))

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

    if old_status is None:
        if new_status == "missed":
            owed += 1
    else:
        if old_status == "missed" and new_status == "delivered":
            owed = max(0, owed - 1)
        elif old_status == "delivered" and new_status == "missed":
            owed += 1

    execute("""
        UPDATE customers
        SET owed = %s
        WHERE customer_id = %s;
    """, (owed, customer_id))

# -------------------------------
# KPIs
# -------------------------------
def delivery_kpis_for_date(delivery_date):
    return fetch_one("""
        SELECT
          COUNT(*) FILTER (WHERE status='delivered') AS delivered,
          COUNT(*) FILTER (WHERE status='missed') AS missed,
          COUNT(*) FILTER (WHERE status NOT IN ('delivered','missed')) AS pending,
          COUNT(*) AS total
        FROM deliveries
        WHERE delivery_date = %s;
    """, (delivery_date,))

# -------------------------------
# AUTH
# -------------------------------
def authenticate_user(username, password):
    return fetch_one("""
        SELECT user_id, username, role, driver_id
        FROM users
        WHERE username = %s AND password = %s;
    """, (username, password))