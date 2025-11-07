Perfect 🚀 Now that you’re moving from just a test script into building **routes, schemas, and services**, yes — you should use **migrations**. That way, whenever you change your models, you can evolve your database schema without losing existing data.

Here’s a **step-by-step guide to set up Alembic for migrations** with your SQLAlchemy async project:

---

## 🔹 1. Install Alembic

In your virtualenv, install Alembic:

```bash
pip install alembic
```

---

## 🔹 2. Initialize Alembic in your project

Inside your project root (where `app/` is), run:

```bash
alembic init alembic
```

This will create:

```
alembic/
    versions/          # migration scripts will live here
alembic.ini           # Alembic config file
```

---

## 🔹 3. Configure `alembic.ini`

Open `alembic.ini` and update the `sqlalchemy.url` line to point to your DB (use async driver):

```ini
sqlalchemy.url = postgresql+asyncpg://postgres:postgres@localhost/demo_db
```

---

## 🔹 4. Configure `env.py`

Open `alembic/env.py`. Replace its contents with async-friendly config:

```python
from logging.config import fileConfig
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from alembic import context

from sqlalchemy.ext.asyncio import create_async_engine
from app.model.baseaudit_model import Base  # <-- Import your Base
from app.model.demo_model import Demo  # <-- Import your models

# this is the Alembic Config object
config = context.config

# Interpret the config file for Python logging
fileConfig(config.config_file_name)

# Add your models' MetaData object here
target_metadata = Base.metadata

def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()

def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection, target_metadata=target_metadata
    )

    with context.begin_transaction():
        context.run_migrations()

async def run_migrations_online() -> None:
    """Run migrations in 'online' mode with async engine."""
    connectable = create_async_engine(
        config.get_main_option("sqlalchemy.url"),
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()

if context.is_offline_mode():
    run_migrations_offline()
else:
    import asyncio
    asyncio.run(run_migrations_online())
```

---

## 🔹 5. Generate first migration

Now autogenerate your migration from the models:

```bash
alembic revision --autogenerate -m "init demo tables"
```

This creates a file in `alembic/versions/` with SQL statements.

---

## 🔹 6. Apply migration

Run:

```bash
alembic upgrade head
```

This applies the migration and creates your tables in the DB.

---

## 🔹 7. Workflow for future changes

Whenever you change models (`demo_model.py`, etc.):

1. Update SQLAlchemy model.

2. Generate migration:

   ```bash
   alembic revision --autogenerate -m "added status column"
   ```

3. Apply migration:

   ```bash
   alembic upgrade head
   ```

---

✅ With this, your **routes, schemas, and services** can rely on a real evolving DB schema.
❌ Don’t use `Base.metadata.create_all` anymore in production/test runner — let Alembic manage schema.

---

👉 Do you want me to **rewrite your test runner** so it skips `create_all` and instead ensures Alembic migrations are applied before running tests?


### Using the API to Manage Database Migrations

You can programmatically set up and upgrade your SQLAlchemy database by calling the following API endpoint:

```
POST http://localhost:8801/demo-management-service/api/v1/database/
```

#### Step 1: Create a Migration (Revision)

Send a POST request with this JSON body to generate a new migration file (revision):

```json
{
  "operation": "revision",
  "message": "initial migration for existing tables"
}
```

#### Step 2: Apply the Migration (Upgrade)

Next, to apply migrations (upgrade the database), send:

```json
{
  "operation": "upgrade",
  "revision": "head"
}
```

This will upgrade your database schema to the latest revision.

---

### Upload and Download Migrations via the API

To **back up** (upload) your local Alembic migration files to Wasabi/S3, or **restore** (download) them from Wasabi, you can use these endpoints:

#### **Upload migration files to Wasabi/S3**

```
POST http://localhost:8801/demo-management-service/api/v1/database/upload
```

**Request body:**

```json
{}
```

- No fields are required in the body.
- The server zips and uploads your current `alembic/versions/*.py` migration scripts to Wasabi/S3.
- Ensure your environment variables for Wasabi/S3 are configured (`WASABI_ACCESS_KEY_ID`, `WASABI_SECRET_ACCESS_KEY`, `MIGRATION_BUCKET_NAME`).

#### **Download migration files from Wasabi/S3**

```
POST http://localhost:8801/demo-management-service/api/v1/database/download
```

**Request body:**

```json
{}
```

- No fields are required in the body.
- Downloads migration files from Wasabi/S3 (by default the “latest” migration set) and writes them to `alembic/versions/`. This will overwrite current migration files in that directory.

##### **Example cURL Usage**

```bash
# Upload migrations to Wasabi
curl -X POST http://localhost:8801/demo-management-service/api/v1/database/upload \
     -H "Content-Type: application/json" \
     -d '{}'

# Download migrations from Wasabi
curl -X POST http://localhost:8801/demo-management-service/api/v1/database/download \
     -H "Content-Type: application/json" \
     -d '{}'
```

These APIs help you share or restore migration files across environments (CI, multiple devs, production, etc.) without manual copying.

---




