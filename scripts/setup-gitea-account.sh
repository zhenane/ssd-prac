#!/usr/bin/env bash
# One-time setup: creates the Gitea admin account for this local git server.
# Run after `docker compose up -d` and once the gitea container has finished
# its first-run initialization (a few seconds).
set -euo pipefail

GITEA_USERNAME="GohZhenAnErnest"   # Gitea usernames cannot contain spaces
GITEA_FULLNAME="Goh Zhen An Ernest"
GITEA_EMAIL="2401807@sit.singaporetech.edu.sg"
GITEA_PASSWORD="2401807@sit.singaporetech.edu.sg"

# 1. Create the admin user via the Gitea CLI inside the container.
docker compose exec -T -u git gitea gitea admin user create \
  --username "$GITEA_USERNAME" \
  --password "$GITEA_PASSWORD" \
  --email "$GITEA_EMAIL" \
  --admin \
  --must-change-password=false

# 2. The CLI has no flag for the display "Full Name", so set it via the
#    admin REST API (requires the account just created above).
curl -s -o /dev/null -w '%{http_code}\n' -u "$GITEA_USERNAME:$GITEA_PASSWORD" \
  -H "Content-Type: application/json" \
  -X PATCH "http://127.0.0.1:3000/api/v1/admin/users/$GITEA_USERNAME" \
  -d "{\"login_name\":\"$GITEA_USERNAME\",\"email\":\"$GITEA_EMAIL\",\"full_name\":\"$GITEA_FULLNAME\"}"

echo "Gitea admin account ready:"
echo "  Username  : $GITEA_USERNAME"
echo "  Full name : $GITEA_FULLNAME"
echo "  Email     : $GITEA_EMAIL"
echo "  Login at  : http://127.0.0.1:3000/"
