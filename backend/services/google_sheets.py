"""
Google OAuth + Sheets API service.

Handles:
1. OAuth flow (login URL, callback, token storage)
2. Creating a Vigilens spreadsheet on the manager's Google account
3. Appending finding rows to the sheet
"""

from __future__ import annotations

import json
import os
from typing import Optional

from dotenv import load_dotenv
load_dotenv()

os.environ["OAUTHLIB_RELAX_TOKEN_SCOPE"] = "1"

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from sqlalchemy.orm import Session

from backend.models import GoogleAccount

# OAuth config — set these in .env
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8000/api/google/callback")

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/userinfo.email",
    "openid",
]

SHEET_HEADERS = [
    "Employee Name",
    "Finding Type",
    "Severity",
    "Status",
    "Timestamp",
    "Policy Citation",
    "Coaching Recommendation",
    "Date Logged",
]


_pending_verifiers: dict[str, str] = {}


def _client_config() -> dict:
    return {
        "web": {
            "client_id": GOOGLE_CLIENT_ID,
            "client_secret": GOOGLE_CLIENT_SECRET,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [GOOGLE_REDIRECT_URI],
        }
    }


def get_oauth_login_url(manager_id: str) -> str:
    """Generate the Google OAuth consent URL."""
    flow = Flow.from_client_config(_client_config(), scopes=SCOPES)
    flow.redirect_uri = GOOGLE_REDIRECT_URI

    auth_url, state = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
        state=manager_id,
    )
    # Store the code verifier so the callback can use it
    if flow.code_verifier:
        _pending_verifiers[manager_id] = flow.code_verifier
    return auth_url


def handle_oauth_callback(code: str, manager_id: str, db: Session) -> GoogleAccount:
    """Exchange the auth code for tokens and store them."""
    flow = Flow.from_client_config(_client_config(), scopes=SCOPES)
    flow.redirect_uri = GOOGLE_REDIRECT_URI
    # Restore the code verifier from the login step
    code_verifier = _pending_verifiers.pop(manager_id, None)
    flow.fetch_token(code=code, code_verifier=code_verifier)

    creds = flow.credentials

    # Get user email
    from googleapiclient.discovery import build as build_svc
    oauth2 = build_svc("oauth2", "v2", credentials=creds)
    user_info = oauth2.userinfo().get().execute()
    email = user_info.get("email", "")

    # Upsert the account
    account = db.query(GoogleAccount).filter(GoogleAccount.id == manager_id).first()
    if account:
        account.email = email
        account.access_token = creds.token
        account.refresh_token = creds.refresh_token or account.refresh_token
        account.scopes = json.dumps(SCOPES)
    else:
        account = GoogleAccount(
            id=manager_id,
            email=email,
            access_token=creds.token,
            refresh_token=creds.refresh_token or "",
            scopes=json.dumps(SCOPES),
        )
        db.add(account)

    db.commit()
    db.refresh(account)
    return account


def _get_credentials(account: GoogleAccount) -> Credentials:
    """Build Google credentials from stored tokens."""
    return Credentials(
        token=account.access_token,
        refresh_token=account.refresh_token,
        token_uri=account.token_uri,
        client_id=GOOGLE_CLIENT_ID,
        client_secret=GOOGLE_CLIENT_SECRET,
        scopes=json.loads(account.scopes) if account.scopes else SCOPES,
    )


def create_vigilens_sheet(account: GoogleAccount, db: Session) -> dict:
    """Create a new 'Vigilens Findings' spreadsheet and store its ID."""
    creds = _get_credentials(account)
    service = build("sheets", "v4", credentials=creds)

    spreadsheet = service.spreadsheets().create(
        body={
            "properties": {"title": "Vigilens — Findings Log"},
            "sheets": [{
                "properties": {"title": "Findings"},
                "data": [{
                    "startRow": 0,
                    "startColumn": 0,
                    "rowData": [{
                        "values": [
                            {"userEnteredValue": {"stringValue": h}}
                            for h in SHEET_HEADERS
                        ]
                    }],
                }],
            }],
        }
    ).execute()

    sheet_id = spreadsheet["spreadsheetId"]
    sheet_url = spreadsheet["spreadsheetUrl"]

    account.sheet_id = sheet_id
    account.sheet_url = sheet_url
    db.commit()

    return {"sheet_id": sheet_id, "sheet_url": sheet_url}


def append_findings_to_sheet(
    account: GoogleAccount,
    employee_name: str,
    findings: list[dict],
) -> int:
    """Append finding rows to the manager's Vigilens sheet.
    Returns the number of rows appended."""
    if not account.sheet_id:
        raise ValueError("No sheet created yet. Call create_vigilens_sheet first.")

    creds = _get_credentials(account)
    service = build("sheets", "v4", credentials=creds)

    from datetime import datetime
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    rows = []
    for f in findings:
        concluded = f.get("concluded_type", "unknown").replace("_", " ").title()
        severity = f.get("severity", "")
        status = f.get("status", "").replace("_", " ")
        timestamp = f.get("timestamp_start", "")
        policy = f"{f.get('policy_code', '')} {f.get('policy_section', '')}".strip()
        coaching = f.get("training_recommendation") or f.get("coaching_recommendation", "")

        rows.append([
            employee_name,
            concluded,
            severity,
            status,
            timestamp,
            policy,
            coaching,
            now,
        ])

    service.spreadsheets().values().append(
        spreadsheetId=account.sheet_id,
        range="Findings!A:H",
        valueInputOption="RAW",
        body={"values": rows},
    ).execute()

    return len(rows)


def get_account(manager_id: str, db: Session) -> Optional[GoogleAccount]:
    """Get the stored Google account for a manager."""
    return db.query(GoogleAccount).filter(GoogleAccount.id == manager_id).first()
