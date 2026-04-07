### MySQL Interpreter
##### Implemented with SvelteKit & Actual MySQL

---

## Local MySQL

Use Docker Compose to run the practice database locally.

1. Ensure [`.env`](/Users/kimdaewon/Desktop/프로젝트/mysql-interpreter/.env) contains the MySQL connection values.
2. Start MySQL with `docker compose up -d`.
3. If you need a fresh initialization from [`backend/schema_init.sql`](/Users/kimdaewon/Desktop/프로젝트/mysql-interpreter/backend/schema_init.sql), run `docker compose down -v` first, then `docker compose up -d`.

## Backend API

The backend exposes schema metadata for the current practice database.

1. Install Python dependencies with `pip install -r backend/requirements.txt`.
2. Start the API with `uvicorn backend.app:app --reload`.
3. Open `http://127.0.0.1:8000/api/schema-metadata`.

You can inspect a user-specific practice database with:

`http://127.0.0.1:8000/api/schema-metadata?user_id=alice`

This resolves to a database named `mysql_interpreter_practice_alice` when `MYSQL_DATABASE=mysql_interpreter_practice`.

## Frontend

1. Run `cd frontend && npm run dev`.
2. Open the local SvelteKit page.
3. The landing page fetches schema metadata from `http://127.0.0.1:8000` by default.

If needed, override the backend base URL with `VITE_BACKEND_URL`.
