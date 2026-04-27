import mysql.connector
mydb = mysql.connector.connect( host="localhost", user="root", password="",)
print(mydb)
mycursor = mydb.cursor(buffered=True)
mycursor.execute("create database Sales_Management_System")
mycursor.execute("""create table Sales_Management_System.branches
                (branch_id INT PRIMARY KEY AUTO_INCREMENT, branch_name VARCHAR(100), branch_admin_name VARCHAR(100))""")
mycursor.execute("""create table Sales_Management_System.customer_sales
                (sale_id INT AUTO_INCREMENT PRIMARY KEY,
                branch_id INT,
                FOREIGN KEY (branch_id) REFERENCES Sales_Management_System.branches(branch_id),
                date DATE,
                name VARCHAR(100),
                mobile_number VARCHAR(15) UNIQUE,
                product_name VARCHAR(30),
                gross_sales DECIMAL(12,2),
                received_amount DECIMAL(12,2) DEFAULT 0,
                pending_amount DECIMAL(12,2) GENERATED ALWAYS AS (gross_sales - received_amount) STORED,
                status ENUM('Open','Close') DEFAULT 'Open')""")
mycursor.execute("""create table Sales_Management_System.users
                    (user_id INT AUTO_INCREMENT PRIMARY KEY, username VARCHAR(100),
                    password VARCHAR(255),branch_id INT,FOREIGN KEY (branch_id) REFERENCES branches(branch_id),
                    role ENUM('Super Admin', 'Admin'),
                    email VARCHAR(255) UNIQUE)""")
mycursor.execute ("""create table Sales_Management_System.payment_splits
                 (payment_id INT AUTO_INCREMENT PRIMARY KEY,
                 sale_id INT,
                 payment_date DATE,
                 amount_paid DECIMAL(12,2),
                 payment_method VARCHAR(50),
                 FOREIGN KEY (sale_id) REFERENCES customer_sales(sale_id))""")
mycursor.execute("""INSERT INTO Sales_Management_System.branches (branch_name, branch_admin_name)
                VALUES ('Chennai','Arun Kumar'),('Bangalore','Ravi Shankar'),('Hyderabad','Suresh Reddy')""")
mydb.commit()
mycursor.execute("SELECT branch_id FROM Sales_Management_System.branches")
print(mycursor.fetchall())
mycursor.execute("""INSERT INTO Sales_Management_System.customer_sales
                (branch_id, date, name, mobile_number, product_name, gross_sales)
                VALUES
                (1, '2024-01-02', 'Customer_1', '9800000001', 'DS', 40000),
                (2, '2024-01-03', 'Customer_2', '9800000002', 'BA', 30000)""")
mydb.commit()
mycursor.execute("""INSERT INTO Sales_Management_System.payment_splits (sale_id, payment_date, amount_paid, payment_method)
                VALUES
                (1, '2024-01-06', 7296, 'Cash'),
                (2, '2024-01-04', 7314, 'Card')""")
mydb.commit()


mycursor.execute("""INSERT INTO Sales_Management_System.users (username, password, branch_id, role, email)
                VALUES
                ('superadmin','super123',NULL,'Super Admin','superadmin@company.com'),
                ('admin_chennai','admin123','1','Admin','chennai@company.com')""")
mydb.commit()
mycursor.execute("USE Sales_Management_System")
mycursor.execute("""
CREATE TRIGGER update_received_amount
AFTER INSERT ON Sales_Management_System.payment_splits
FOR EACH ROW
BEGIN
    UPDATE Sales_Management_System.customer_sales
    SET received_amount = (
        SELECT IFNULL(SUM(amount_paid), 0)
        FROM Sales_Management_System.payment_splits
        WHERE sale_id = NEW.sale_id
    )
    WHERE sale_id = NEW.sale_id;
END
""")


mycursor.execute("select * from Sales_Management_System.customer_sales")

out=mycursor.fetchall()
from tabulate import tabulate
print(tabulate(out,headers=[i[0] for i in mycursor.description],  tablefmt='psql'))
mycursor.execute("select * from Sales_Management_System.payment_splits")

out=mycursor.fetchall()
from tabulate import tabulate
print(tabulate(out,headers=[i[0] for i in mycursor.description],  tablefmt='psql'))
mycursor.execute("""INSERT INTO Sales_Management_System.payment_splits 
(sale_id, payment_date, amount_paid, payment_method)
VALUES (1, '2026-04-05', 3000, 'UPI')
""")
mydb.commit()




mycursor.execute("SET FOREIGN_KEY_CHECKS = 0")

mycursor.execute("TRUNCATE TABLE payment_splits")
mycursor.execute("TRUNCATE TABLE customer_sales")
mycursor.execute("TRUNCATE TABLE users")
mycursor.execute("TRUNCATE TABLE branches")

mycursor.execute("SET FOREIGN_KEY_CHECKS = 1")

mydb.commit()
print("All tables cleared")