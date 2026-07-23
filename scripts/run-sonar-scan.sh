#!/usr/bin/env bash
# Runs a local SonarQube scan of the app/ source code (Q4) against the
# SonarQube instance provisioned in docker-compose (Q7). Uses the scanner
# CLI Docker image attached to the compose network, talking to SonarQube
# over its internal HTTP address (no self-signed cert trust needed) -
# results still show up on the public https://127.0.0.1:9000/ UI.
set -euo pipefail

SONAR_URL="https://127.0.0.1:9000"
SONAR_ADMIN_PASSWORD="2401807@SIT.singaporetech.edu.sg"
SONAR_INTERNAL_URL="http://sonarqube:9000"
NETWORK="ssd-prac_default"
PROJECT_KEY="ssd-prac-app"

TOKEN=$(curl -sk -u "admin:$SONAR_ADMIN_PASSWORD" -X POST \
  "$SONAR_URL/api/user_tokens/generate" \
  --data-urlencode "name=scanner-token-$(date +%s)" \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['token'])")

docker run --rm \
  --network "$NETWORK" \
  -v "$(pwd)/app:/usr/src" \
  -w /usr/src \
  -e SONAR_HOST_URL="$SONAR_INTERNAL_URL" \
  -e SONAR_TOKEN="$TOKEN" \
  sonarsource/sonar-scanner-cli

echo
echo "Scan complete. View results at $SONAR_URL/dashboard?id=$PROJECT_KEY"
