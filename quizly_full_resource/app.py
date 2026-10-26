import os, sqlite3
from functools import wraps
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, session, flash, abort
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "change-this-secret-key-before-deployment")
DB_PATH = os.path.join(os.path.dirname(__file__), "quizly.db")

def db():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    return con

def init_db():
    con = db()
    con.executescript("""
    CREATE TABLE IF NOT EXISTS users (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      name TEXT NOT NULL, email TEXT UNIQUE NOT NULL,
      password_hash TEXT NOT NULL, role TEXT NOT NULL CHECK(role IN ('admin','participant')),
      created_at TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS quizzes (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      title TEXT NOT NULL, description TEXT DEFAULT '',
      created_at TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS questions (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      quiz_id INTEGER NOT NULL REFERENCES quizzes(id) ON DELETE CASCADE,
      question TEXT NOT NULL, option_a TEXT NOT NULL, option_b TEXT NOT NULL,
      option_c TEXT NOT NULL, option_d TEXT NOT NULL, correct_option INTEGER NOT NULL CHECK(correct_option BETWEEN 0 AND 3)
    );
    CREATE TABLE IF NOT EXISTS attempts (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      user_id INTEGER NOT NULL REFERENCES users(id),
      quiz_id INTEGER NOT NULL REFERENCES quizzes(id),
      score INTEGER NOT NULL, total INTEGER NOT NULL, percent INTEGER NOT NULL,
      submitted_at TEXT NOT NULL
    );
    """)
    # A default admin is created only if it does not already exist.
    admin_email = os.environ.get("QUIZLY_ADMIN_EMAIL", "admin@quizly.local").lower()
    admin_password = os.environ.get("QUIZLY_ADMIN_PASSWORD", "Admin123!")
    exists = con.execute("SELECT id FROM users WHERE email=?", (admin_email,)).fetchone()
    if not exists:
        con.execute("INSERT INTO users(name,email,password_hash,role,created_at) VALUES(?,?,?,?,?)",
                    ("Administrator", admin_email, generate_password_hash(admin_password), "admin", datetime.now().isoformat(timespec="seconds")))
    count = con.execute("SELECT COUNT(*) n FROM quizzes").fetchone()["n"]
    if count == 0:
        seeds = [
            ("General Knowledge", "A quick test of everyday knowledge.", [
                ("Which is the largest planet in our solar system?", ["Earth","Jupiter","Saturn","Mars"], 1),
                ("What is the capital of Japan?", ["Seoul","Beijing","Tokyo","Bangkok"], 2),
                ("How many days are there in a leap year?", ["364","365","366","367"], 2),
                ("Which ocean is the largest?", ["Atlantic","Indian","Arctic","Pacific"], 3),
                ("Which is the national animal of India?", ["Lion","Bengal tiger","Elephant","Peacock"], 1),
                ("How many colours are traditionally listed in a rainbow?", ["Five","Six","Seven","Eight"], 2),
                ("Which planet is known as the Red Planet?", ["Venus","Mars","Mercury","Neptune"], 1),
                ("What is the currency of Japan?", ["Yuan","Won","Yen","Ringgit"], 2),
                ("Which is the tallest mountain above sea level?", ["K2","Mount Everest","Kangchenjunga","Lhotse"], 1),
                ("How many sides does a hexagon have?", ["Five","Six","Seven","Eight"], 1)]),
            ("Computer Science", "Programming, computers, and web fundamentals.", [
                ("What does CPU stand for?", ["Central Processing Unit","Computer Personal Unit","Core Program Utility","Central Program User"], 0),
                ("Which language is used to style web pages?", ["HTML","CSS","SQL","Python"], 1),
                ("Which of these is an input device?", ["Monitor","Speaker","Keyboard","Projector"], 2),
                ("What does HTML stand for?", ["Hyper Trainer Marking Language","HyperText Markup Language","HighText Machine Language","HyperText Markdown Link"], 1),
                ("Which number system uses only 0 and 1?", ["Decimal","Octal","Binary","Hexadecimal"], 2),
                ("Which one is a web browser?", ["Linux","Chrome","Python","MySQL"], 1),
                ("What does RAM mainly provide?", ["Long-term storage","Temporary working memory","Internet access","Power supply"], 1),
                ("Which symbol commonly ends a Java statement?", [":",";",".",","], 1),
                ("Which is a relational database system?", ["MySQL","HTML","CSS","Figma"], 0),
                ("What does URL stand for?", ["Uniform Resource Locator","Universal Record Link","Unified Routing Language","User Reference Location"], 0)]),
            ("Science", "Basic science and the natural world.", [
                ("Which gas do plants absorb during photosynthesis?", ["Oxygen","Nitrogen","Carbon dioxide","Hydrogen"], 2),
                ("What is H2O commonly known as?", ["Salt","Water","Oxygen","Hydrogen"], 1),
                ("Which organ pumps blood around the human body?", ["Lungs","Brain","Liver","Heart"], 3),
                ("At sea level, water boils at approximately what temperature?", ["50 C","75 C","100 C","125 C"], 2),
                ("Which force pulls objects toward Earth?", ["Friction","Gravity","Magnetism","Tension"], 1),
                ("Which part of a plant usually absorbs water from soil?", ["Flower","Leaf","Root","Fruit"], 2),
                ("What is the closest star to Earth?", ["Sirius","The Sun","Polaris","Proxima Centauri"], 1),
                ("Which vitamin can the body produce with sunlight exposure?", ["Vitamin A","Vitamin B12","Vitamin C","Vitamin D"], 3),
                ("What is the basic unit of life?", ["Atom","Cell","Organ","Tissue"], 1),
                ("Which state of matter has a fixed volume but no fixed shape?", ["Solid","Liquid","Gas","Plasma"], 1)]),
            ("Mathematics", "Arithmetic, shapes, and number skills.", [
                ("What is 12 x 8?", ["84","92","96","108"], 2),
                ("What is the square root of 81?", ["7","8","9","10"], 2),
                ("What is 25% of 200?", ["25","40","50","75"], 2),
                ("How many degrees are in a right angle?", ["45","90","180","360"], 1),
                ("What is 15 + 27?", ["32","40","42","45"], 2),
                ("Which of these is a prime number?", ["21","27","29","33"], 2),
                ("What is 7 squared?", ["14","42","49","56"], 2),
                ("What is the perimeter of a square with side 5 cm?", ["10 cm","15 cm","20 cm","25 cm"], 2),
                ("What is 3/4 as a percentage?", ["25%","50%","75%","80%"], 2),
                ("What is 100 divided by 4?", ["20","25","40","50"], 1)])
        ]
        for title, description, qs in seeds:
            cur = con.execute("INSERT INTO quizzes(title,description,created_at) VALUES(?,?,?)", (title, description, datetime.now().isoformat(timespec="seconds")))
            qid = cur.lastrowid
            for question, opts, correct in qs:
                con.execute("INSERT INTO questions(quiz_id,question,option_a,option_b,option_c,option_d,correct_option) VALUES(?,?,?,?,?,?,?)",
                            (qid, question, opts[0], opts[1], opts[2], opts[3], correct))
    con.commit()
    con.close()

