# Quizly — Cloud-Based Online Quiz System

A starter full-stack college project using **Python Flask + SQLite + HTML/CSS**.

## Features
- Separate Admin and Participant login roles
- Participant registration (passwords are hashed)
- Admin dashboard with participant, quiz, and attempt counts
- Admin can create/edit/delete quizzes and add/delete MCQ questions
- Participants can take quizzes and get automatic scores
- Attempt history for each participant
- Leaderboard calculated from actual attempts in the database
- Four sample quizzes are seeded automatically on first run
- Responsive layout

## Run on Windows
1. Install Python 3.10 or newer.
2. Extract the ZIP.
3. Open Command Prompt/Terminal inside the extracted `quizly_full_resource` folder.
4. Create a virtual environment (recommended):
   ```bash
   python -m venv .venv
   ```
5. Activate it:
   ```bash
   .venv\Scripts\activate
   ```
6. Install requirements:
   ```bash
   pip install -r requirements.txt
   ```
7. Start the app:
   ```bash
   python app.py
   ```
8. Open `http://127.0.0.1:5000` in your browser.

## Demo admin login
- Email: `admin@quizly.local`
- Password: `Admin123!`

Change these demo credentials before using the project for real users. You can set environment variables before the first launch:
- `QUIZLY_ADMIN_EMAIL`
- `QUIZLY_ADMIN_PASSWORD`
- `SECRET_KEY`

On Windows Command Prompt, for example:
```bat
set QUIZLY_ADMIN_EMAIL=your-admin-email@example.com
set QUIZLY_ADMIN_PASSWORD=choose-a-strong-password
set SECRET_KEY=replace-with-a-long-random-secret
python app.py
```
The default admin account is only seeded if that email does not already exist in the database.

## Participant login
Participants click **Create participant account**, register with name/email/password (minimum 8 characters), and then log in with the Participant role.

## Important deployment notes
- This is a functional local starter, not already hosted online.
- SQLite is suitable for local demos. For a real public cloud deployment, use a managed database such as PostgreSQL, set a strong `SECRET_KEY`, disable debug mode, configure HTTPS, add CSRF protection and rate limiting, and use a production WSGI server. Do not use the demo admin credentials on a public deployment.
- Admin-created quizzes and participant attempts are stored in `quizly.db` next to `app.py`.
