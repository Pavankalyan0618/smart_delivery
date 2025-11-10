import streamlit as st
from datetime import date, timedelta
import time
from db import (
    list_customers, list_drivers,
    add_customer, add_driver, create_assignment,
    db_healthcheck,
    list_assignments_for_date, upsert_delivery, copy_missed_to_date, delivery_kpis_for_date
)
from db import authenticate_user
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
    st.session_state["role"] = None

if not st.session_state["logged_in"]:
    st.title("Smart Delivery Login")
 
    username = st.text_input("username")
    password = st.text_input("password", type="password")

    if st.button("Login"):
        user = authenticate_user(username, password)
        if user:
             st.session_state["logged_in"] = True
             st.session_state["role"] = user["role"]
             st.session_state["user_id"] = user["user_id"]
             st.session_state["driver_id"] = user.get("driver_id")  # driver only
             st.success(f"Welcome {user['username']} ({user['role']})!")
             time.sleep(1)
             st.rerun()
        else:
         st.error("Invalid credentials")
    st.stop()   
            

st.set_page_config(page_title="Smart Delivery", layout="wide")
st.title("Smart Delivery System")

#---- Role based tabs -----
if st.session_state["role"] == "admin":
    tabs = st.tabs(["Admin", "Driver", "Dashboard"])
elif st.session_state["role"] == "driver":
    tabs = st.tabs(["Driver"])
else:
    st.error("Unknown role. Please contatct admin.")
    st.stop()

# Sidebar diagnostics 
st.sidebar.title("Diagnostics")
if st.sidebar.button("DB Ping"):
    st.sidebar.write("DB reachable:", db_healthcheck())

last_err = st.session_state.get("last_error")
if last_err:
    st.sidebar.warning(f"Last error: {last_err}")

# -------------------- Admin Tab --------------------
if st.session_state["role"] == "admin":
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

# -------------------- Driver Tab --------------------
if st.session_state["role"] == "admin":
    with tabs[1]:
        st.subheader("Driver - mark Delivered / Missed")
elif st.session_state["role"] == "driver":
    with tabs[0]:
        st.subheader("Driver - mark Delivered / Missed")  
        
        work_date = st.date_input("Date", value=date.today(), key="driver_work_date")
        
        driver_id = st.session_state.get("driver_id")
        if not driver_id:
            st.error("Driver ID not found in session. Please log in again.")
            st.stop()
        try:
            todays_assign = list_assignments_for_date(work_date)
            todays_assign =[r for r in todays_assign if r["driver_id"] == driver_id]
        except Exception as e:
            st.session_state['last_error'] = str(e)
            st.error("Couldn't load assignmnets.")
            todays_assign = []

        if not todays_assign:
            st.info("No assignments for you on this date.")
        else:
            st.caption("Mark each delivery as Delivered or Missed, then Submit.")
            status_by_assignment = {}
            for row in todays_assign:
               key = f'status_{row["assignment_id"]}'
               status_by_assignment[row["assignment_id"]] = st.radio(
                f'{row["customer_name"]}',
                options=["DELIVERED", "MISSED"],
                horizontal=True,
                key=key
                )
             

            if st.button("Submit statuses"):
                try:
                    for row in todays_assign:
                        upsert_delivery(
                            assignment_id=row["assignment_id"],
                            delivery_date=work_date,
                            status=status_by_assignment[row["assignment_id"]].lower(),
                            marked_by=st.session_state.get("user_id")
                            )
                           
                    st.success("Statuses saved.")
                except Exception as e:
                    st.session_state["last_error"] = str(e)
                    st.error("Failed to save statuses. See sidebar.")

        st.divider()
        if st.button("Copy yesterday's MISSED to today"):
            try:
                prev_date = work_date - timedelta(days=1) 
                copy_missed_to_date(prev_date, work_date)
                st.success("Carried over yesterday's MISSED assignmnets.") 
            except Exception as e:
                st.session_state["last_error"] = str(e) 
                st.error("Failed to carry over") 

# -------------------- Dashboard Tab -----------------
if st.session_state["role"] == "admin":
    with tabs[2]:
        st.subheader("Dashboard – KPIs")
        kpi_date = st.date_input("KPI Date", value=date.today())
        try:
            k = delivery_kpis_for_date(kpi_date)
            colA, colB, colC, colD = st.columns(4)
            colA.metric("Delivered", k.get("delivered", 0))
            colB.metric("Missed",    k.get("missed", 0))
            colC.metric("Pending",   k.get("pending", 0))
            colD.metric("Total",     k.get("total", 0))
        except Exception as e:
            st.session_state["last_error"] = str(e)
            st.error("Could not load KPIs.")
