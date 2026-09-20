#!/usr/bin/env bash
# GrantBot — Google Calendar OAuth Setup
# Run this once after placing your credentials.json file.
set -euo pipefail

CRED_DIR="$HOME/.config/grantbot"
CRED_FILE="$CRED_DIR/calendar_credentials.json"
TOKEN_FILE="$CRED_DIR/calendar_token.json"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "╔══════════════════════════════════════════════════╗"
echo "║   GrantBot — Google Calendar Setup              ║"
echo "╚══════════════════════════════════════════════════╝"

if [ ! -f "$CRED_FILE" ]; then
    echo ""
    echo "MISSING: $CRED_FILE"
    echo ""
    echo "To create it:"
    echo "  1. Go to https://console.cloud.google.com"
    echo "  2. Create a new project (or select existing)"
    echo "  3. Go to APIs & Services > Library"
    echo "  4. Search 'Google Calendar API' and click Enable"
    echo "  5. Go to APIs & Services > Credentials"
    echo "  6. Click '+ CREATE CREDENTIALS' > OAuth client ID"
    echo "  7. If prompted, configure OAuth consent screen:"
    echo "     - User type: External"
    echo "     - App name: GrantBot"
    echo "     - Add your email as test user"
    echo "  8. Application type: Desktop app"
    echo "  9. Name: GrantBot Calendar"
    echo " 10. Click Create"
    echo " 11. Click the download icon (JSON) next to your new client"
    echo " 12. Save the file as:"
    echo "     $CRED_FILE"
    echo ""
    echo "Then run this script again."
    exit 1
fi

echo "Credentials found. Starting OAuth flow..."
echo "A browser window will open — sign in and click Allow."
echo ""

cd "$SCRIPT_DIR"

python3 -c "
import os, sys
sys.path.insert(0, '$SCRIPT_DIR')

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

SCOPES = ['https://www.googleapis.com/auth/calendar']
CREDS = '$CRED_FILE'
TOKEN = '$TOKEN_FILE'

creds = None
if os.path.exists(TOKEN):
    creds = Credentials.from_authorized_user_file(TOKEN, SCOPES)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
    print('Token refreshed successfully.')
else:
    flow = InstalledAppFlow.from_client_secrets_file(CREDS, SCOPES)
    creds = flow.run_local_server(port=8090)
    print('OAuth flow completed.')

os.makedirs(os.path.dirname(TOKEN), exist_ok=True)
with open(TOKEN, 'w') as f:
    f.write(creds.to_json())

print(f'Token saved to: {TOKEN}')
print('Calendar sync is now active.')
" 2>&1

if [ $? -eq 0 ]; then
    echo ""
    echo "SUCCESS. Running pipeline with live calendar sync..."
    python3 "$SCRIPT_DIR/pipeline.py" 2>&1 | grep -E "(Calendar|ICS|PIPELINE|Discovered|Qualified|Drafts|Complete|Saved)"
else
    echo "Setup failed. Check error above."
fi
