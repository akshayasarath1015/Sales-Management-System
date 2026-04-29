import streamlit as st
import mysql.connector
import pandas as pd
from datetime import date

st.set_page_config(page_title="Sales System", layout="wide")

# Database
def connect():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="",
        database="Sales_Management_System"
    )

# Session
if "user" not in st.session_state:
    st.session_state["user"] = None

# Login
def login(username, password):
    conn = connect()
    cur = conn.cursor()
    cur.execute("""
        SELECT user_id, username, role, branch_id
        FROM users
        WHERE username=%s AND password=%s
    """, (username, password))
    user = cur.fetchone()
    conn.close()
    return user

# Login Page
if st.session_state["user"] is None:
    st.title("Login")

    u = st.text_input("Username")
    p = st.text_input("Password", type="password")

    if st.button("Login"):
        user = login(u, p)
        if user:
            st.session_state["user"] = user
            st.rerun()
        else:
            st.error("Invalid credentials")

# Main App
else:
    user_id, username, role, branch_id = st.session_state["user"]

    st.sidebar.title("Menu")
    page = st.sidebar.radio("Go to", [
        "Dashboard",
        "Add Sales",
        "Add Payment",
        "SQL Queries"
    ])

    if st.sidebar.button("Logout"):
        st.session_state["user"] = None
        st.rerun()

    conn = connect()

# Dashboard
    if page == "Dashboard":

        st.title("Dashboard")
        st.info(f"User: {username} | Role: {role}")

        # Min Date
        min_date = pd.read_sql(
            "SELECT MIN(date) AS min_date FROM customer_sales", conn
        ).iloc[0]["min_date"]

        if pd.isna(min_date):
            min_date = date.today()

        # Branch list
        branch_df = pd.read_sql("SELECT * FROM branches", conn)

        col1, col2, col3 = st.columns(3)

        # Branch Filter
        with col1:
            if role == "Super Admin":
                branch_filter = st.selectbox(
                    "Branch", ["All"] + branch_df["branch_name"].tolist()
                )
            else:
                branch_filter = branch_df[
                    branch_df["branch_id"] == branch_id
                ]["branch_name"].values[0]
                st.text_input("Branch", value=branch_filter, disabled=True)

        # Status Filter
        with col2:
            status_filter = st.selectbox("Status", ["All", "Open", "Closed"])

        # Date Filter
        with col3:
            start_date = st.date_input("Start Date", value=min_date)

        end_date = st.date_input("End Date", value=date.today())

        query = """
        SELECT 
            cs.sale_id,
            cs.date,
            cs.name,
            b.branch_name,
            cs.product_name,
            cs.gross_sales,
            IFNULL(SUM(ps.amount_paid),0) AS received,
            cs.gross_sales - IFNULL(SUM(ps.amount_paid),0) AS pending
        FROM customer_sales cs
        LEFT JOIN payment_splits ps ON cs.sale_id = ps.sale_id
        JOIN branches b ON cs.branch_id = b.branch_id
        WHERE cs.date BETWEEN %s AND %s
        """

        params = [start_date, end_date]

        if role != "Super Admin":
            query += " AND cs.branch_id=%s"
            params.append(branch_id)

        if role == "Super Admin" and branch_filter != "All":
            query += " AND b.branch_name=%s"
            params.append(branch_filter)

        query += " GROUP BY cs.sale_id ORDER BY cs.date DESC"

        df = pd.read_sql(query, conn, params=params)

        if not df.empty:

            df["status"] = df["pending"].apply(
                lambda x: "Open" if x > 0 else "Closed"
            )

            if status_filter != "All":
                df = df[df["status"] == status_filter]

            st.subheader("KPI Summary")

            total_sales = df["gross_sales"].sum()
            total_received = df["received"].sum()
            total_pending = df["pending"].sum()

            c1, c2, c3 = st.columns(3)
            c1.metric("Sales", int(total_sales))
            c2.metric("Received", int(total_received))
            c3.metric("Pending", int(total_pending))

            if total_sales > 0:
                st.metric("Pending %", f"{(total_pending/total_sales)*100:.2f}%")

            # ✅ PRODUCT BUTTON (FIXED)
            col_btn1, col_btn2 = st.columns(2)

            with col_btn1:
                if st.button("View Product List"):
                    st.session_state["show_products"] = True

            with col_btn2:
                if st.button("Hide Product List"):
                    st.session_state["show_products"] = False

            # ✅ PRODUCT LIST
            if st.session_state["show_products"]:

                st.subheader("Product Summary")

                product_query = """
                SELECT 
                    cs.product_name,
                    COUNT(*) AS total_orders,
                    SUM(cs.gross_sales) AS total_sales
                FROM customer_sales cs
                JOIN branches b ON cs.branch_id = b.branch_id
                WHERE cs.date BETWEEN %s AND %s
                """

                product_params = [start_date, end_date]

                if role != "Super Admin":
                    product_query += " AND cs.branch_id=%s"
                    product_params.append(branch_id)

                if role == "Super Admin" and branch_filter != "All":
                    product_query += " AND b.branch_name=%s"
                    product_params.append(branch_filter)

                product_query += """
                GROUP BY cs.product_name
                ORDER BY total_sales DESC
                """

                product_df = pd.read_sql(product_query, conn, params=product_params)

                st.dataframe(product_df, use_container_width=True)


            st.subheader("Payment Summary")

            pay_df = pd.read_sql("""
                SELECT payment_method, SUM(amount_paid) total
                FROM payment_splits GROUP BY payment_method
            """, conn)

            st.dataframe(pay_df, use_container_width=True)

            st.subheader("Sales Data")
            st.dataframe(df, use_container_width=True)

        else:
            st.warning("No data found")
        
        
