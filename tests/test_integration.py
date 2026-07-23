"""
Integration tests for the Flask search application.

These hit the running application over plain HTTP (as started directly by
the CI workflow, i.e. not through the nginx/HTTPS/Basic-Auth front end) and
verify the request/response flow together with the database side effect,
i.e. that validated searches are persisted to the "2401807" table and that
rejected (attack) input is never persisted.
"""
import os
import re
import time

import psycopg2
import pytest
import requests

APP_URL = os.environ.get("APP_URL", "http://127.0.0.1:5000").rstrip("/")

DB_CONFIG = dict(
    host=os.environ.get("DB_HOST", "localhost"),
    port=os.environ.get("DB_PORT", "5432"),
    dbname=os.environ.get("DB_NAME", "ssd_prac"),
    user=os.environ.get("DB_USER", "ssd_user"),
    password=os.environ.get("DB_PASSWORD", ""),
)

CSRF_INPUT_RE = re.compile(r'name="csrf_token"\s+value="([^"]+)"')


def count_rows():
    conn = psycopg2.connect(**DB_CONFIG)
    try:
        with conn.cursor() as cur:
            cur.execute('SELECT COUNT(*) FROM "2401807"')
            return cur.fetchone()[0]
    finally:
        conn.close()


def post_search(session, term):
    """Fetch a fresh CSRF token from the home page, then submit the search
    form with it - mirrors what a real browser does via the hidden field."""
    home_resp = session.get(APP_URL + "/")
    token = CSRF_INPUT_RE.search(home_resp.text).group(1)
    return session.post(APP_URL + "/search", data={"search_term": term, "csrf_token": token})


def test_home_page_loads_with_search_form():
    resp = requests.get(APP_URL + "/")
    assert resp.status_code == 200
    assert 'name="search_term"' in resp.text
    assert 'type="submit"' in resp.text


def test_search_without_csrf_token_is_rejected():
    resp = requests.post(APP_URL + "/search", data={"search_term": "no token"})
    assert resp.status_code == 400


@pytest.mark.parametrize(
    "term",
    [
        "' OR '1'='1",
        "1; DROP TABLE users;--",
        "UNION SELECT password FROM users",
    ],
)
def test_sql_injection_is_rejected_and_not_logged(term):
    before = count_rows()
    with requests.Session() as session:
        resp = post_search(session, term)
    assert resp.status_code == 200
    assert "SQL Injection" in resp.text
    assert count_rows() == before


@pytest.mark.parametrize(
    "term",
    [
        "<script>alert(1)</script>",
        "<img src=x onerror=alert(1)>",
        "javascript:alert(1)",
    ],
)
def test_xss_is_rejected_and_not_logged(term):
    before = count_rows()
    with requests.Session() as session:
        resp = post_search(session, term)
    assert resp.status_code == 200
    assert "XSS" in resp.text
    assert count_rows() == before


def test_empty_search_term_is_rejected():
    with requests.Session() as session:
        resp = post_search(session, "")
    assert resp.status_code == 200
    assert "at least 1 character" in resp.text


def test_overlong_search_term_is_rejected():
    with requests.Session() as session:
        resp = post_search(session, "a" * 101)
    assert resp.status_code == 200
    assert "must not exceed 100 characters" in resp.text


def test_valid_search_is_accepted_and_logged():
    before = count_rows()
    term = f"integration test {int(time.time())}"

    with requests.Session() as session:
        resp = post_search(session, term)

    assert resp.status_code == 200
    assert term in resp.text
    assert "Back to Home" in resp.text
    assert count_rows() == before + 1
