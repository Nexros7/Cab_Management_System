import streamlit as st
import pandas as pd
import pymysql
import hashlib
from datetime import datetime

# ---------------------------
# CONFIG
# ---------------------------
DB_CONFIG = {
    "host": "localhost",
    "user": "souyash",
    "password": "soy123",
    "database": "dbms"
}

# ---------------------------
# DB HELPERS
# ---------------------------
def get_conn():
    return pymysql.connect(**DB_CONFIG, cursorclass=pymysql.cursors.DictCursor)

def run_query(query, params=None):
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute(query, params or ())
        rows = cur.fetchall()
        return pd.DataFrame(rows)
    finally:
        cur.close()
        conn.close()

def run_update(query, params=None):
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute(query, params or ())
        conn.commit()
    finally:
        cur.close()
        conn.close()

def run_proc(proc_name, params=None):
    conn = get_conn()
    cur = conn.cursor()
    try:
        if params:
            placeholders = ",".join(["%s"] * len(params))
            sql = f"CALL {proc_name}({placeholders})"
            cur.execute(sql, params)
        else:
            sql = f"CALL {proc_name}()"
            cur.execute(sql)

        conn.commit()

        rows = cur.fetchall()

        while cur.nextset():
            pass

        return pd.DataFrame(rows)
    finally:
        cur.close()
        conn.close()

# ---------------------------
# AUTH
# ---------------------------
def sha256(txt):
    return hashlib.sha256(txt.encode()).hexdigest()

def ensure_app_users_table():
    try:
        df = run_query(
            "SELECT COUNT(*) AS c FROM information_schema.TABLES WHERE TABLE_SCHEMA=%s AND TABLE_NAME='APP_USERS'",
            (DB_CONFIG["database"],)
        )
        if df["c"].iloc[0] == 0:
            run_update("""
            CREATE TABLE APP_USERS (
                user_id INT AUTO_INCREMENT PRIMARY KEY,
                username VARCHAR(50) UNIQUE NOT NULL,
                password VARCHAR(256) NOT NULL,
                role ENUM('admin','user') NOT NULL DEFAULT 'user'
            );
            """)
            run_update(
                "INSERT INTO APP_USERS(username,password,role) VALUES(%s,%s,%s)",
                ("admin", sha256("admin123"), "admin")
            )
            st.info("APP_USERS table created with default admin/admin123")
    except Exception as e:
        st.error(f"Startup user table error: {e}")

def verify_user(username, password):
    hashed = sha256(password)
    df = run_query(
        "SELECT * FROM APP_USERS WHERE username=%s AND password=%s",
        (username, hashed)
    )
    return df.iloc[0].to_dict() if not df.empty else None

def create_app_user(username, password, role="user"):
    run_update(
        "INSERT INTO APP_USERS(username,password,role) VALUES(%s,%s,%s)",
        (username, sha256(password), role)
    )

# ---------------------------
# STREAMLIT INIT (remove hamburger menu)
# ---------------------------
st.set_page_config(
    page_title="Taxi Cab Management System",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={}       # REMOVES 3-DOT MENU + DEPLOY
)

# Init session vars
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "username" not in st.session_state:
    st.session_state.username = None
if "role" not in st.session_state:
    st.session_state.role = None
if "show_signup" not in st.session_state:
    st.session_state.show_signup = False

ensure_app_users_table()

# ---------------------------
# LOGIN / SIGNUP
# ---------------------------
if not st.session_state.logged_in:

    st.title("🔐 Login")

    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        user = verify_user(username, password)
        if user:
            st.session_state.logged_in = True
            st.session_state.username = user["username"]
            st.session_state.role = user["role"]
            st.rerun()
        else:
            st.error("Invalid username/password")

    st.write("Don't have an account?")
    if st.button("Sign up"):
        st.session_state.show_signup = True
        st.rerun()

    # SIGNUP SCREEN
    if st.session_state.show_signup:
        st.subheader("📝 Sign Up")
        new_user = st.text_input("New Username", key="su1")
        new_pass = st.text_input("New Password", type="password", key="su2")
        new_role = st.selectbox("Role", ["user", "admin"], key="su3")

        if st.button("Create Account"):
            try:
                create_app_user(new_user, new_pass, new_role)
                st.success("Account created! Please login.")
                st.session_state.show_signup = False
                st.rerun()
            except Exception as e:
                st.error(e)

        if st.button("Back to Login"):
            st.session_state.show_signup = False
            st.rerun()

    st.stop()

# ---------------------------
# MAIN APP
# ---------------------------
st.sidebar.markdown(f"**Logged in as:** {st.session_state.username}")
st.sidebar.markdown(f"**Role:** {st.session_state.role}")

if st.sidebar.button("Logout"):
    st.session_state.logged_in = False
    st.session_state.username = None
    st.session_state.role = None
    st.rerun()

# MENU
menu_items = [
    "Dashboard",
    "View Tables",
    "Add Booking",
    "Add Driver",
    "Delete Booking",
    "Driver Procedures",
    "Run Custom SQL",
]

# REMOVE HELP COMPLETELY
if st.session_state.role == "admin":
    menu_items.append("User Management")

menu = st.sidebar.radio("Navigation", menu_items)

