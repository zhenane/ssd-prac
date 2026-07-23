"""
Browser-driven UI tests for the Flask search application, run over plain
HTTP with Playwright (headless Chromium).

Covers the actual user-facing flow: filling in the form, submitting it,
and seeing either the results page or an inline error - plus a check that
server-side validation still holds even with JavaScript disabled, since
the client-side check is UX only and must never be the sole defense.
"""
import os
import time

from playwright.sync_api import sync_playwright

APP_URL = os.environ.get("APP_URL", "http://127.0.0.1:5000").rstrip("/")


def test_ui_home_page_has_search_form():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        try:
            page = browser.new_page()
            page.goto(APP_URL + "/")
            assert page.locator("#search_term").is_visible()
            assert page.locator("#search-form button[type=submit]").is_visible()
        finally:
            browser.close()


def test_ui_valid_search_flow_and_back_to_home():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        try:
            page = browser.new_page()
            page.goto(APP_URL + "/")

            term = f"ui test {int(time.time())}"
            page.fill("#search_term", term)
            page.click("#search-form button[type=submit]")

            page.wait_for_selector("h1:text('Search Results')")
            assert term in page.content()

            page.click("text=Back to Home")
            page.wait_for_selector("h1:text('Search')")
            assert page.locator("#search_term").is_visible()
        finally:
            browser.close()


def test_ui_client_side_validation_blocks_xss_before_submit():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        try:
            page = browser.new_page()
            page.goto(APP_URL + "/")

            page.fill("#search_term", "<script>alert(1)</script>")
            page.click("#search-form button[type=submit]")

            page.wait_for_selector("#client-error:not(:empty)")
            assert "XSS" in page.inner_text("#client-error")
            # never navigated away from the home page, and the field was cleared
            assert page.url.rstrip("/") == APP_URL
            assert page.locator("#search_term").input_value() == ""
        finally:
            browser.close()


def test_ui_server_side_validation_blocks_sqli_when_js_disabled():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        try:
            # Disable JavaScript to prove the server re-validates independently
            # of the client-side check (OWASP C3: never trust the client).
            context = browser.new_context(java_script_enabled=False)
            page = context.new_page()
            page.goto(APP_URL + "/")

            page.fill("#search_term", "' OR '1'='1")
            page.click("#search-form button[type=submit]")
            page.wait_for_load_state("networkidle")

            assert "SQL Injection" in page.content()
            assert page.locator("#search_term").input_value() == ""
        finally:
            browser.close()
