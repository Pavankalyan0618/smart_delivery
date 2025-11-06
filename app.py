import streamlit as st
import pandas as pd
from datetime import date, datetime
from dateutil.parser import parse as parse_date
from db import fetchall, execute

st.set_page_config(page_title="Smart Delivery", layout="wide")
st.title("Smart Delivery System")

# ---------- Utility logic ----------
WEEKDAYS = ["mon","tue","wed","thu","fri","sat","sun"]
def dow_str(d): return WEEKDAYS[d.weekday()]

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




 

