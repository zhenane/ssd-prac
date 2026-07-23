const js = require("@eslint/js");
const security = require("eslint-plugin-security");
const noUnsanitized = require("eslint-plugin-no-unsanitized");
const globals = require("globals");

module.exports = [
  js.configs.recommended,
  security.configs.recommended,
  {
    files: ["app/static/js/**/*.js"],
    plugins: {
      "no-unsanitized": noUnsanitized,
    },
    languageOptions: {
      ecmaVersion: 2021,
      sourceType: "script",
      globals: {
        ...globals.browser,
      },
    },
    rules: {
      ...noUnsanitized.configs.recommended.rules,
    },
  },
];
