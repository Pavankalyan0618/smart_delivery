# Smart Delivery  
### Automated Fruit Bowl Subscription & Delivery Management System

Smart Delivery is a full‑stack Streamlit web application designed to automate the daily workflow of small‑scale fruit bowl delivery businesses.  
It replaces manual WhatsApp/Excel tracking with a clean, reliable, cloud‑based system for managing customers, drivers, subscriptions, deliveries, and business analytics.

---

## 🌟 Overview

This project removes operational chaos by automating:

- Daily delivery assignments  
- Missed‑delivery tracking (owed/carry‑forward logic)  
- Subscription expiry monitoring  
- Netflix‑style renewal process  
- Driver performance insights  
- Real‑time delivery updates via mobile‑friendly UI  

Built with Python + Streamlit + PostgreSQL (NeonDB), the system is optimized for simplicity, accuracy, and real‑world usability.

---

## 🚀 Core Features

### 👨‍💼 Admin Portal
- Add / edit / delete customers  
- Add / delete drivers  
- Assign customers to drivers for any delivery date  
- Mark deliveries as **Delivered**, **Missed**, or **Paused**  
- Intelligent *owed logic* handles missed deliveries automatically  
- Netflix‑style renewal (allowed only when **Carry Forward = 0**)  
- Full subscription overview with Active / Expired status  
- Delivery KPI dashboard (total, delivered, missed, pending)  
- Bulk renewal operations  

### 🚗 Driver Portal
- Driver‑specific login  
- View daily assigned deliveries  
- Update delivery status in real time  
- Designed for **mobile screens**  

---

##  Business Logic

###  Owed (Carry‑Forward) System
The system automatically tracks missed deliveries:

- Missed → `owed + 1`  
- Delivered‑after‑missed → `owed − 1`  
- Delivered normally → no owed impact  
- Paused → no owed impact  

This ensures fairness and accurate delivery fulfillment over time.

### Subscription Lifecycle (Calculated in app.py)
```
subscription_end = subscription_start + (subscription_days + owed)
```

###  Netflix‑Style Renewal Logic  
A customer may renew **only when owed = 0**.

Upon renewal:
```
subscription_start = today
subscription_days = plan_days (e.g., 30)
owed = 0
```

This starts a clean new billing cycle and avoids stacking expired days.

---

##  Technology Stack

- **Python 3**
- **Streamlit** (web UI)
- **PostgreSQL / NeonDB** (database)
- **psycopg2** (DB driver)
- **Pandas** (data processing)
- **VS Code** (development)
- **Git** (version control)

---

## 🗂 Project Structure

```
smart_delivery/
│
├── app.py                  # Main Streamlit UI and workflows
├── db.py                   # Database operations & business logic
├── requirements.txt        # Dependencies
├── README.md               # Documentation
└── .streamlit/
      └── secrets.toml      # Database credentials
```

---

##  Setup Instructions

### 1️⃣ Install Dependencies
```
pip install -r requirements.txt
```

## ▶️ 1.1 Create & Activate Virtual Environment (venv)

It is strongly recommended to run this project inside a **virtual environment** to keep your system clean and avoid package conflicts.

### 🔹 Create venv  
Inside your project folder, run:

```
python3 -m venv venv
```

### 🔹 Activate venv  
Mac / Linux:
```
source venv/bin/activate
```

Windows:
```
venv\Scripts\activate
```

After activation, your terminal will show:

```
(venv)
```

Now continue with the installation steps.

### 2️⃣ Configure Database (Neon / PostgreSQL)
Create:

```
.streamlit/secrets.toml
```

Add:

```
DB_HOST=""
DB_NAME=""
DB_USER=""
DB_PASSWORD=""
DB_SSLMODE="require"
```

### 3️⃣ Run the Application
```
streamlit run app.py
```

---

## 🧭 Operating the System

### 🔹 Admin Workflow
1. Log in using admin credentials  
2. Add customers and drivers  
3. Assign customers to driver routes  
4. Each day, update delivery statuses  
5. Review KPIs for delivery performance  
6. Renew subscriptions (only when owed = 0)  
7. Monitor Active/Expired subscriptions  

