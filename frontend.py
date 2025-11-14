# app.py
import streamlit as st
import pandas as pd
import pymysql
from datetime import datetime

# ---------------------------
# 🔧 DATABASE CONFIGURATION
# ---------------------------
DB_CONFIG = {
    "host": "localhost",
    "user": "souyash",      
    "password": "soy123",   
    "database": "dbms_proj"
}

# ---------------------------
# 🧩 DATABASE HELPERS
# ---------------------------
def get_conn():
    return pymysql.connect(**DB_CONFIG, cursorclass=pymysql.cursors.DictCursor)

def run_query(query, params=None):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(query, params or ())
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return pd.DataFrame(rows)

def run_update(query, params=None):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(query, params or ())
    conn.commit()
    cur.close()
    conn.close()

def run_proc(proc_name, params=None):
    conn = get_conn()
    cur = conn.cursor()
    cur.callproc(proc_name, params or ())
    results = []
    for result in cur.stored_results():
        results.extend(result.fetchall())
    cur.close()
    conn.close()
    return pd.DataFrame(results)

def test_connection():
    try:
        conn = get_conn()
        conn.close()
        st.success("✅ Connected to MySQL successfully as 'souyash'!")
        return True
    except Exception as e:
        st.error(f"❌ Connection failed: {e}")
        return False

# ---------------------------
# 🚕 STREAMLIT UI
# ---------------------------
st.set_page_config(page_title="Taxi Cab Management System", layout="wide")
st.title("🚖 Taxi Cab Management System")

if test_connection():
    menu = st.sidebar.radio(
        "Navigation",
        [
            "Dashboard",
            "View Tables",
            "Add Booking",
            "Delete Booking",
            "Car Assignment",
            "Driver Procedures",
            "Run Custom SQL"
        ]
    )

    # ---------------------------
    # 📊 DASHBOARD
    # ---------------------------
    if menu == "Dashboard":
        st.header("📊 Dashboard Overview")

        tables = ["DRIVERS", "CARS", "CLIENTS", "BOOKINGS"]
        cols = st.columns(len(tables))
        for i, tbl in enumerate(tables):
            try:
                count = run_query(f"SELECT COUNT(*) AS count FROM {tbl}")
                cols[i].metric(tbl, count['count'][0])
            except:
                cols[i].metric(tbl, "N/A")

        st.subheader("Recent Bookings")
        df = run_query("SELECT * FROM BOOKINGS ORDER BY time_of_booking DESC LIMIT 10")
        st.dataframe(df)

    # ---------------------------
    # 📄 VIEW TABLES
    # ---------------------------
    elif menu == "View Tables":
        st.header("📋 View Database Tables")
        tables = run_query("SHOW TABLES;")
        if not tables.empty:
            tbl_name = st.selectbox("Select Table", [list(t.values())[0] for t in tables.to_dict('records')])
            df = run_query(f"SELECT * FROM {tbl_name}")
            st.dataframe(df)
        else:
            st.warning("No tables found in the database.")

    # ---------------------------
    # ➕ ADD BOOKING
    # ---------------------------
    elif menu == "Add Booking":
        st.header("➕ Add Booking (via stored procedure `AddBooking`)")
        with st.form("add_booking_form"):
            op_id = st.number_input("Operator ID", min_value=1, value=201)
            d_id = st.number_input("Driver ID", min_value=1, value=101)
            client_id = st.number_input("Client ID", min_value=1, value=301)
            type_booking = st.selectbox("Booking Type", ["Cab", "Pool", "Parcel"])
            time_booking = st.text_input("Time of Booking (YYYY-MM-DD HH:MM:SS)",
                                         value=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            pickup_time = st.text_input("Pickup Time (YYYY-MM-DD HH:MM:SS)",
                                        value=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            pickup_loc = st.text_input("Pickup Location", "MG Road")
            destination = st.text_input("Destination", "Airport")
            payment_type = st.selectbox("Payment Type", ["CARD", "CASH"])
            price = st.number_input("Price", min_value=1)
            submit = st.form_submit_button("Add Booking")

        if submit:
            try:
                conn = get_conn()
                cur = conn.cursor()
                cur.callproc("AddBooking", (
                    op_id, d_id, client_id, type_booking, time_booking, pickup_time,
                    pickup_loc, destination, payment_type, price
                ))
                conn.commit()
                conn.close()
                st.success("✅ Booking added successfully!")
            except Exception as e:
                st.error(f"Error adding booking: {e}")

    # ---------------------------
    # ❌ DELETE BOOKING
    # ---------------------------
    elif menu == "Delete Booking":
        st.header("❌ Delete Booking (Trigger `log_deleted_booking` will run automatically)")
        df = run_query("SELECT booking_id, pickup_location, destination FROM BOOKINGS ORDER BY booking_id DESC")
        if not df.empty:
            bid = st.selectbox("Select Booking ID", df["booking_id"])
            if st.button("Delete Booking"):
                try:
                    run_update("DELETE FROM BOOKINGS WHERE booking_id = %s", (bid,))
                    st.success("✅ Booking deleted (logged automatically).")
                except Exception as e:
                    st.error(f"Error deleting booking: {e}")
        else:
            st.info("No bookings found.")

    # ---------------------------
    # 🚗 UPDATE CAR ASSIGNMENT
    # ---------------------------
    elif menu == "Car Assignment":
        st.header("🚗 Assign/Unassign Driver (Trigger `update_car_status` fires on update)")
        cars = run_query("SELECT registration, car_make, car_model, d_id, status FROM CARS")
        reg = st.selectbox("Select Car Registration", cars["registration"])
        new_driver = st.text_input("New Driver ID (leave blank to unassign)")
        if st.button("Update Assignment"):
            d_val = new_driver if new_driver.strip() != "" else None
            try:
                run_update("UPDATE CARS SET d_id = %s WHERE registration = %s", (d_val, reg))
                st.success("✅ Car assignment updated successfully!")
            except Exception as e:
                st.error(f"Error updating car assignment: {e}")

    # ---------------------------
    # 👨‍✈️ DRIVER PROCEDURES
    # ---------------------------
    elif menu == "Driver Procedures":
        st.header("👨‍✈️ Driver Stored Procedures")
        proc = st.selectbox("Select Procedure", [
            "GetDriverBookings", "GetDriverRevenue", "GetDriverShift", "GetAvailableCars"
        ])
        if proc != "GetAvailableCars":
            driver_id = st.number_input("Driver ID", min_value=1, value=101)
        if st.button("Run Procedure"):
            try:
                if proc == "GetAvailableCars":
                    df = run_proc(proc)
                else:
                    df = run_proc(proc, (driver_id,))
                if df.empty:
                    st.info("No results found.")
                else:
                    st.dataframe(df)
            except Exception as e:
                st.error(f"Error running procedure: {e}")

    # ---------------------------
    # 🧠 CUSTOM SQL
    # ---------------------------
    elif menu == "Run Custom SQL":
        st.header("🧮 Run Custom SQL")
        sql = st.text_area("Enter your SQL statement (SELECT only recommended)")
        if st.button("Execute"):
            try:
                if sql.strip().lower().startswith("select"):
                    df = run_query(sql)
                    st.dataframe(df)
                else:
                    run_update(sql)
                    st.success("✅ Query executed successfully.")
            except Exception as e:
                st.error(f"Error: {e}")
