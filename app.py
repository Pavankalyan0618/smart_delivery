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

# Assignment section
    st.markdown("**Assign Customer to Driver (for a date)**")
    try:
        customers = list_customers()
    except Exception as e:
        st.session_state["last_error"] = str(e)
        st.error("Couldn't load customers from DB.")
        customers = []

    try:
        drivers = list_drivers()
    except Exception as e:
        st.session_state["last_error"] = str(e)
        st.error("Couldn't load drivers from DB.")
        drivers = []

    if not customers:
        st.info("No customers yet. Add one above.")
    if not drivers:
        st.info("No drivers yet. Add one above.")

    if customers and drivers:
        cust_map = {c["full_name"]: c["customer_id"] for c in customers}
        driv_map = {d["full_name"]: d["driver_id"] for d in drivers}

        sel_cust = st.selectbox("Customer", list(cust_map.keys()), key="assign_customer")
        sel_driv = st.selectbox("Driver", list(driv_map.keys()), key="assign_driver")
        sel_date = st.date_input("Assignment date", value=date.today(), key="assign_date")

        if st.button("Create Assignment"):
            try:
                create_assignment(sel_date, cust_map[sel_cust], driv_map[sel_driv])
                st.success("Assignment created.")
            except Exception as e:
                st.session_state["last_error"] = str(e)
                st.error("Failed to create assignment. See sidebar for details.")

    st.divider()

    st.markdown("**Customers (live from DB)**")
    if customers:
        st.dataframe(customers, use_container_width=True)
    else:
        st.info("No customers to display.")

    st.markdown("**Drivers (live from DB)**")
    if drivers:
        st.dataframe(drivers, use_container_width=True)
    else:
        st.info("No drivers to display.")