def login_required(role=None):
    def decorator(fn):
        @wraps(fn)
        def wrapped(*args, **kwargs):
            if not session.get("user_id"):
                flash("Please log in first.", "warning")
                return redirect(url_for("login"))
            if role and session.get("role") != role:
                abort(403)
            return fn(*args, **kwargs)
        return wrapped
    return decorator

@app.context_processor
def common_context():
    return {"current_user": session.get("name"), "current_role": session.get("role")}

@app.route("/")
def home():
    con = db()
    quizzes = con.execute("""SELECT q.*, COUNT(questions.id) question_count FROM quizzes q
      LEFT JOIN questions ON questions.quiz_id=q.id GROUP BY q.id ORDER BY q.id DESC""").fetchall()
    con.close()
    return render_template("home.html", quizzes=quizzes)

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        if not name or not email or len(password) < 8:
            flash("Enter your name and email, and use a password of at least 8 characters.", "danger")
            return render_template("register.html")
        con = db()
        try:
            con.execute("INSERT INTO users(name,email,password_hash,role,created_at) VALUES(?,?,?,?,?)",
                        (name, email, generate_password_hash(password), "participant", datetime.now().isoformat(timespec="seconds")))
            con.commit()
        except sqlite3.IntegrityError:
            flash("That email is already registered. Please log in.", "danger")
            con.close()
            return render_template("register.html")
        con.close()
        flash("Account created. You can now log in.", "success")
        return redirect(url_for("login"))
    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        role = request.form.get("role", "participant")
        con = db()
        user = con.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
        con.close()
        if not user or not check_password_hash(user["password_hash"], password) or user["role"] != role:
            flash("Invalid email, password, or account type.", "danger")
            return render_template("login.html")
        session.clear()
        session["user_id"], session["name"], session["role"] = user["id"], user["name"], user["role"]
        return redirect(url_for("admin_dashboard" if user["role"] == "admin" else "participant_dashboard"))
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("home"))

