
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
    create_driver_user,
    delete_customer, delete_driver
)
from db import authenticate_user
from db import update_customer, renew_subscription, pause_delivery_for_customer
for key in ["logged_in", "role", "user_id", "driver_id", "last_error"]:
    if key not in st.session_state:
        st.session_state[key] = None
if "admin_mode" not in st.session_state:
    st.session_state["admin_mode"] = None
st.session_state["logged_in"] = st.session_state["logged_in"] or False

# ---------------- LOGIN SCREEN ----------------
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
            
# ---------------- LOGOUT SECTION ----------------
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

# ---------------- ROLE-BASED UI LOADING ----------------
if st.session_state.get("role") == "admin":
    tabs = st.tabs(["Admin", "Driver", "Dashboard"])
elif st.session_state.get("role") == "driver":
    tabs = st.tabs(["Driver"])
else:
    st.error("Unknown role. Please contatct admin.")
    st.stop()

# ---------------- DIAGNOSTICS (DEBUGGING INFO) ----------------
st.sidebar.title("Diagnostics")
if st.sidebar.button("DB Ping"):
    st.sidebar.write("DB reachable:", db_healthcheck())

last_err = st.session_state.get("last_error")
if last_err:
    st.sidebar.warning(f"Last error: {last_err}")

#-------------------- ADMIN TAB - CUSTOMER & DRIVER MANAGEMENT -------------

