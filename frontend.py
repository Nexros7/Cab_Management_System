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
    """
    Executes a SELECT (or other that returns rows) and returns a pandas DataFrame.
    """
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
    """
    Executes an INSERT/UPDATE/DELETE (writes).
    """
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute(query, params or ())
        conn.commit()
    finally:
        cur.close()
        conn.close()

def run_proc(proc_name, params=None):
    """
    Execute stored procedure using CALL proc_name(...) to avoid stored_results issues.
    Returns DataFrame of the first resultset (or empty DF).
    """
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

        # commit for procedures that perform writes
        conn.commit()

        rows = cur.fetchall()
        # consume remaining resultsets if any
        while cur.nextset():
            pass

        return pd.DataFrame(rows)
    finally:
        cur.close()
        conn.close()

# ---------------------------
# AUTH HELPERS
# ---------------------------
def sha256(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()

def ensure_app_users_table():
    """
    Create APP_USERS table and default admin if not present.
    """
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
            ) ENGINE=InnoDB;
            """)
            # default admin (admin/admin123)
            run_update("INSERT INTO APP_USERS(username, password, role) VALUES(%s, %s, %s)",
                       ("admin", sha256("admin123"), "admin"))
            st.info("APP_USERS table created with default admin/admin123.")
    except Exception as e:
        st.error(f"Could not ensure APP_USERS table: {e}")

def verify_user(username, password):
    hashed = sha256(password)
    try:
        df = run_query("SELECT user_id, username, role FROM APP_USERS WHERE username=%s AND password=%s",
                       (username, hashed))
    except Exception as e:
        st.error(f"Auth DB error: {e}")
        return None
    return df.iloc[0].to_dict() if not df.empty else None

def create_app_user(username, password, role="user"):
    hashed = sha256(password)
    run_update("INSERT INTO APP_USERS(username, password, role) VALUES(%s, %s, %s)",
               (username, hashed, role))

# ---------------------------
# SESSION INITIALIZATION
# ---------------------------
st.set_page_config(page_title="Taxi Cab Management System", layout="wide")
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user = None
    st.session_state.show_signup = False

# Ensure APP_USERS exists on startup
ensure_app_users_table()

# ---------------------------
# LOGIN / SIGNUP UI (shown when not logged in)
# ---------------------------
if not st.session_state.logged_in:
    st.title("🔐 Login")

    left, right = st.columns([3, 1])
    with left:
        username = st.text_input("Username", key="login_username")
        password = st.text_input("Password", type="password", key="login_password")
    with right:
        if st.button("Login"):
            user = verify_user(username, password)
            if user:
                st.session_state.logged_in = True
                st.session_state.user = user
                st.success(f"Welcome, {user['username']}!")
                st.experimental_rerun()
            else:
                st.error("Invalid username/password")

    st.markdown("---")
    st.write("Don't have an account?")

    if st.button("Sign up"):
        st.session_state.show_signup = True
        st.experimental_rerun()

    if st.session_state.show_signup:
        st.header("📝 Sign up")
        new_user = st.text_input("New username", key="su_username")
        new_pass = st.text_input("New password", type="password", key="su_password")
        new_role = st.selectbox("Role", ["user", "admin"], key="su_role")
        if st.button("Create account"):
            try:
                create_app_user(new_user, new_pass, new_role)
                st.success("Account created. Please login.")
                st.session_state.show_signup = False
            except Exception as e:
                st.error(f"Could not create account: {e}")
        if st.button("Back to Login"):
            st.session_state.show_signup = False
            st.experimental_rerun()

    st.stop()

# ---------------------------
# MAIN APP (after login) - Option A sidebar
# ---------------------------
current_user = st.session_state.user
st.sidebar.markdown(f"**Logged in as:** {current_user['username']}")
st.sidebar.markdown(f"**Role:** {current_user['role']}")
if st.sidebar.button("Logout"):
    st.session_state.logged_in = False
    st.session_state.user = None
    st.experimental_rerun()

menu_items = [
    "Dashboard",
    "View Tables",
    "Add Booking",
    "Add Driver",
    "Delete Booking",
    "Driver Procedures",
    "Run Custom SQL"
]
if current_user["role"] == "admin":
    menu_items.append("User Management")
else:
    menu_items.append("Help")

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
            try:
                cnt = run_query(f"SELECT COUNT(*) AS cnt FROM {tbl}")
                val = int(cnt['cnt'][0]) if not cnt.empty else 0
                cols[i].metric(tbl, val)
            except Exception:
                cols[i].metric(tbl, "N/A")

        st.subheader("Recent Bookings")
        recent = run_query("SELECT booking_id, d_id, client_id, pickup_location, destination, price, payment_type, time_of_booking FROM BOOKINGS ORDER BY time_of_booking DESC LIMIT 10")
        if recent.empty:
            st.info("No bookings found.")
        else:
            st.dataframe(recent)
    except Exception as e:
        st.error(f"Dashboard error: {e}")

# ---------------------------
# VIEW TABLES
# ---------------------------
elif menu == "View Tables":
    st.header("📋 View Database Tables")
    try:
        tables = run_query("SHOW TABLES;")
        if tables.empty:
            st.info("No tables found.")
        else:
            tbl_names = [list(t.values())[0] for t in tables.to_dict("records")]
            chosen = st.selectbox("Select table", tbl_names)
            df = run_query(f"SELECT * FROM {chosen} LIMIT 1000")
            st.dataframe(df)
    except Exception as e:
        st.error(f"Error showing tables: {e}")

# ---------------------------
# ADD BOOKING (via stored proc)
# ---------------------------
elif menu == "Add Booking":
    st.header("➕ Add Booking (uses stored procedure AddBooking)")
    with st.form("add_booking_form"):
        op_id = st.number_input("Operator ID", min_value=1, value=201)
        d_id = st.number_input("Driver ID", min_value=1, value=101)
        client_id = st.number_input("Client ID", min_value=1, value=301)
        type_booking = st.selectbox("Booking Type", ["Cab", "Pool", "Parcel"])
        time_booking = st.text_input("Time of Booking (YYYY-MM-DD HH:MM:SS)", value=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        pickup_time = st.text_input("Pickup Time (YYYY-MM-DD HH:MM:SS)", value=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        pickup_loc = st.text_input("Pickup Location", "MG Road")
        destination = st.text_input("Destination", "Airport")
        payment_type = st.selectbox("Payment Type", ["CARD", "CASH", "UPI"])
        price = st.number_input("Price", min_value=1, value=100)
        submitted = st.form_submit_button("Add Booking")
    if submitted:
        try:
            # call AddBooking stored procedure
            run_proc("AddBooking", (op_id, d_id, client_id, type_booking, time_booking, pickup_time, pickup_loc, destination, payment_type, price))
            st.success("Booking added successfully.")
        except Exception as e:
            st.error(f"Error adding booking: {e}")

# ---------------------------
# ADD DRIVER (via stored proc)
# ---------------------------
elif menu == "Add Driver":
    st.header("➕ Add Driver (uses stored procedure AddDriver)")
    with st.form("add_driver_form"):
        d_id = st.number_input("Driver ID", min_value=1, value=106)
        f_name = st.text_input("First name")
        l_name = st.text_input("Last name")
        address = st.text_input("Address")
        gender = st.selectbox("Gender", ["M", "F", "O"])
        phone = st.text_input("Phone")
        dob = st.date_input("Date of birth")
        doj = st.date_input("Date employed")
        aadhaar = st.text_input("Aadhaar number")
        drv_submitted = st.form_submit_button("Add Driver")
    if drv_submitted:
        try:
            run_proc("AddDriver", (d_id, f_name, l_name, address, gender, phone, dob.strftime("%Y-%m-%d"), doj.strftime("%Y-%m-%d"), aadhaar))
            st.success("Driver added successfully.")
        except Exception as e:
            st.error(f"Error adding driver: {e}")

# ---------------------------
# DELETE BOOKING
# ---------------------------
elif menu == "Delete Booking":
    st.header("❌ Delete Booking")
    try:
        df = run_query("SELECT booking_id, pickup_location, destination FROM BOOKINGS ORDER BY booking_id DESC")
        if df.empty:
            st.info("No bookings available.")
        else:
            bid = st.selectbox("Select Booking ID to delete", df["booking_id"])
            if st.button("Delete Booking"):
                try:
                    run_update("DELETE FROM BOOKINGS WHERE booking_id=%s", (bid,))
                    st.success("Booking deleted.")
                except Exception as e:
                    st.error(f"Error deleting booking: {e}")
    except Exception as e:
        st.error(f"Error loading bookings: {e}")

# ---------------------------
# DRIVER PROCEDURES
# ---------------------------
elif menu == "Driver Procedures":
    st.header("👨‍✈️ Driver Procedures")
    proc = st.selectbox("Choose procedure", ["GetDriverBookings", "GetDriverShift", "GetAvailableCars"])
    param = None
    if proc in ("GetDriverBookings", "GetDriverShift", "GetDriverTotalRevenue"):
        param = st.number_input("Driver ID", min_value=1, value=101)
    if st.button("Run Procedure"):
        try:
            if param is None:
                df = run_proc(proc)
            else:
                df = run_proc(proc, (param,))
            if df.empty:
                st.info("No results.")
            else:
                st.dataframe(df)
        except Exception as e:
            st.error(f"Stored procedure error: {e}")

elif menu == "Run Custom SQL":
    st.header("🧮 Run Custom SQL / Nested Query Examples")

    # --- Button to run nested query ---
    if st.button("Show Drivers With Above-Average Revenue (Nested Query)"):
        try:
            nested_sql = """
                SELECT d_id, revenue
                FROM REVENUE
                WHERE revenue > (
                    SELECT AVG(revenue)
                    FROM REVENUE
                );
            """
            df = run_query(nested_sql)
            if df.empty:
                st.info("No results found.")
            else:
                st.dataframe(df)
        except Exception as e:
            st.error(f"Nested Query Error: {e}")

# ---------------------------
# USER MANAGEMENT (Admin only)
# ---------------------------
elif menu == "User Management":
    if current_user["role"] != "admin":
        st.error("Admin access only.")
        st.stop()

    st.header("👤 User Management (Admin)")
    st.subheader("Create App User")
    new_app_user = st.text_input("App username")
    new_app_pass = st.text_input("App password", type="password")
    new_app_role = st.selectbox("Role", ["user", "admin"])
    if st.button("Create App User"):
        try:
            create_app_user(new_app_user, new_app_pass, new_app_role)
            st.success("App user created.")
        except Exception as e:
            st.error(f"Error creating app user: {e}")

    st.markdown("---")
    st.subheader("Create DB User (requires DB privilege)")
    db_user = st.text_input("DB username", key="db_user")
    db_pass = st.text_input("DB password", type="password", key="db_pass")
    if st.button("Create DB user"):
        try:
            run_update(f"CREATE USER '{db_user}'@'localhost' IDENTIFIED BY '{db_pass}'")
            st.success("DB user created (if your DB account has privileges).")
        except Exception as e:
            st.error(f"DB user creation error: {e}")

    st.markdown("---")
    st.subheader("Grant / Revoke DB Privileges")
    grant_user = st.text_input("Grant to DB user", key="grant_to")
    grant_priv = st.selectbox("Privilege to grant", ["SELECT", "INSERT", "UPDATE", "DELETE", "ALL PRIVILEGES"], key="grant_priv")
    if st.button("Grant Privilege"):
        try:
            run_update(f"GRANT {grant_priv} ON {DB_CONFIG['database']}.* TO '{grant_user}'@'localhost'")
            st.success("Granted privileges (if permitted).")
        except Exception as e:
            st.error(f"Grant error: {e}")

    revoke_user = st.text_input("Revoke from DB user", key="revoke_from")
    revoke_priv = st.selectbox("Privilege to revoke", ["SELECT", "INSERT", "UPDATE", "DELETE", "ALL PRIVILEGES"], key="revoke_priv")
    if st.button("Revoke Privilege"):
        try:
            run_update(f"REVOKE {revoke_priv} ON {DB_CONFIG['database']}.* FROM '{revoke_user}'@'localhost'")
            st.success("Revoked privileges (if permitted).")
        except Exception as e:
            st.error(f"Revoke error: {e}")


