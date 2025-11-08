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

# Sidebar diagnostics 
st.sidebar.title("Diagnostics")
if st.sidebar.button("DB Ping"):
    st.sidebar.write("DB reachable:", db_healthcheck())

last_err = st.session_state.get("last_error")
if last_err:
    st.sidebar.warning(f"Last error: {last_err}")

# -------------------- Admin Tab --------------------
with tabs[0]:
    st.subheader("Admin – manage customers, drivers, assignments")

    col1, col2 = st.columns(2)

    # LEFT: Add Customer
    with col1:
        st.markdown("**Add Customer**")
        c_name = st.text_input("Full name", key="c_name")
        c_phone = st.text_input("Phone", key="c_phone")
        c_addr = st.text_area("Address", key="c_addr")
        c_plan = st.selectbox("Plan", ["Daily", "Weekdays", "Custom"], key="c_plan")
        c_active = st.checkbox("Active", value=True, key="c_active")
        if st.button("Save Customer"):
            if c_name.strip():
                try:
                    add_customer(c_name, c_phone, c_addr, c_plan, c_active)
                    st.success("Customer saved.")
                except Exception as e:
                    st.session_state["last_error"] = str(e)
                    st.error("Failed to save customer. See sidebar for details.")
            else:
                st.warning("Name is required.")

    
# RIGHT: Add Driver
    with col2:
        st.markdown("**Add Driver**")
        d_name = st.text_input("Driver name", key="d_name")
        d_phone = st.text_input("Driver phone", key="d_phone")
        if st.button("Save Driver"):
            if d_name.strip():
                try:
                    add_driver(d_name, d_phone)
                    st.success("Driver saved.")
                except Exception as e:
                    st.session_state["last_error"] = str(e)
                    st.error("Failed to save driver. See sidebar for details.")
            else:
                st.warning("Driver name is required.")

    st.divider()
