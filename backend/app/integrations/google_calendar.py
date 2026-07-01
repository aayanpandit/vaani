import os
import dateparser
from datetime import datetime, timedelta


from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build


SCOPES = ["https://www.googleapis.com/auth/calendar"]

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))

CREDENTIALS_PATH = os.path.join(BASE_DIR, "credentials", "credentials.json")
TOKEN_PATH = os.path.join(BASE_DIR, "credentials", "token.json")


def get_calendar_service():
    creds = None

    if os.path.exists(TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                CREDENTIALS_PATH,
                SCOPES,
            )
            creds = flow.run_local_server(
    port=8080,
    prompt="consent",
)

        with open(TOKEN_PATH, "w") as token:
            token.write(creds.to_json())

    return build("calendar", "v3", credentials=creds)


def create_calendar_event(
    summary: str,
    start_datetime: str,
    duration_minutes: int = 30,
):
    service = get_calendar_service()

    start = dateparser.parse(
    start_datetime,
    settings={
        "TIMEZONE": "Asia/Kolkata",
        "RETURN_AS_TIMEZONE_AWARE": False,
    },
)
    end = start + timedelta(minutes=duration_minutes)

    event = {
        "summary": summary,
        "start": {
            "dateTime": start.isoformat(),
            "timeZone": "Asia/Kolkata",
        },
        "end": {
            "dateTime": end.isoformat(),
            "timeZone": "Asia/Kolkata",
        },
    }

    created_event = service.events().insert(
        calendarId="primary",
        body=event,
    ).execute()

    return created_event

def delete_calendar_event(event_id: str):
    service = get_calendar_service()

    service.events().delete(
        calendarId="primary",
        eventId=event_id,
    ).execute()

    return True

def update_calendar_event(
    event_id: str,
    start_datetime: str,
    duration_minutes: int = 30,
):
    from datetime import timedelta
    import dateparser

    service = get_calendar_service()

    start = dateparser.parse(start_datetime)

    if not start:
        raise ValueError(f"Could not parse datetime: {start_datetime}")

    end = start + timedelta(minutes=duration_minutes)

    event = service.events().get(
        calendarId="primary",
        eventId=event_id,
    ).execute()

    event["start"] = {
        "dateTime": start.isoformat(),
        "timeZone": "Asia/Kolkata",
    }

    event["end"] = {
        "dateTime": end.isoformat(),
        "timeZone": "Asia/Kolkata",
    }

    updated_event = service.events().update(
        calendarId="primary",
        eventId=event_id,
        body=event,
    ).execute()

    return updated_event