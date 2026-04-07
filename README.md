## MySQL Interpreter

Sogang University `CSE4110 Database Systems` course project.

This project provides:

- a SvelteKit frontend for running SQL queries
- a FastAPI backend connected to MySQL
- an IP-scoped practice database session that is initialized from course schema and sample data
- a schema diagram view generated from live database metadata

## Stack

- Frontend: SvelteKit
- Backend: FastAPI
- Database: MySQL 8 via Docker Compose

## Project Files

- [`frontend/src/routes/+page.svelte`](frontend/src/routes/+page.svelte): main UI
- [`backend/app.py`](backend/app.py): API entrypoint
- [`backend/schema_init.sql`](backend/schema_init.sql): base relational schema
- [`backend/sample_appending.sql`](backend/sample_appending.sql): sample rows loaded into each practice DB
- [`docker-compose.yml`](docker-compose.yml): local MySQL container

## Environment

Set [`.env`](.env) with at least:

```env
MYSQL_HOST=127.0.0.1
MYSQL_PORT=3306
MYSQL_DATABASE=mysql_interpreter_practice
MYSQL_USER=practice_user
MYSQL_PASSWORD=practice_password
MYSQL_ROOT_PASSWORD=rootpassword
SESSION_TTL_SECONDS=90
```

`MYSQL_ROOT_PASSWORD` is required because the backend creates and drops practice databases dynamically.

## Run Locally

1. Start MySQL.

```bash
docker compose up -d
```

2. Install backend dependencies and run the API.

```bash
pip install -r backend/requirements.txt
uvicorn backend.app:app --reload
```

3. Run the frontend.

```bash
cd frontend
npm install
npm run dev
```

4. Open the local SvelteKit page shown by Vite, usually `http://localhost:5173`.

## Practice Database Session

The backend does not use login-based database allocation right now.

Instead:

- each client IP gets its own practice database
- the database name is derived from `MYSQL_DATABASE` and the client IP
- a new session database is initialized with [`backend/schema_init.sql`](backend/schema_init.sql) and [`backend/sample_appending.sql`](backend/sample_appending.sql)
- the frontend sends periodic heartbeat requests
- when the page closes, the frontend requests release
- expired sessions are cleaned up after `SESSION_TTL_SECONDS`

This is approximate session cleanup, not a perfect disconnect detector.

## Query Behavior

The frontend query panel sends SQL to the backend and refreshes the schema diagram after execution.

Special handling exists for `CREATE TABLE` statements using textbook-style foreign key shorthand such as:

```sql
foreign key (dept_name) references department
```

If MySQL rejects that form, the backend retries by expanding it to the referenced primary key columns automatically.

## Resetting MySQL State

To reset the Docker MySQL volume completely:

```bash
docker compose down -v
docker compose up -d
```

Then restart the backend so new IP-scoped practice databases are recreated from the current schema and sample SQL.