if st.session_state.get("role") == "admin":
    with tabs[0]:
        
        # ---------------- CARD STYLE CUSTOMER MANAGEMENT ----------------
        mode = st.session_state.get("admin_mode")

        
        if mode is None:
            st.markdown("## 🛠 Smart Delivery Control Center – Admin")

            # --- Top-Level Category Buttons ---
            main_cols = st.columns(3)

            with main_cols[0]:
                if st.button("👤 Customer Management", key="btn_customer_section"):
                    st.session_state["admin_mode"] = "customer_section"
                    st.rerun()

            with main_cols[1]:
                if st.button("📦 Subscription & Delivery", key="btn_subscription_section"):
                    st.session_state["admin_mode"] = "subscription_section"
                    st.rerun()

            with main_cols[2]:
                if st.button("🚗 Driver Management", key="btn_driver_section"):
                    st.session_state["admin_mode"] = "driver_section"
                    st.rerun()
            st.markdown("---")

        # ================= CUSTOMER SECTION =================
        if mode == "customer_section":
            st.markdown("### 👤 Customer Management")

            ccols = st.columns(3)
            with ccols[0]:
                if st.button("➕ New Customer", key="cust_add_btn"):
                    st.session_state["admin_mode"] = "add"
                    st.rerun()

            with ccols[1]:
                if st.button("✏️ Update Customer Details", key="cust_edit_btn"):
                    st.session_state["admin_mode"] = "edit"
                    st.rerun()

            with ccols[2]:
                if st.button("🗑 Remove Customer", key="cust_delete_btn"):
                    st.session_state["admin_mode"] = "delete_customer"
                    st.rerun()

            if st.button("⬅ Back", key="cust_back"):
                st.session_state["admin_mode"] = None
                st.rerun()

        # ================= SUBSCRIPTION SECTION =================
        elif mode == "subscription_section":
            st.markdown("### 📦 Subscription Management")

            scols = st.columns(2)
            with scols[0]:
                if st.button("🔁 Renew Plan", key="sub_renew_btn"):
                    st.session_state["admin_mode"] = "renew"
                    st.rerun()

            with scols[1]:
                if st.button("⏸ Pause Delivery for a Day", key="sub_pause_btn"):
                    st.session_state["admin_mode"] = "pause"
                    st.rerun()

            if st.button("⬅ Back", key="sub_back"):
                st.session_state["admin_mode"] = None
                st.rerun()

        # ================= DRIVER SECTION =================
        elif mode == "driver_section":
            st.markdown("### 🚗 Driver Management")

            dcols = st.columns(2)
            with dcols[0]:
                if st.button("➕ New Driver", key="driver_add_btn"):
                    st.session_state["admin_mode"] = "add_driver"
                    st.rerun()

            with dcols[1]:
                if st.button("🗑 Remove Driver", key="driver_delete_btn"):
                    st.session_state["admin_mode"] = "delete_driver"
                    st.rerun()

            if st.button("⬅ Back", key="driver_back"):
                st.session_state["admin_mode"] = None
                st.rerun()

        # SHOW SELECTED PAGE ONLY
        elif mode == "add":
            st.markdown('<div class="card"><span class="card-title">Add Customer</span></div>', unsafe_allow_html=True)

            c_name = st.text_input("Full Name")
            c_phone = st.text_input("Phone Number (10 digits)", max_chars=10)
            c_addr = st.text_area("Address")
            c_location = st.text_input("Location")
            c_sub_start = st.date_input(
                "Subscription Start Date",
                value=date.today(),
                min_value=date.today()
            )
            c_sub_days = 30

            if st.button("Save Customer"):
                if not c_phone.isdigit() or len(c_phone) != 10:
                    st.error("Invalid phone number. Must be 10 digits.")
                elif not c_name.strip():
                    st.warning("Name is required.")
                else:
                    try:
                        add_customer(c_name, c_phone, c_addr, "Monthly", c_location, c_sub_start, c_sub_days)
                        st.success("Customer added successfully.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Failed to add customer: {e}")

            if st.button("⬅ Back"):
                st.session_state["admin_mode"] = None
                st.rerun()

        elif mode == "edit":
            st.markdown('<div class="card"><span class="card-title">Edit Existing Customer</span></div>', unsafe_allow_html=True)
            customers = list_customers()
            cust_map = {c["full_name"]: c for c in customers}
            sel = st.selectbox("Select customer", ["-- Select --"] + list(cust_map.keys()), key="edit_card_sel")

            if sel != "-- Select --":
                c = cust_map[sel]
                name = st.text_input("Full Name", value=c["full_name"])
                phone = st.text_input("Phone Number", value=c["phone_number"])
                addr = st.text_area("Address", value=c["address"])
                plan = st.text_input("Plan Name", value=c["plan_name"])
                loc = st.text_input("Location", value=c["location"])
                start = st.date_input(
                    "Subscription Start",
                    value=c["subscription_start"],
                    min_value=date(2000, 1, 1)
                )
                days = st.number_input("Subscription Days", min_value=1, value=int(c["subscription_days"]))

                if st.button("Save Changes"):
                    update_customer(c["customer_id"], name, phone, addr, plan, loc, start, days)
                    st.success("Customer updated successfully.")
                    st.rerun()
            if st.button("⬅ Back"):
                st.session_state["admin_mode"] = None
                st.rerun()

        elif mode == "renew":
            st.markdown('<div class="card"><span class="card-title">Renew Subscription</span></div>', unsafe_allow_html=True)
            customers = list_customers()

            # --------- AUTO‑FILTER EXPIRED ONLY ----------
            expired_customers = []
            for c in customers:
                sub_start = pd.to_datetime(c["subscription_start"])
                sub_days = int(c["subscription_days"])
                owed = int(c.get("owed", 0))
                sub_end = sub_start + timedelta(days=sub_days + owed)

                if sub_end < pd.to_datetime(date.today()):
                    expired_customers.append(c)

            if not expired_customers:
                st.info("No expired customers available for renewal.")
            else:
                # --------- BULK RENEW OPTION ----------
                st.markdown("### 🔄 Renew All Expired Customers (Bulk Action)")

                expired_names = [c["full_name"] for c in expired_customers]

                bulk_selected = st.multiselect(
                    "Select expired customers to renew in bulk",
                    expired_names,
                    key="bulk_renew_select"
                )

                bulk_days = st.number_input(
                    "Days to add for selected customers",
                    min_value=1,
                    value=30,
                    key="bulk_renew_days"
                )

                if bulk_selected and st.button("Apply Bulk Renewal", key="bulk_renew_btn"):
                    try:
                        for name in bulk_selected:
                            cid = next(c["customer_id"] for c in expired_customers if c["full_name"] == name)
                            renew_subscription(cid, bulk_days)
                        st.success(f"Renewed {len(bulk_selected)} customers successfully.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Bulk renewal failed: {e}")

                cust_map = {c["full_name"]: c for c in expired_customers}

                sel = st.selectbox("Select expired customer to renew", ["-- Select --"] + list(cust_map.keys()), key="renew_card_sel")

                if sel != "-- Select --":
                    c = cust_map[sel]

                    # Calculate subscription_end using same logic as overview table
                    sub_start = pd.to_datetime(c["subscription_start"])
                    sub_days = int(c["subscription_days"])
                    owed = int(c.get("owed", 0))

                    sub_end = sub_start + timedelta(days=sub_days + owed)
                    today = pd.to_datetime(date.today())

                    # ---- BLOCK RENEWAL IF STILL ACTIVE ----
                    if sub_end >= today:
                        st.warning(f"⚠ Subscription for {sel} is ACTIVE until {sub_end.date()}. Cannot renew now.")
                    else:
                        st.success(f"Subscription expired on {sub_end.date()}. Renewal allowed.")

                        extra = st.number_input("Add Days", min_value=1, value=30)

                        if st.button("Apply Renewal"):
                            renew_subscription(c["customer_id"], extra)
                            st.success(f"Subscription renewed for {sel}.")
                            st.rerun()
            if st.button("⬅ Back"):
                st.session_state["admin_mode"] = None
                st.rerun()

        elif mode == "pause":
            st.markdown('<div class="card"><span class="card-title">Pause Delivery</span></div>', unsafe_allow_html=True)
            customers = list_customers()
            cust_map = {c["full_name"]: c for c in customers}
            sel = st.selectbox("Select customer to pause", ["-- Select --"] + list(cust_map.keys()), key="pause_card_sel")
            pause_date = st.date_input("Pause Date", value=date.today())

            if sel != "-- Select --" and st.button("Pause Now"):
                pause_delivery_for_customer(cust_map[sel]["customer_id"], pause_date, st.session_state.get("user_id"))
                st.success(f"Paused delivery for {sel} on {pause_date}.")
                st.rerun()
            if st.button("⬅ Back"):
                st.session_state["admin_mode"] = None
                st.rerun()

        elif mode == "delete_customer":
            st.markdown('<div class="card"><span class="card-title">Delete Customer</span></div>', unsafe_allow_html=True)
            customers = list_customers()
            cust_map = {c["full_name"]: c for c in customers}
            sel = st.selectbox("Select customer to delete", ["-- Select --"] + list(cust_map.keys()), key="del_cust_card_sel")

            if sel != "-- Select --":
                confirm = st.checkbox(f"Are you sure you want to delete {sel}?")
                if confirm and st.button("Delete Customer Now"):
                    delete_customer(cust_map[sel]["customer_id"])
                    st.success(f"Deleted customer: {sel}")
                    st.rerun()
            if st.button("⬅ Back"):
                st.session_state["admin_mode"] = None
                st.rerun()

        elif mode == "add_driver":
            st.markdown('<div class="card"><span class="card-title">Add Driver</span></div>', unsafe_allow_html=True)

            d_name = st.text_input("Driver Name")
            d_phone = st.text_input("Driver Phone")

            if st.button("Save Driver", key="save_driver_card"):
                if d_name.strip() and d_phone.strip():
                    try:
                        driver_id = add_driver(d_name, d_phone)
                        create_driver_user(username=d_phone, password="1234", driver_id=driver_id)
                        st.success(f"Driver added. Login: {d_phone} / 1234")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Failed to add driver: {e}")
                else:
                    st.warning("Driver name and phone required.")

            if st.button("⬅ Back"):
                st.session_state["admin_mode"] = None
                st.rerun()

        elif mode == "delete_driver":
            st.markdown('<div class="card"><span class="card-title">Delete Driver</span></div>', unsafe_allow_html=True)
            drivers = list_drivers()
            d_map = {d["full_name"]: d for d in drivers}
            sel = st.selectbox("Select driver to delete", ["-- Select --"] + list(d_map.keys()), key="del_driver_card_sel")

            if sel != "-- Select --":
                confirm = st.checkbox(f"Are you sure you want to delete driver {sel}?")
                if confirm and st.button("Delete Driver Now"):
                    delete_driver(d_map[sel]["driver_id"])
                    st.success(f"Deleted driver: {sel}")
                    st.rerun()
            if st.button("⬅ Back"):
                st.session_state["admin_mode"] = None
                st.rerun()


        # ----------- Customer-to-Driver Assignment Panel -----------
        if mode is None:
            st.markdown("---")
            st.markdown("## Customer-to-Driver Assignment Panel")
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
                st.markdown("**Customers in Selected Area**")

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

            # ----------- NEW: REMOVE ASSIGNMENTS SECTION -----------
            st.markdown("## Remove Existing Assignments")

            remove_date = st.date_input("Select Date to View Assignments", value=date.today(), key="remove_assign_date")

            # Select driver for removal
            drv_names = [d["full_name"] for d in drivers]
            chosen_driver = st.selectbox("Select Driver", drv_names, key="remove_assign_driver")
            chosen_driver_id = {d["full_name"]: d["driver_id"] for d in drivers}[chosen_driver]

            # Load assignments for chosen date + driver
            rows = fetch_all(
                "SELECT a.assignment_id, a.customer_id, c.full_name "
                "FROM assignments a "
                "JOIN customers c ON a.customer_id = c.customer_id "
                "WHERE a.assign_date = %s AND a.driver_id = %s;",
                (remove_date, chosen_driver_id)
            )

            if not rows:
                st.info("No assignments found for this driver on this date.")
            else:
                cust_map = {r["full_name"]: r["assignment_id"] for r in rows}

                to_remove = st.multiselect(
                    "Select customers to unassign",
                    list(cust_map.keys()),
                    key="remove_assign_multiselect"
                )

                if to_remove and st.button("Unassign Selected Customers", key="remove_assign_btn"):
                    try:
                        for name in to_remove:
                            aid = cust_map[name]
                            fetch_all("DELETE FROM assignments WHERE assignment_id = %s;", (aid,))
                        st.success(f"Removed {len(to_remove)} assignments.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Failed to remove assignments: {e}")

            # Customer Subscription Overview block
            st.markdown("## Customer Subscription Overview")

            customers = list_customers()
            df = pd.DataFrame(customers)

            if "owed" not in df.columns:
                df["owed"] = 0

            if "subscription_days" not in df.columns:
                df["subscription_days"] = 30

            if not df.empty and "subscription_start" in df.columns:
                df["subscription_start"] = pd.to_datetime(df["subscription_start"], errors="coerce")
                df["subscription_end"] = df["subscription_start"] + pd.to_timedelta(
                    df["subscription_days"].fillna(30) + df["owed"].fillna(0), unit="D"
                )
            else:
                df["subscription_end"] = pd.NaT

            if not df.empty and "subscription_end" in df.columns:
                today = pd.Timestamp.today()
                df["subscription_status"] = df["subscription_end"].apply(
                    lambda d: ("Active" if d >= today else "Expired") if pd.notnull(d) else "Unknown"
                )
            else:
                df["subscription_status"] = "Unknown"

            st.dataframe(df, use_container_width=True)

