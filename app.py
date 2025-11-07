import streamlit as st
from datetime import date, datetime
from db import (
    list_customers, list_drivers,
    add_customer, add_driver, create_assignment,
    db_healthcheck,
    list_assignments_for_date, upsert_delivery, copy_missed_to_date, delivery_kpis_for_date
)

st.set_page_config(page_title="Smart Delivery", layout="wide")
st.title("Smart Delivery System")

tabs = st.tabs(["Admin", "Driver", "Dashboard"])

# Sidebar diagnostics (always visible)
st.sidebar.title("Diagnostics")
if st.sidebar.button("DB Ping"):
    st.sidebar.write("DB reachable:", db_healthcheck())

def plan_hits(d, plan):
    p = (plan or "").strip().lower()
    if p == "daily": return True
    if p in ("weekday","weekdays"): return dow_str(d) in WEEKDAYS[:5]
    if not p: return False
    return dow_str(d) in [x.strip() for x in p.split(",") if x.strip()]

def in_window(d, s, e):
    return (not s or d >= s) and (not e or d <= e)

def after_pause(d, p):
    return (not p) or (d > p)

def schedule_today(target=None):
    d = parse_date(target).date() if target else date.today()
    cs = fetchall("""
      SELECT c.customer_id, c.plan, c.start_date, c.end_date, c.pause_until, COALESCE(c.owed,0) owed,
             a.driver_id
      FROM customers c LEFT JOIN assignments a ON a.customer_id=c.customer_id
    """)
    existing = {r["customer_id"] for r in fetchall(
        "SELECT customer_id FROM deliveries WHERE date=:d", {"d": d}
    )}
    added = 0
    for c in cs:
        if in_window(d, c["start_date"], c["end_date"]) and after_pause(d, c["pause_until"]):
            if plan_hits(d, c["plan"]) or (c["owed"]>0):
                if c["customer_id"] not in existing:
                    execute("""
                      INSERT INTO deliveries(date,customer_id,driver_id,status,notes)
                      VALUES(:d,:cid,:did,'pending','')
                    """, {"d": d, "cid": c["customer_id"], "did": c["driver_id"]})
                    added += 1
    return added

def write_kpis(target=None):
    d = parse_date(target).date() if target else date.today()
    rows = fetchall("SELECT status FROM deliveries WHERE date=:d", {"d": d})
    total = len(rows)
    delivered = sum(1 for r in rows if r["status"]=="delivered")
    missed = sum(1 for r in rows if r["status"]=="missed")
    pending = sum(1 for r in rows if r["status"]=="pending")
    owed_customers = fetchall("SELECT COUNT(*) c FROM customers WHERE COALESCE(owed,0)>0")[0]["c"]
    execute("""
      INSERT INTO daily_report(date,total,delivered,missed,pending,owed_customers)
      VALUES(:d,:t,:dv,:m,:p,:o)
      ON CONFLICT (date) DO UPDATE SET
        total=:t, delivered=:dv, missed=:m, pending=:p, owed_customers=:o
    """, {"d": d, "t": total, "dv": delivered, "m": missed, "p": pending, "o": owed_customers})
    return dict(date=str(d), total=total, delivered=delivered, missed=missed, pending=pending, owed_customers=owed_customers)

def apply_update(customer_id, driver_id, status):
    owner = fetchall("SELECT driver_id FROM assignments WHERE customer_id=:cid", {"cid": customer_id})
    if not owner or owner[0]["driver_id"] != driver_id:
        return False
    d = date.today()
    execute("UPDATE deliveries SET status=:s, driver_id=:did WHERE date=:d AND customer_id=:cid",
            {"s": status, "did": driver_id, "d": d, "cid": customer_id})
    owed_row = fetchall("SELECT owed FROM customers WHERE customer_id=:cid", {"cid": customer_id})
    owed = (owed_row[0]["owed"] if owed_row else 0) or 0
    if status=="missed":
        owed += 1
    elif status=="delivered" and owed>0:
        owed -= 1
    execute("UPDATE customers SET owed=:o WHERE customer_id=:cid", {"o": owed, "cid": customer_id})
    return True

# ---------- Admin unlock ----------
ADMIN_OK = False
pw = st.sidebar.text_input("Admin password", type="password", help="Ask owner/admin for the password")
if pw and pw == st.secrets.get("ADMIN_PASS","admin123"):
    ADMIN_OK = True

