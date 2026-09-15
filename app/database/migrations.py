from sqlalchemy import text
from app.database.connection import engine


def run_migrations() -> None:
    """Non-destructive schema migration script.
    
    Safely adds new required columns to 'webhooks' and creates 'webhook_deliveries'
    without modifying or deleting existing webhook rows.
    """
    with engine.begin() as conn:
        print("Running non-destructive database migrations...")
        
        # 1. Add target_url column if not present
        conn.execute(text("""
            ALTER TABLE webhooks 
            ADD COLUMN IF NOT EXISTS target_url VARCHAR(500) NOT NULL DEFAULT 'http://127.0.0.1:9000';
        """))

        # 2. Add event_type column if not present
        conn.execute(text("""
            ALTER TABLE webhooks 
            ADD COLUMN IF NOT EXISTS event_type VARCHAR(50) DEFAULT 'default';
        """))

        # 3. Add idempotency_key column if not present
        conn.execute(text("""
            ALTER TABLE webhooks 
            ADD COLUMN IF NOT EXISTS idempotency_key VARCHAR(100);
        """))

        # 4. Add updated_at column if not present
        conn.execute(text("""
            ALTER TABLE webhooks 
            ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
        """))

        # 5. Create webhook_deliveries table for granular attempt history
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS webhook_deliveries (
                id SERIAL PRIMARY KEY,
                webhook_id INT NOT NULL REFERENCES webhooks(id) ON DELETE CASCADE,
                attempt_number INT NOT NULL,
                status VARCHAR(20) NOT NULL,
                response_status_code INT,
                response_body TEXT,
                error_message TEXT,
                duration_ms INT,
                started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """))

        # 6. Add indexes for high-throughput queries
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_webhooks_status ON webhooks(status);
        """))
        conn.execute(text("""
            CREATE UNIQUE INDEX IF NOT EXISTS idx_webhooks_idempotency_key 
            ON webhooks(idempotency_key) WHERE idempotency_key IS NOT NULL;
        """))
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_webhook_deliveries_webhook_id 
            ON webhook_deliveries(webhook_id);
        """))

        print("Migrations applied successfully! Existing data preserved.")


if __name__ == "__main__":
    run_migrations()
