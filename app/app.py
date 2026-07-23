import os
import secrets
from datetime import datetime

import psycopg2
from flask import Flask, render_template, request
from flask_wtf import CSRFProtect

from validation import MAX_LENGTH, MIN_LENGTH, validate_search_term

app = Flask(__name__)
# Required by Flask-WTF to sign CSRF tokens. Falls back to a fresh random
# key per process (invalidating outstanding tokens on restart) rather than
# a hardcoded default, since a literal secret in source is itself a
# security issue.
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY") or secrets.token_hex(32)
csrf = CSRFProtect(app)

DB_CONFIG = {
    "host": os.environ.get("DB_HOST", "db"),
    "port": os.environ.get("DB_PORT", "5432"),
    "dbname": os.environ.get("DB_NAME", "ssd_prac"),
    "user": os.environ.get("DB_USER", "ssd_user"),
    "password": os.environ.get("DB_PASSWORD", ""),
}


def get_db_connection():
    return psycopg2.connect(**DB_CONFIG)


def log_search_query(term):
    conn = get_db_connection()
    try:
        with conn, conn.cursor() as cur:
            # Parameterized query - never string-format user input into SQL.
            cur.execute(
                'INSERT INTO "2401807" (search_query, query_time) VALUES (%s, %s)',
                (term, datetime.now()),
            )
    finally:
        conn.close()


@app.route("/", methods=["GET"])
def home():
    return render_template("index.html", min_length=MIN_LENGTH, max_length=MAX_LENGTH)


@app.route("/search", methods=["POST"])
def search():
    term = request.form.get("search_term", "")
    is_valid, error = validate_search_term(term)

    if not is_valid:
        # Attack (or otherwise invalid input) detected: clear the input
        # and stay on the home page so the user can try again.
        return render_template(
            "index.html",
            min_length=MIN_LENGTH,
            max_length=MAX_LENGTH,
            error=error,
            search_term="",
        )

    clean_term = term.strip()
    log_search_query(clean_term)
    return render_template("results.html", search_term=clean_term)


if __name__ == "__main__":
    # This dev-server entry point is only used for local/CI runs (the
    # container's real entrypoint is gunicorn, see Dockerfile), where the
    # test client always runs on the same host - loopback is sufficient
    # and avoids exposing the Flask dev server on all interfaces.
    app.run(host="127.0.0.1", port=5000)