#----------------- ADMIN VIEW OF DRIVER ASSIGNMENTS + DELIVERY STATUS -------------
if st.session_state.get("role") == "admin":
    with tabs[1]:
        st.subheader("Driver Delivery Tracking – Admin Panel")

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
                enriched_rows = []
                for r in todays_assign:
                    # Fetch delivery status, marked time, and marked_by
                    status_row = fetch_all(
                        "SELECT status, marked_by FROM deliveries WHERE assignment_id = %s AND delivery_date = %s;",
                        (r["assignment_id"], work_date)
                    )
                    delivery_status = status_row[0]["status"] if status_row else "Not Marked"
                    marked_by = status_row[0].get("marked_by") if status_row else None

                    # Fetch customer location
                    cust_info = fetch_all(
                        "SELECT location FROM customers WHERE customer_id = %s;",
                        (r["customer_id"],)
                    )
                    location = cust_info[0]["location"] if cust_info else ""

                    enriched_rows.append({
                        "Customer": r["customer_name"],
                        "Assignment ID": r["assignment_id"],
                        "Customer ID": r["customer_id"],
                        "Driver Name": r.get("driver_name", ""),
                        "Area / Location": location,
                        "Delivered / Missed": delivery_status,
                        "Time Marked": marked_by if marked_by else "",
                        "Date": work_date,
                    })

                st.dataframe(enriched_rows, use_container_width=True)

                # --- DOWNLOAD ADMIN DRIVER REPORT ---
                df_admin_driver = pd.DataFrame(enriched_rows)

                st.download_button(
                    label="⬇ Download This Report (CSV)",
                    data=df_admin_driver.to_csv(index=False),
                    file_name=f"driver_report_{sel_driver_label}_{work_date}.csv",
                    mime="text/csv",
                    key="download_admin_driver_report"
                )

        except Exception as e:
            st.session_state["last_error"] = str(e)
            st.error("Couldn't load driver data.")

