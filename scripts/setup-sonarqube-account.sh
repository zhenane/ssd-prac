#!/usr/bin/env bash
# One-time setup: sets the SonarQube admin password for a freshly started
# instance (default credentials are admin/admin). Run after `docker compose
# up -d sonarqube` once https://127.0.0.1:9000/api/system/status reports
# {"status":"UP"} (first boot can take a couple of minutes).
#
# Note: SonarQube enforces a built-in password policy (minimum length plus
# upper/lower-case, digit and special character) that cannot be disabled via
# settings. '2401807@sit.singaporetech.edu.sg' fails it (no uppercase), so
# the admin password used here capitalizes "SIT" instead.
set -euo pipefail

SONAR_URL="https://127.0.0.1:9000"
NEW_PASSWORD="2401807@SIT.singaporetech.edu.sg"

curl -sk -u 'admin:admin' -X POST "$SONAR_URL/api/users/change_password" \
  --data-urlencode "login=admin" \
  --data-urlencode "previousPassword=admin" \
  --data-urlencode "password=$NEW_PASSWORD" \
  -w "change_password HTTP %{http_code}\n" -o /dev/null

echo "SonarQube admin account ready:"
echo "  Username: admin"
echo "  Password: $NEW_PASSWORD"
echo "  URL     : $SONAR_URL/"
