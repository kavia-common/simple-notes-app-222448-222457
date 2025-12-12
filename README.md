# simple-notes-app-222448-222457

Simple Notes App with FastAPI backend, React frontend, and PostgreSQL.

- Backend (FastAPI) runs on port 3001
- Frontend (React + Vite) runs on port 3000
- Database (PostgreSQL) runs on port 5001

Environment variables:
- See .env.example in this workspace. Ensure the backend has access to a valid DATABASE_URL or POSTGRES_* vars.
- Frontend uses VITE_BACKEND_URL (defaults to http://localhost:3001).

Backend:
- Endpoints:
  - GET /notes
  - GET /notes/{id}
  - POST /notes
  - PUT /notes/{id}
  - DELETE /notes/{id}
- On startup, the backend creates the notes table if it does not exist.

Frontend:
- Sidebar lists notes.
- Main pane edits the selected note (auto-saves on change).
- Create and Delete actions available from the UI.

CORS:
- Configured to allow http://localhost:3000 by default.

Notes:
- Data persists in PostgreSQL.