# Add Sales
    elif page == "Add Sales":

        st.title("Add Sales")

        branch_df = pd.read_sql("SELECT * FROM branches", conn)

        name = st.text_input("Customer Name")
        mobile = st.text_input("Mobile")
        product = st.selectbox("Product", ["DS", "DA", "BA", "FSD"])
        amount = st.number_input("Amount", min_value=0)

        if role == "Super Admin":
            branch = st.selectbox("Branch", branch_df["branch_name"])
            branch_id_sel = branch_df[
                branch_df["branch_name"] == branch
            ]["branch_id"].values[0]
        else:
            branch_id_sel = branch_id

        if st.button("Save"):
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO customer_sales
                (date, name, mobile_number, product_name, gross_sales, branch_id)
                VALUES (%s,%s,%s,%s,%s,%s)
            """, (date.today(), name, mobile, product, amount, branch_id_sel))
            conn.commit()
            st.success("Sales added")

# Add Payment
    elif page == "Add Payment":

        st.title("Add Payment")

        if role == "Super Admin":
            sales_df = pd.read_sql("SELECT sale_id FROM customer_sales", conn)
        else:
            sales_df = pd.read_sql(
                "SELECT sale_id FROM customer_sales WHERE branch_id=%s",
                conn, params=[branch_id]
            )

        sale_id = st.selectbox("Sale ID", sales_df["sale_id"])
        amount = st.number_input("Amount", min_value=0)
        method = st.selectbox("Method", ["Cash", "UPI", "Card"])

        if st.button("Add"):
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO payment_splits
                (sale_id, amount_paid, payment_method)
                VALUES (%s,%s,%s)
            """, (sale_id, amount, method))
            conn.commit()
            st.success("Payment added")

         # SQL QUERIES
    elif page == "SQL Queries":

        st.title("SQL Queries")

        query_options = {
            "1. Retrieve all records from the customer_sales table.": "SELECT * FROM customer_sales;",
            "2. Retrieve all records from the branches table.": "SELECT * FROM branches;",
            "3. Retrieve all records from the payment_splits table.": "SELECT * FROM payment_splits;",
            "4. Display all sales with status = Open.": """                
                SELECT cs.sale_id,
                cs.name,
                b.branch_name,
                cs.gross_sales,
                IFNULL(SUM(ps.amount_paid),0) AS received,
                cs.gross_sales - IFNULL(SUM(ps.amount_paid),0) AS pending
                FROM customer_sales cs
                JOIN branches b ON cs.branch_id = b.branch_id
                LEFT JOIN payment_splits ps ON cs.sale_id = ps.sale_id
                GROUP BY cs.sale_id, cs.name, b.branch_name, cs.gross_sales
                HAVING pending > 0;
            """,
            "5. Retrieve all sales belonging to Chennai branch.": """
                SELECT cs.*, b.branch_name
                FROM customer_sales cs
                JOIN branches b ON cs.branch_id = b.branch_id
                WHERE b.branch_name='Chennai';
            """,
            "6. Calculate total sales.": "SELECT SUM(gross_sales) FROM customer_sales;",
            "7. Calculate total received.": "SELECT SUM(amount_paid) FROM payment_splits;",
            "8. Calculate total pending.": """
                SELECT SUM(cs.gross_sales - IFNULL(ps.total_paid,0))
                FROM customer_sales cs
                LEFT JOIN (
                    SELECT sale_id, SUM(amount_paid) AS total_paid
                    FROM payment_splits GROUP BY sale_id
                ) ps ON cs.sale_id = ps.sale_id;
            """,
            "9. Count sales per branch.": """
                SELECT b.branch_name, COUNT(cs.sale_id)
                FROM customer_sales cs
                JOIN branches b ON cs.branch_id = b.branch_id
                GROUP BY b.branch_name;
            """,
            "10. Average sales.": "SELECT AVG(gross_sales) FROM customer_sales;",
            "11. Sales with branch.": """
                SELECT cs.*, b.branch_name
                FROM customer_sales cs
                JOIN branches b ON cs.branch_id = b.branch_id;
            """,
            "12. Sales with payments.": """
                SELECT cs.sale_id, cs.name, SUM(ps.amount_paid)
                FROM customer_sales cs
                LEFT JOIN payment_splits ps ON cs.sale_id = ps.sale_id
                GROUP BY cs.sale_id;
            """,
            "13. Branch total sales.": """
                SELECT b.branch_name, SUM(cs.gross_sales)
                FROM customer_sales cs
                JOIN branches b ON cs.branch_id = b.branch_id
                GROUP BY b.branch_name;
            """,
            "14. Payment methods.": """
                SELECT payment_method, SUM(amount_paid)
                FROM payment_splits GROUP BY payment_method;
            """,
            "15. Sales with admin.": """
                SELECT cs.sale_id, b.branch_name, u.username
                FROM customer_sales cs
                JOIN branches b ON cs.branch_id = b.branch_id
                JOIN users u ON b.branch_id = u.branch_id;
            """,
            "16. Pending > 5000.": """
                SELECT cs.sale_id
                FROM customer_sales cs
                LEFT JOIN payment_splits ps ON cs.sale_id = ps.sale_id
                GROUP BY cs.sale_id
                HAVING cs.gross_sales - IFNULL(SUM(ps.amount_paid),0) > 5000;
            """,
            "17. Top 3 sales.": "SELECT * FROM customer_sales ORDER BY gross_sales DESC LIMIT 3;",
            "18. Best branch.": """
                SELECT b.branch_name, SUM(cs.gross_sales)
                FROM customer_sales cs
                JOIN branches b ON cs.branch_id = b.branch_id
                GROUP BY b.branch_name ORDER BY 2 DESC LIMIT 1;
            """,
            "19. Monthly sales.": "SELECT DATE_FORMAT(date,'%Y-%m'), SUM(gross_sales) FROM customer_sales GROUP BY 1;",
            "20. Payment summary.": "SELECT payment_method, SUM(amount_paid) FROM payment_splits GROUP BY payment_method;"
        }

        selected_query = st.selectbox("Select Query", list(query_options.keys()))

        if st.button("Run Query"):
            conn = mysql.connector.connect(host="localhost", user="root", password="", database="Sales_Management_System")
            df = pd.read_sql(query_options[selected_query], conn)
            conn.close()
            st.dataframe(df, width="stretch")


        