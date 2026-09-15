import psycopg2

connection = psycopg2.connect(
    host="localhost",
    database="webhook_engine",
    user="postgres",
    password="Doremon@123",
    port="5432"
)

cursor = connection.cursor()

message = "Payment successful"

cursor.execute(
    """
    INSERT INTO webhooks (message)
    VALUES (%s)
    """,
    (message,)
)

connection.commit()

print("Webhook saved successfully!")

cursor.close()
connection.close()