### 🔹 Driver Workflow
1. Log in using driver credentials  
2. View that day's assignment list  
3. Mark each delivery as Delivered / Missed / Paused  
4. Data syncs instantly to admin dashboard  

---

## 🧪 Testing the System

- Add sample customers with expired subscriptions  
- Assign customers to drivers for a specific date  
- Mark various deliveries to test owed logic  
- Renew customers with owed > 0 (should be blocked)  
- Renew customers with owed = 0 (should refresh cycle)  
- Log in as driver and test delivery marking  
- Validate KPI dashboard values  

---

## 🗄 Database Schema Summary

### customers
```
customer_id | full_name | phone_number | address | plan_name | location  
subscription_start | subscription_days | owed
```

### drivers
```
driver_id | full_name | phone
```

### assignments
```
assignment_id | customer_id | driver_id | assign_date
```

### deliveries
```
delivery_id | assignment_id | delivery_date | status | marked_by
```

### users
```
user_id | username | password | role | driver_id (nullable)
```

---

## 🌐 Deployment

Smart Delivery can be deployed on:

- **Streamlit Cloud**  
- **Any cloud VM with Python support**  

Requirements:
- PostgreSQL database accessible over SSL  
- `secrets.toml` properly configured  

---

## 🧰 Complete Setup Guide (Easy Step‑By‑Step)

This section explains **exactly what tools to install** and **how to run Smart Delivery on any computer** — even for beginners.

---

## 🛠 1. Tools You Must Install

### ✔ Python 3.10 or newer  
Download from: https://www.python.org/downloads/

### ✔ VS Code (Recommended)
Used to open and edit the project.  
Download: https://code.visualstudio.com/

### ✔ Git (Optional but recommended)
Used for version control.  
Download: https://git-scm.com/downloads

### ✔ PostgreSQL OR NeonDB  
NeonDB is recommended because the project is already configured for cloud DB.

---

## 📦 2. Install Required Python Libraries

Open a terminal inside the project folder and run:

```
pip install -r requirements.txt
```

This installs:

- streamlit  
- psycopg2-binary  
- pandas  
- other dependencies needed for the system  

---

## 🔑 3. Configure Database Connection

Create a folder:

```
.smart_delivery/.streamlit/
```

Inside that folder, create a file:

```
secrets.toml
```

Add your NeonDB credentials:

```
DB_HOST="your_host"
DB_NAME="your_db"
DB_USER="your_user"
DB_PASSWORD="your_password"
DB_SSLMODE="require"
```

These values come from your NeonDB dashboard.

---

## ▶️ 4. How to Run the Application

In the terminal:

```
streamlit run app.py
```

Streamlit will open automatically in your default browser:  
http://localhost:8501

---

## 🖥 5. How to Use the System (Beginner Friendly)

### 🔹 Admin Login
1. Log in using admin credentials  
2. Add customers  
3. Add drivers  
4. Assign customers to drivers  
5. Update delivery status daily  
6. Monitor KPIs  
7. Renew subscriptions only when owed = 0  

### 🔹 Driver Login
1. Driver logs in using driver credentials  
2. Views daily assigned customers  
3. Marks deliveries as Delivered / Missed / Paused  
4. Updates sync instantly to admin dashboard  

---

## 🧪 6. Testing Checklist (Simple)

- Add few customers with expired plans  
- Add drivers  
- Assign customers to drivers  
- Mark deliveries  
- Check owed increases/decreases correctly  
- Try renewing customers (owed MUST be 0)  
- Verify new subscription cycle starts  
- Check dashboard metrics  

---

## ☁️ 7. Deploying to Cloud (Streamlit Cloud)

1. Push your project to GitHub  
2. Go to https://share.streamlit.io  
3. Connect your repo  
4. Add DB secrets under "App Secrets"  
5. Deploy the app  

Your system will run online 24/7.

---

##  Contact

```
Smart Delivery – Capstone Project  
Developed by: Pavan Kalyan Pendyala, Musthaq Shaik 
Murray State University – Fall 2025
```

---