tab_admin, tab_driver, tab_dash = st.tabs(["Admin – Assign", "Driver – Update", "Dashboard"])

with tab_admin:
    st.subheader("Assignments")
    if not ADMIN_OK:
        st.info("Enter admin password in the left sidebar to edit assignments.")
    else:
        customers = fetchall("""
          SELECT c.customer_id, c.name, c.plan, COALESCE(a.driver_id,'') driver_id
          FROM customers c LEFT JOIN assignments a ON a.customer_id=c.customer_id
          ORDER BY c.name
        """)
        drivers = fetchall("SELECT driver_id, driver_name FROM drivers WHERE active=TRUE ORDER BY driver_id")
        if customers:
            for r in customers:
                cols = st.columns([2,3,3,3])
                cols[0].write(r["customer_id"])
                cols[1].write(r["name"])
                cols[2].write(r["plan"] or "")
                new_driver = cols[3].selectbox(
                    "Driver", [""]+[d["driver_id"] for d in drivers],
                    index=([""]+[d["driver_id"] for d in drivers]).index(r["driver_id"]),
                    key=f"drv_{r['customer_id']}"
                )
            if st.button("Save Changes"):
                for r in customers:
                    did = st.session_state.get(f"drv_{r['customer_id']}", "")
                    if did == "":
                        execute("DELETE FROM assignments WHERE customer_id=:cid", {"cid": r["customer_id"]})
                    else:
                        execute("""
                          INSERT INTO assignments(customer_id, driver_id) VALUES(:cid,:did)
                          ON CONFLICT(customer_id) DO UPDATE SET driver_id=:did
                        """, {"cid": r["customer_id"], "did": did})
                st.success("Assignments saved.")
        st.markdown("---")
        c1, c2 = st.columns(2)
        if c1.button("Schedule Today"):
            added = schedule_today()
            st.success(f"Scheduled {added} pending rows for {date.today().isoformat()}.")
        if c2.button("Update KPIs"):
            k = write_kpis()
            st.success(f"KPIs updated: {k}")

with tab_driver:
    st.subheader("Mark Deliveries")
    drivers = fetchall("SELECT driver_id, driver_name FROM drivers WHERE active=TRUE ORDER BY driver_id")
    if not drivers:
        st.info("No drivers yet")
    else:
        driver_id = st.selectbox("Select Driver ID", [d["driver_id"] for d in drivers])
        stops = fetchall("""
          SELECT d.customer_id, c.name, d.status
          FROM deliveries d JOIN customers c ON c.customer_id=d.customer_id
          WHERE d.date=:d AND d.driver_id=:did
          ORDER BY c.name
        """, {"d": date.today(), "did": driver_id})
        if not stops:
            st.info("No pending stops. Ask admin to run 'Schedule Today'.")
        else:
            for r in stops:
                col1, col2, col3 = st.columns([4,3,2])
                col1.write(f"{r['customer_id']} - {r['name']}")
                status = col2.selectbox("Status", ["pending","delivered","missed"],
                                        index=["pending","delivered","missed"].index(r["status"]),
                                        key=f"st_{r['customer_id']}")
                if col3.button("Save", key=f"save_{r['customer_id']}"):
                    ok = apply_update(r['customer_id'], driver_id, status)
                    if ok: st.success("Saved"); 
                    else: st.error("Rejected: not assigned to you.")

with tab_dash:
    st.subheader("KPIs")
    today = date.today()
    rows = fetchall("SELECT status FROM deliveries WHERE date=:d", {"d": today})
    total = len(rows)
    delivered = sum(1 for r in rows if r["status"]=="delivered")
    missed = sum(1 for r in rows if r["status"]=="missed")
    pending = sum(1 for r in rows if r["status"]=="pending")
    owed = fetchall("SELECT COUNT(*) c FROM customers WHERE COALESCE(owed,0)>0")[0]["c"]
    c1,c2,c3,c4,c5 = st.columns(5)
    c1.metric("Total", total)
    c2.metric("Delivered", delivered)
    c3.metric("Missed", missed)
    c4.metric("Pending", pending)
    c5.metric("Owed Customers", owed)

    st.subheader("Delivered vs Missed (Today)")
    df = pd.DataFrame([
        {"status":"delivered","count":delivered},
        {"status":"missed","count":missed},
        {"status":"pending","count":pending},
    ]).set_index("status")
    st.bar_chart(df)

    if st.button("Refresh KPIs"):
        k = write_kpis()
        st.success(f"Refreshed: {k}")

 

