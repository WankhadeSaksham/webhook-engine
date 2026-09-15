import psycopg2
import requests
import time


# Connect to PostgreSQL
connection = psycopg2.connect(
    host="localhost",
    database="webhook_engine",
    user="postgres",
    password="*********",
    port="5432"
)

cursor = connection.cursor()


# Webhook message
message = "Payment successful"


# Save webhook in database
cursor.execute(
    """
    INSERT INTO webhooks (message)
    VALUES (%s)
    RETURNING id
    """,
    (message,)
)

webhook_id = cursor.fetchone()[0]

connection.commit()

print(f"Webhook created successfully!")
print(f"Webhook ID: {webhook_id}")


# Receiver URL
url = "http://127.0.0.1:9000"

data = {
    "webhook_id": webhook_id,
    "message": message
}


# Try to deliver 3 times
max_retries = 3

for attempt in range(1, max_retries + 1):

    print(f"Attempt {attempt}: Sending webhook...")

    # Save attempt number in database
    cursor.execute(
        """
        UPDATE webhooks
        SET attempts = %s
        WHERE id = %s
        """,
        (attempt, webhook_id)
    )

    connection.commit()

    try:
        response = requests.post(
            url,
            json=data,
            timeout=5
        )

        if response.status_code == 200:

            cursor.execute(
                """
                UPDATE webhooks
                SET status = 'delivered'
                WHERE id = %s
                """,
                (webhook_id,)
            )

            connection.commit()

            print("✅ Webhook delivered!")
            break

        else:
            print("❌ Receiver returned an error")

    except requests.exceptions.RequestException:
        print("❌ Receiver is unavailable")

    # Wait before retry
    if attempt < max_retries:
        print("⏳ Waiting 2 seconds before retry...")
        time.sleep(2)

else:

    cursor.execute(
        """
        UPDATE webhooks
        SET status = 'failed'
        WHERE id = %s
        """,
        (webhook_id,)
    )

    connection.commit()

    print("❌ Webhook failed after 3 attempts")


cursor.close()
connection.close()
