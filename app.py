import streamlit as st
from datetime import date, timedelta
import time
import pandas as pd
from db import fetch_all
from db import update_owed_deliveries
from db import (
    list_customers, list_drivers,
    add_customer, add_driver, create_assignment,
    db_healthcheck,
    list_assignments_for_date, upsert_delivery, delivery_kpis_for_date,
    create_driver_user
)
from db import authenticate_user
for key in ["logged_in", "role", "user_id", "driver_id", "last_error"]:
    if key not in st.session_state:
        st.session_state[key] = None
st.session_state["logged_in"] = st.session_state["logged_in"] or False

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
            
#-----Logout button--------
st.set_page_config(page_title="Smart Delivery", layout="wide")
col1, col2 = st.columns([8, 1])
with col1:
    st.title("Smart Delivery System")
with col2:
    if st.button("Logout"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.success("Logged out successfully.")
        st.rerun()

#---- Role based tabs -----
if st.session_state.get("role") == "admin":
    tabs = st.tabs(["Admin", "Driver", "Dashboard"])
elif st.session_state.get("role") == "driver":
    tabs = st.tabs(["Driver"])
else:
    st.error("Unknown role. Please contatct admin.")
    st.stop()

#-----Sidebar diagnostics  ------
st.sidebar.title("Diagnostics")
if st.sidebar.button("DB Ping"):
    st.sidebar.write("DB reachable:", db_healthcheck())

last_err = st.session_state.get("last_error")
if last_err:
    st.sidebar.warning(f"Last error: {last_err}")

# -------------------- Admin Tab --------------------
if st.session_state.get("role") == "admin":
    with tabs[0]:
        st.subheader("Admin – manage customers, drivers, assignments")

        col1, col2 = st.columns(2)

        # LEFT: Add Customer
        with col1:
            st.markdown("**Add Customer**")
            c_name = st.text_input("Full name", key="c_name")
            c_phone = st.text_input("Phone Number (10 digits)", max_chars=10, key="c_phone")
            if c_phone and (not c_phone.isdigit()):
                st.warning("phone number must contain only digits.")
            elif c_phone and len(c_phone) != 10:
                st.warning("Phone number must be exactly 10 digits.")

            c_addr = st.text_area("Address", key="c_addr")
            c_plan = "Monthly"
            c_location = st.text_input("Location", key="c_location")
            c_sub_start = st.date_input("Subscription Start Date", key="c_sub_start")
            c_sub_days = 30

            if st.button("Save Customer"):
                if not c_phone.isdigit() or len(c_phone) != 10:
                    st.error("Invalid phone number. Please enter exactly 10 digits.")
                
                elif not c_name.strip():
                     st.warning("Name is required.")
                
                else:
                    try:
                        add_customer(c_name, c_phone, c_addr, c_plan, c_location, c_sub_start, c_sub_days)
                        st.success("Customer saved.")
                    except Exception as e:
                     st.session_state["last_error"] = str(e)
                     st.error("Failed to save customer. See sidebar for details.")

        
        # RIGHT: Add Driver
        with col2:
            st.markdown("**Add Driver**")
            d_name = st.text_input("Driver name", key="d_name")
            d_phone = st.text_input("Driver phone", key="d_phone")

            if st.button("Save Driver"):
                if d_name.strip() and d_phone.strip():
                    try:
                        # Save driver and get driver_id
                        driver_id = add_driver(d_name, d_phone)

                        # AUTO‑CREATE USER ACCOUNT FOR DRIVER
                        create_driver_user(
                            username=d_phone,
                            password="1234",
                            driver_id=driver_id
                        )

                        st.success(f"Driver saved. Login created: Username = {d_phone}, Password = 1234")

                    except Exception as e:
                        st.session_state["last_error"] = str(e)
                        st.error("Failed to save driver or create login. See sidebar for details.")
                else:
                    st.warning("Driver name and phone are required.")

        st.divider()

# --------Assignment section--------------------
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

            # ---------------- AREA DROPDOWN ----------------
            areas = sorted({c["location"] for c in customers if c.get("location")})
            selected_area = st.selectbox("Select Area / Location", ["-- Select Area --"] + areas)

            if selected_area != "-- Select Area --":
                customers = [c for c in customers if c.get("location") == selected_area]

            # ---------------- CUSTOMER LIST ----------------
            st.markdown("### Customers in Selected Area")

            customer_names = [c["full_name"] for c in customers]
            if "multi_customers" not in st.session_state:
                st.session_state["multi_customers"] = []
            selected_customers = st.multiselect("Select Customers", customer_names, key="multi_customers")

            name_to_id = {c["full_name"]: c["customer_id"] for c in customers}

            # ---------------- SELECTED CUSTOMER ----------------
            if selected_customers:
               
                driv_map = {d["full_name"]: d["driver_id"] for d in drivers}

                sel_driv = st.selectbox("Driver", list(driv_map.keys()), key="assign_driver")
                sel_date = st.date_input("Assignment date", value=date.today(), key="assign_date")

                if st.button("Create Assignment"):
                    try:
                        for name in selected_customers:
                            cid = name_to_id[name]
                            create_assignment(sel_date, cid, driv_map[sel_driv])

                        st.success("Assignments created successfully.")
                    except ValueError as ve:
                        st.error(str(ve))
                    except Exception as e:
                        st.session_state["last_error"] = str(e)
                        st.error("Failed to create assignment. See sidebar.")
        st.divider()

        st.markdown("**Customers (live from DB)**")
        
        customers = list_customers()
        df = pd.DataFrame(customers)

#------------- OWED EXISTs ------------------

        if "owed" not in df.columns:
            df["owed"] = 0

#-------------- SUBCRIPTION DAYS EXISTS ---------------
        if "subscription_days" not in df.columns:
            df["subscription_days"] = 30

#-------------- SAFE SUBSCRIPTION END CALCULATION ---------------
        if not df.empty and "subscription_start" in df.columns:
            
            df["subscription_start"] = pd.to_datetime(df["subscription_start"], errors="coerce")

            
            df["subscription_end"] = df["subscription_start"] + pd.to_timedelta(
                df["subscription_days"].fillna(30) + df["owed"].fillna(0),
                unit="D"
            )
        else:
            df["subscription_end"] = pd.NaT

#--------------  SUBSCRIPTION STATUS ------------------------
        if not df.empty and "subscription_end" in df.columns:
            today = pd.Timestamp.today()

            df["subscription_status"] = df["subscription_end"].apply(
                lambda d: ("Active" if d >= today else "Expired") if pd.notnull(d) else "Unknown"
            )
        else:
            df["subscription_status"] = "Unknown"

        # DISPLAY CUSTOMERS LIVE FROM DB
        st.dataframe(df, use_container_width=True)
# -------------------- Driver Tab --------------------
if st.session_state.get("role") == "admin":
    with tabs[1]:
        st.subheader("Driver - mark Delivered / Missed")

        work_date = st.date_input("Date", value=date.today(), key="admin_driver_work_date")

        try:
            drivers = list_drivers()
            driver_map = {d["full_name"]: d["driver_id"] for d in drivers}
            sel_driver_label = st.selectbox("Select Driver", list(driver_map.keys()), key="admin_driver_select")
            sel_driver_id = driver_map[sel_driver_label]

            todays_assign = list_assignments_for_date(work_date)
            todays_assign = [r for r in todays_assign if r["driver_id"] == sel_driver_id]

            if not todays_assign:
                st.info("No assignments for this driver on the selected date.")
            else:
                st.dataframe(todays_assign, use_container_width=True)

        except Exception as e:
            st.session_state["last_error"] = str(e)
            st.error("Couldn't load driver data.")
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
                        status = status_by_assignment[row["assignment_id"]].lower()
                        update_owed_deliveries(
                            row["assignment_id"],
                            row["customer_id"],
                            status,
                            work_date
                        )
                        upsert_delivery(
                            assignment_id=row["assignment_id"],
                            delivery_date=work_date,
                            status=status,
                            marked_by=st.session_state.get("user_id")
                        )

                    st.success("Statuses saved.")
                except Exception as e:
                    st.session_state["last_error"] = str(e)
                    st.error("Failed to save statuses. See sidebar.")
                    
# -------------------- Dashboard Tab -----------------
if st.session_state.get("role") == "admin":
    with tabs[2]:
        st.subheader("KPI Date Range")
        st.write("")

        # KPI DATE RANGE
        with st.container():
            col1, col2 = st.columns(2)
            from_date = col1.date_input("From Date", value=date.today())
            to_date = col2.date_input("To Date", value=date.today())

            if from_date > to_date:
                st.error("From Date cannot be after To Date.")
            else:
                rows = fetch_all("""
                    SELECT status FROM deliveries
                    WHERE delivery_date BETWEEN %s AND %s;
                """, (from_date, to_date))

                delivered = sum(1 for r in rows if r["status"] == "delivered")
                missed = sum(1 for r in rows if r["status"] == "missed")
                total = len(rows)

                k1, k2, k3 = st.columns(3)
                k1.metric("Delivered", delivered)
                k2.metric("Missed", missed)
                k3.metric("Total Deliveries", total)

        st.divider()

        # TWO COLUMN LAYOUT
        left, right = st.columns(2)

        # LEFT: CARRY-FORWARD
        with left:
            st.subheader("Carry-Forward Deliveries")
            st.write("")
            try:
                owed_data = fetch_all("""
                    SELECT customer_id, full_name, owed
                    FROM customers
                    WHERE owed > 0
                    ORDER BY owed DESC;
                """)

                if owed_data:
                    df = pd.DataFrame(owed_data)
                    df.rename(columns={"owed": "Carry Forward"}, inplace=True)
                    st.dataframe(df, use_container_width=True)
                    total_owed = df["Carry Forward"].sum()
                    st.metric("Total Carry Forward Deliveries", total_owed)
                else:
                    st.info("No carry-forward deliveries right now.")
            except Exception as e:
                st.error(f"Error loading carry-forward: {e}")

        # RIGHT: DRIVER MISSED
        with right:
            st.subheader("Driver-wise Missed Deliveries")
            st.write("")

            drivers = list_drivers()

            if not drivers:
                st.info("No drivers available.")
                st.stop()

            driver_names = [d["full_name"] for d in drivers]
            selected_driver = st.selectbox("Select Driver", driver_names)

            driver_map = {d["full_name"]: d["driver_id"] for d in drivers}
            driver_id = driver_map.get(selected_driver)

            if driver_id is None:
                st.warning("Invalid driver selection.")
                st.stop()

            d1, d2 = st.columns(2)
            d_from = d1.date_input("From Date (Driver)", value=date.today())
            d_to = d2.date_input("To Date (Driver)", value=date.today())

            if d_from > d_to:
                st.error("From Date cannot be after To Date.")
            else:
                try:
                    query = """
                        SELECT d.full_name AS driver_name,
                               COUNT(*) AS missed_count
                        FROM deliveries del
                        JOIN assignments a ON del.assignment_id = a.assignment_id
                        JOIN drivers d ON a.driver_id = d.driver_id
                        WHERE del.status = 'missed'
                        AND d.driver_id = %s
                        AND del.delivery_date BETWEEN %s AND %s
                        GROUP BY d.full_name;
                    """
                    rows = fetch_all(query, (driver_id, d_from, d_to))

                    if rows:
                        df_d = pd.DataFrame(rows)
                        st.dataframe(df_d, use_container_width=True)
                    else:
                        st.info(f"No missed deliveries for {selected_driver} in this range.")
                except Exception as e:
                    st.error(f"Error loading driver missed: {e}")