@app.route("/participant")
@login_required("participant")
def participant_dashboard():
    con = db()
    quizzes = con.execute("""SELECT q.*, COUNT(questions.id) question_count FROM quizzes q
      LEFT JOIN questions ON questions.quiz_id=q.id GROUP BY q.id ORDER BY q.id DESC""").fetchall()
    attempts = con.execute("""SELECT attempts.*, quizzes.title FROM attempts JOIN quizzes ON quizzes.id=attempts.quiz_id
      WHERE user_id=? ORDER BY submitted_at DESC""", (session["user_id"],)).fetchall()
    con.close()
    return render_template("participant.html", quizzes=quizzes, attempts=attempts)

@app.route("/quiz/<int:quiz_id>", methods=["GET", "POST"])
@login_required("participant")
def take_quiz(quiz_id):
    con = db()
    quiz = con.execute("SELECT * FROM quizzes WHERE id=?", (quiz_id,)).fetchone()
    if not quiz:
        con.close()
        abort(404)
    questions = con.execute("SELECT * FROM questions WHERE quiz_id=? ORDER BY id", (quiz_id,)).fetchall()
    if request.method == "POST":
        if not questions:
            con.close()
            flash("This quiz has no questions yet.", "warning")
            return redirect(url_for("participant_dashboard"))
        score = sum(1 for q in questions if request.form.get(f"q{q['id']}") == str(q["correct_option"]))
        total = len(questions)
        percent = round(score / total * 100)
        con.execute("INSERT INTO attempts(user_id,quiz_id,score,total,percent,submitted_at) VALUES(?,?,?,?,?,?)",
                    (session["user_id"], quiz_id, score, total, percent, datetime.now().isoformat(timespec="seconds")))
        con.commit()
        con.close()
        return render_template("quiz_result.html", quiz=quiz, score=score, total=total, percent=percent)
    con.close()
    return render_template("take_quiz.html", quiz=quiz, questions=questions)

@app.route("/admin")
@login_required("admin")
def admin_dashboard():
    con = db()
    stats = {
        "users": con.execute("SELECT COUNT(*) n FROM users WHERE role='participant'").fetchone()["n"],
        "quizzes": con.execute("SELECT COUNT(*) n FROM quizzes").fetchone()["n"],
        "attempts": con.execute("SELECT COUNT(*) n FROM attempts").fetchone()["n"],
    }
    quizzes = con.execute("""SELECT q.*, COUNT(questions.id) question_count FROM quizzes q
      LEFT JOIN questions ON questions.quiz_id=q.id GROUP BY q.id ORDER BY q.id DESC""").fetchall()
    participants = con.execute("SELECT id,name,email,created_at FROM users WHERE role='participant' ORDER BY id DESC LIMIT 10").fetchall()
    attempts = con.execute("""SELECT users.name, quizzes.title, attempts.score, attempts.total, attempts.percent, attempts.submitted_at
      FROM attempts JOIN users ON users.id=attempts.user_id JOIN quizzes ON quizzes.id=attempts.quiz_id
      ORDER BY attempts.submitted_at DESC LIMIT 10""").fetchall()
    con.close()
    return render_template("admin.html", stats=stats, quizzes=quizzes, participants=participants, attempts=attempts)

@app.route("/admin/quiz/new", methods=["GET", "POST"])
@login_required("admin")
def create_quiz():
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()
        if not title:
            flash("Quiz title is required.", "danger")
        else:
            con = db()
            con.execute("INSERT INTO quizzes(title,description,created_at) VALUES(?,?,?)", (title, description, datetime.now().isoformat(timespec="seconds")))
            con.commit()
            con.close()
            flash("Quiz created. Add questions next.", "success")
            return redirect(url_for("admin_dashboard"))
    return render_template("quiz_form.html", quiz=None)

