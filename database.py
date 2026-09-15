import psycopg2

connection = psycopg2.connect(
    host="localhost",
    database="webhook_engine",
    user="postgres",
    password="Doremon@123",
    port="5432"
)

print("Database connected successfully!")