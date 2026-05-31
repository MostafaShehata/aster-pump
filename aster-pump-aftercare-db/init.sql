DO $$
BEGIN
    RAISE NOTICE 'DB | init | creating Aster Pump Aftercare ticket schema';
END $$;

CREATE TABLE IF NOT EXISTS support_tickets (
    id SERIAL PRIMARY KEY,
    customer_email TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'created',
    description TEXT NOT NULL DEFAULT '',
    detected_objects JSONB NOT NULL DEFAULT '[]'::jsonb,
    detected_error_code TEXT,
    technical_steps TEXT,
    reply_subject TEXT,
    reply_body TEXT,
    email_sent BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_support_tickets_email ON support_tickets(customer_email);
CREATE INDEX IF NOT EXISTS idx_support_tickets_status ON support_tickets(status);

DO $$
BEGIN
    RAISE NOTICE 'DB | init | support_tickets table and indexes are ready';
END $$;