@app.route("/admin/quiz/<int:quiz_id>/edit", methods=["GET", "POST"])
@login_required("admin")
def edit_quiz(quiz_id):
    con = db()
    quiz = con.execute("SELECT * FROM quizzes WHERE id=?", (quiz_id,)).fetchone()
    if not quiz:
        con.close()
        abort(404)
    if request.method == "POST":
        title, description = request.form.get("title", "").strip(), request.form.get("description", "").strip()
        if title:
            con.execute("UPDATE quizzes SET title=?,description=? WHERE id=?", (title, description, quiz_id))
            con.commit()
            con.close()
            flash("Quiz updated.", "success")
            return redirect(url_for("admin_dashboard"))
        flash("Quiz title is required.", "danger")
    con.close()
    return render_template("quiz_form.html", quiz=quiz)

@app.route("/admin/quiz/<int:quiz_id>/delete", methods=["POST"])
@login_required("admin")
def delete_quiz(quiz_id):
    con = db()
    con.execute("DELETE FROM questions WHERE quiz_id=?", (quiz_id,))
    con.execute("DELETE FROM attempts WHERE quiz_id=?", (quiz_id,))
    con.execute("DELETE FROM quizzes WHERE id=?", (quiz_id,))
    con.commit()
    con.close()
    flash("Quiz deleted.", "success")
    return redirect(url_for("admin_dashboard"))

@app.route("/admin/quiz/<int:quiz_id>/questions", methods=["GET", "POST"])
@login_required("admin")
def manage_questions(quiz_id):
    con = db()
    quiz = con.execute("SELECT * FROM quizzes WHERE id=?", (quiz_id,)).fetchone()
    if not quiz:
        con.close()
        abort(404)
    if request.method == "POST":
        question = request.form.get("question", "").strip()
        opts = [request.form.get(f"option_{x}", "").strip() for x in "abcd"]
        try:
            correct = int(request.form.get("correct_option", "-1"))
        except ValueError:
            correct = -1
        if not question or not all(opts) or correct not in range(4):
            flash("Fill the question, all four options, and the correct answer.", "danger")
        else:
            con.execute("INSERT INTO questions(quiz_id,question,option_a,option_b,option_c,option_d,correct_option) VALUES(?,?,?,?,?,?,?)",
                        (quiz_id, question, *opts, correct))
            con.commit()
            flash("Question added.", "success")
            con.close()
            return redirect(url_for("manage_questions", quiz_id=quiz_id))
    questions = con.execute("SELECT * FROM questions WHERE quiz_id=? ORDER BY id", (quiz_id,)).fetchall()
    con.close()
    return render_template("questions.html", quiz=quiz, questions=questions)

@app.route("/admin/question/<int:question_id>/delete", methods=["POST"])
@login_required("admin")
def delete_question(question_id):
    con = db()
    row = con.execute("SELECT quiz_id FROM questions WHERE id=?", (question_id,)).fetchone()
    if row:
        quiz_id = row["quiz_id"]
        con.execute("DELETE FROM questions WHERE id=?", (question_id,))
        con.commit()
    else:
        quiz_id = None
    con.close()
    flash("Question deleted." if row else "Question not found.", "success" if row else "warning")
    return redirect(url_for("manage_questions", quiz_id=quiz_id)) if quiz_id else redirect(url_for("admin_dashboard"))

@app.route("/leaderboard")
def leaderboard():
    con = db()
    rows = con.execute("""SELECT users.name, SUM(attempts.score) points, COUNT(attempts.id) attempts,
      MAX(attempts.percent) best FROM users JOIN attempts ON attempts.user_id=users.id
      WHERE users.role='participant' GROUP BY users.id ORDER BY points DESC, best DESC LIMIT 50""").fetchall()
    con.close()
    return render_template("leaderboard.html", rows=rows)

@app.errorhandler(403)
def forbidden(e):
    return render_template("message.html", title="Access denied", message="You do not have permission to view this page."), 403

@app.errorhandler(404)
def not_found(e):
    return render_template("message.html", title="Page not found", message="The page or quiz you requested does not exist."), 404

init_db()
if __name__ == "__main__":
    app.run(debug=True)
