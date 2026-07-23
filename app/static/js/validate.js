/**
 * Client-side input validation (OWASP Proactive Control C3: Validate All
 * Input - frontend layer). This exists only for immediate user feedback and
 * to avoid unnecessary round-trips; it is NOT a security boundary. Anyone
 * can bypass this by calling POST /search directly, which is why the
 * server (validation.py) enforces the same rules again and is the only
 * check that is actually trusted.
 *
 * No unicode handling is required: only plain ASCII letters, digits and
 * spaces are accepted, mirroring the server-side allow-list.
 */
(function () {
    "use strict";

    var MIN_LENGTH = 1;
    var MAX_LENGTH = 100;

    var ALLOWED_PATTERN = /^[A-Za-z0-9 ]+$/;
    var SQLI_PATTERN = /(--|;|\/\*|\*\/|'|"|\bunion\b|\bselect\b|\binsert\b|\bupdate\b|\bdelete\b|\bdrop\b|\bexec\b|\bor\b\s+\d+\s*=\s*\d+)/i;
    var XSS_PATTERN = /(<\s*script|<\/\s*script|javascript:|on\w+\s*=|<\s*img|<\s*svg|<\s*iframe|<[^>]+>)/i;

    function validateSearchTerm(rawTerm) {
        var term = (rawTerm || "").trim();

        if (term.length < MIN_LENGTH) {
            return { valid: false, message: "Search term must be at least " + MIN_LENGTH + " character(s) long." };
        }
        if (term.length > MAX_LENGTH) {
            return { valid: false, message: "Search term must not exceed " + MAX_LENGTH + " characters." };
        }
        if (SQLI_PATTERN.test(term)) {
            return { valid: false, message: "Potential SQL Injection attack detected." };
        }
        if (XSS_PATTERN.test(term)) {
            return { valid: false, message: "Potential XSS attack detected." };
        }
        if (!ALLOWED_PATTERN.test(term)) {
            return { valid: false, message: "Only letters, numbers and spaces are allowed." };
        }
        return { valid: true, message: "" };
    }

    document.addEventListener("DOMContentLoaded", function () {
        var form = document.getElementById("search-form");
        var input = document.getElementById("search_term");
        var errorEl = document.getElementById("client-error");

        if (!form) {
            return;
        }

        form.addEventListener("submit", function (event) {
            var result = validateSearchTerm(input.value);
            if (!result.valid) {
                event.preventDefault();
                errorEl.textContent = result.message;
                input.value = "";
                input.focus();
            } else {
                errorEl.textContent = "";
            }
        });
    });
})();
