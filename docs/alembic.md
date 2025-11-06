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