#--------------------- DRIVER TAB - MARK DELIVERED / MISSED ----------------
elif st.session_state["role"] == "driver":
    with tabs[0]:
        st.subheader("Delivery Status Submission - Driver View")  
        
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
            # --- DRIVER DOWNLOAD REPORT (Enhanced) ---
            driver_report_data = []
            for r in todays_assign:

                # Fetch delivery status & marked time (if exists)
                status_row = fetch_all(
                    "SELECT status, marked_by FROM deliveries WHERE assignment_id = %s AND delivery_date = %s;",
                    (r['assignment_id'], work_date)
                )
                delivery_status = status_row[0]["status"] if status_row else "Not Marked"
                marked_by = status_row[0].get("marked_by") if status_row else None

                # Fetch customer location
                cust_info = fetch_all(
                    "SELECT location FROM customers WHERE customer_id = %s;",
                    (r['customer_id'],)
                )
                location = cust_info[0]["location"] if cust_info else ""

                driver_report_data.append({
                    "Customer": r["customer_name"],
                    "Assignment ID": r["assignment_id"],
                    "Customer ID": r["customer_id"],
                    "Driver Name": st.session_state.get("role") == "driver" and st.session_state.get("user_id"),
                    "Area / Location": location,
                    "Delivered / Missed": delivery_status,
                    "Time Marked": marked_by if marked_by else "",
                    "Date": work_date,
                })

            df_driver_report = pd.DataFrame(driver_report_data)

            st.download_button(
                label="⬇ Download Today's Assignment Report (CSV)",
                data=df_driver_report.to_csv(index=False),
                file_name=f"driver_assignments_{work_date}.csv",
                mime="text/csv",
                key="download_driver_assignments"
            )
            for row in todays_assign:
                #------- Get existing status for this assignment & date backend checks -------
                status_rows = fetch_all(
                    "SELECT status FROM deliveries WHERE assignment_id = %s AND delivery_date = %s;",
                    (row["assignment_id"], work_date)
                )
                existing_status = status_rows[0]["status"] if status_rows else None

                if existing_status == "delivered":
                    default_status = "Delivered"
                elif existing_status == "missed":
                    default_status = "Missed"
                else:
                    default_status = None

                st.write(f"### {row['customer_name']}")
                options = ["Delivered", "Missed"]

                # If an existing status is available, preselect it; otherwise no default index
                if default_status in options:
                    idx = options.index(default_status)
                    selected_status = st.radio(
                        f"Status for {row['customer_name']}",
                        options,
                        index=idx,
                        key=f"radio_{row['assignment_id']}"
                    )
                else:
                    selected_status = st.radio(
                        f"Status for {row['customer_name']}",
                        options,
                        key=f"radio_{row['assignment_id']}"
                    )

                # --- Status saved indicator  ---
                if existing_status == "delivered":
                    st.write("✔ Saved as Delivered")
                elif existing_status == "missed":
                    st.write("✔ Saved as Missed")

                if st.button("Save Status", key=f"save_{row['assignment_id']}"):
                    try:
                        final_status = selected_status.lower()

                        update_owed_deliveries(
                            row["assignment_id"],
                            row["customer_id"],
                            final_status,
                            work_date
                        )
                        upsert_delivery(
                            assignment_id=row["assignment_id"],
                            delivery_date=work_date,
                            status=final_status,
                            marked_by=st.session_state.get("user_id")
                        )
                        st.success(f"Updated {row['customer_name']} as {selected_status}.")
                        st.rerun()
                    except Exception as e:
                        st.session_state["last_error"] = str(e)
                        st.error("Failed to update status.")

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

                # --- DOWNLOAD DELIVERY REPORT ---
                df_report = pd.DataFrame(rows)
                if not df_report.empty:
                    st.download_button(
                        label="⬇ Download Delivery Report (CSV)",
                        data=df_report.to_csv(index=False),
                        file_name=f"delivery_report_{from_date}_to_{to_date}.csv",
                        mime="text/csv",
                        key="download_delivery_report"
                    )
                else:
                    st.info("No deliveries found for this date range. Nothing to download.")

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

        #--------- LEFT: CARRY-FORWARD --------------
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
                    if not df.empty:
                        st.download_button(
                            label="⬇ Download Carry-Forward Report (CSV)",
                            data=df.to_csv(index=False),
                            file_name="carry_forward_report.csv",
                            mime="text/csv",
                            key="download_carry_forward_report"
                        )
                else:
                    st.info("No carry-forward deliveries right now.")
            except Exception as e:
                st.error(f"Error loading carry-forward: {e}")

        #-------------- RIGHT: DRIVER MISSED --------------
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
                        if not df_d.empty:
                            st.download_button(
                                label="⬇ Download Driver Missed Report (CSV)",
                                data=df_d.to_csv(index=False),
                                file_name=f"driver_missed_{selected_driver}.csv",
                                mime='text/csv',
                                key='download_driver_missed_report'
                            )
                    else:
                        st.info(f"No missed deliveries for {selected_driver} in this range.")
                except Exception as e:
                    st.error(f"Error loading driver missed: {e}")





