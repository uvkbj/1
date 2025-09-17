import pyodbc

conn_str = (
    r"Driver={SQL Server};"
    r"Server=.;" 
    r"Database=SalaryDB;"
    r"Trusted_Connection=yes;"
)

def get_db_connection():
    return pyodbc.connect(conn_str)