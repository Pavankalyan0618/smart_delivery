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

last_err = st.session_state.get("last_error")
if last_err:
    st.sidebar.warning(f"Last error: {last_err}")




 

