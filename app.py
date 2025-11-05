import streamlit as st
from datetime import date, timedelta
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

last_err = st.session_state.get("last_error")
if last_err:
    st.sidebar.warning(f"Last error: {last_err}")




 