# ---------------------------
# DASHBOARD
# ---------------------------
if menu == "Dashboard":
    st.header("📊 Dashboard Overview")

    try:
        tables = ["DRIVERS", "CARS", "CLIENTS", "BOOKINGS"]
        cols = st.columns(len(tables))

        for i, tbl in enumerate(tables):
            df = run_query(f"SELECT COUNT(*) AS c FROM {tbl}")
            count = df["c"][0] if not df.empty else 0
            cols[i].metric(tbl, count)

        st.subheader("Recent Bookings")
        df = run_query("""
            SELECT booking_id, d_id, client_id, pickup_location, destination,
                   price, payment_type, time_of_booking
            FROM BOOKINGS ORDER BY booking_id DESC LIMIT 10
        """)
        st.dataframe(df)
    except Exception as e:
        st.error(e)

# ---------------------------
# VIEW TABLES
# ---------------------------
elif menu == "View Tables":
    st.header(" View Tables")
    tables = run_query("SHOW TABLES;")
    names = [list(t.values())[0] for t in tables.to_dict("records")]
    choice = st.selectbox("Choose table:", names)
    df = run_query(f"SELECT * FROM {choice}")
    st.dataframe(df)

# ---------------------------
# ADD BOOKING
# ---------------------------
elif menu == "Add Booking":
    st.header(" Add Booking")

    with st.form("add_book"):
        op = st.number_input("Operator ID", value=201)
        drv = st.number_input("Driver ID", value=101)
        cli = st.number_input("Client ID", value=301)
        btype = st.selectbox("Booking Type", ["Cab", "Pool", "Parcel"])
        t1 = st.text_input("Time of Booking", value=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        t2 = st.text_input("Pickup Time", value=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        loc = st.text_input("Pickup Location")
        dst = st.text_input("Destination")
        pay = st.selectbox("Payment Type", ["CARD", "CASH"])
        price = st.number_input("Price", min_value=1, value=100)
        submit = st.form_submit_button("Add Booking")

    if submit:
        try:
            run_proc("AddBooking", (op, drv, cli, btype, t1, t2, loc, dst, pay, price))
            st.success("Booking added!")
        except Exception as e:
            st.error(e)

# ---------------------------
# ADD DRIVER
# ---------------------------
elif menu == "Add Driver":
    st.header(" Add Driver")

    with st.form("add_driver"):
        did = st.number_input("Driver ID", value=106)
        fn = st.text_input("First Name")
        ln = st.text_input("Last Name")
        addr = st.text_input("Address")
        gen = st.selectbox("Gender", ["M", "F", "O"])
        phone = st.text_input("Phone")
        dob = st.date_input("Date of Birth")
        doj = st.date_input("Date Employed")
        aad = st.text_input("Aadhaar Number")
        submit = st.form_submit_button("Add Driver")

    if submit:
        try:
            run_proc("AddDriver", (did, fn, ln, addr, gen, phone,
                                   dob.strftime("%Y-%m-%d"),
                                   doj.strftime("%Y-%m-%d"),
                                   aad))
            st.success("Driver added!")
        except Exception as e:
            st.error(e)

# ---------------------------
# DELETE BOOKING
# ---------------------------
elif menu == "Delete Booking":
    st.header(" Delete Booking")

    df = run_query("SELECT booking_id FROM BOOKINGS ORDER BY booking_id DESC")
    if df.empty:
        st.info("No bookings found.")
    else:
        bid = st.selectbox("Choose booking:", df["booking_id"])
        if st.button("Delete"):
            run_update("DELETE FROM BOOKINGS WHERE booking_id=%s", (bid,))
            st.success("Deleted!")

# ---------------------------
# DRIVER PROCEDURES
# ---------------------------
elif menu == "Driver Procedures":
    st.header(" Driver Procedures")

    choice = st.selectbox("Choose procedure", [
        "GetDriverBookings",
        "GetDriverShift",
        "GetAvailableCars",
        "GetDriverTotalRevenue (FUNCTION)"
    ])

    needs_id = choice in ["GetDriverBookings", "GetDriverShift", "GetDriverTotalRevenue (FUNCTION)"]

    if needs_id:
        did = st.number_input("Driver ID", value=101)

    if st.button("Run Procedure"):
        try:
            # function call
            if choice == "GetDriverTotalRevenue (FUNCTION)":
                df = run_query("SELECT GetDriverTotalRevenue(%s) AS total_revenue;", (did,))
                st.dataframe(df)

            # normal stored procedures
            else:
                df = run_proc(choice, (did,)) if needs_id else run_proc(choice)
                st.dataframe(df)
        except Exception as e:
            st.error(e)

# ---------------------------
# RUN CUSTOM SQL – CLEANED VERSION
# ---------------------------
elif menu == "Run Custom SQL":
    st.header(" Nested Query Example")

    if st.button("Show Drivers With Above-Average Revenue"):
        try:
            sql = """
            SELECT d_id, revenue
            FROM REVENUE
            WHERE revenue > (SELECT AVG(revenue) FROM REVENUE);
            """
            df = run_query(sql)
            st.dataframe(df)
        except Exception as e:
            st.error(e)

# ---------------------------
# USER MANAGEMENT (Admin only)
# ---------------------------
elif menu == "User Management":
    if st.session_state.role != "admin":
        st.error("Admins only.")
        st.stop()

    st.header(" User Management")

    newU = st.text_input("New Username")
    newP = st.text_input("Password", type="password")
    newR = st.selectbox("Role", ["user", "admin"])
    
    if st.button("Create"):
        try:
            create_app_user(newU, newP, newR)
            st.success("User created.")
        except Exception as e:
            st.error(e)
