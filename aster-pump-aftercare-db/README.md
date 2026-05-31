# Aster Pump Aftercare Database

PostgreSQL database component for support tickets.

The backend does not connect to this database directly. The official MCP server
owns database operations and exposes them as MCP tools.

## Technology Brief

### PostgreSQL

PostgreSQL stores support-ticket records.

### Init SQL

The Docker image copies `init.sql` into:

```text
/docker-entrypoint-initdb.d/001-init.sql
```

PostgreSQL runs this SQL only when the data volume is created for the first
time.

## Important Files

| File | Function |
| --- | --- |
| `Dockerfile` | Builds local PostgreSQL image with init SQL. |
| `init.sql` | Creates support ticket table and indexes. |
| `build-image.ps1` | Builds local Docker image. |

## Code Walkthrough

### Dockerfile

```dockerfile
FROM postgres:16-alpine
```

Explanation:

- Uses the official PostgreSQL 16 Alpine image.
- Alpine keeps the image smaller.

```dockerfile
COPY init.sql /docker-entrypoint-initdb.d/001-init.sql
```

Explanation:

- PostgreSQL automatically runs scripts in `/docker-entrypoint-initdb.d`.
- The script runs when the database volume is empty.

### Ticket Table

```sql
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
```

Explanation:

- `id` is the ticket number.
- `customer_email` is used for latest-ticket lookup.
- `status` moves through values such as `image_analyzed`,
  `technical_steps_added`, and `completed`.
- `detected_objects` stores labels returned by the Image AI service.
- `detected_error_code` stores values such as `E-77`.
- `technical_steps` stores RAG-generated support instructions.
- `reply_subject` and `reply_body` store the simulated email.
- `email_sent` marks whether reply was sent.

### Indexes

```sql
CREATE INDEX IF NOT EXISTS idx_support_tickets_email ON support_tickets(customer_email);
CREATE INDEX IF NOT EXISTS idx_support_tickets_status ON support_tickets(status);
```

Explanation:

- Email lookup is used when the user checks latest status.
- Status index is useful for future dashboards or operational filters.

## Build And Deployment

See:

```text
BUILD_AND_DEPLOY.md
```

