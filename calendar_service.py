from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
import pickle
import os
from datetime import datetime, timedelta

SCOPES = ['https://www.googleapis.com/auth/calendar']
TOKEN_PATH = 'token.pickle'
CREDENTIALS_PATH = 'credentials.json'

def authenticate_google():
    creds = None
    if os.path.exists(TOKEN_PATH):
        with open(TOKEN_PATH, 'rb') as token:
            creds = pickle.load(token)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_PATH, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_PATH, 'wb') as token:
            pickle.dump(creds, token)
    service = build('calendar', 'v3', credentials=creds)
    return service

def list_calendars(service):
    calendars = service.calendarList().list().execute()
    for cal in calendars.get('items', []):
        print(f"{cal['summary']} (ID: {cal['id']})")

def list_events(service, calendar_id, days=7):
    now = datetime.utcnow().isoformat() + 'Z'
    future = (datetime.utcnow() + timedelta(days=days)).isoformat() + 'Z'
    events_result = service.events().list(calendarId=calendar_id, timeMin=now, timeMax=future, singleEvents=True, orderBy='startTime').execute()
    events = events_result.get('items', [])
    if not events:
        print('No upcoming events found.')
    for event in events:
        start = event['start'].get('dateTime', event['start'].get('date'))
        print(f"{start}: {event['summary']}")

def get_or_create_calendar(service, calendar_name):
    # Check if calendar exists
    calendars = service.calendarList().list().execute()
    for cal in calendars.get('items', []):
        if cal['summary'] == calendar_name:
            return cal['id']
    # Create new calendar
    calendar = {
        'summary': calendar_name,
        'timeZone': 'UTC',
    }
    created = service.calendars().insert(body=calendar).execute()
    return created['id']

def create_event(service, calendar_id, summary, start_time, end_time, attendees=None, description=None, location=None):
    event = {
        'summary': summary,
        'start': {'dateTime': start_time, 'timeZone': 'UTC'},
        'end': {'dateTime': end_time, 'timeZone': 'UTC'},
    }
    if attendees:
        event['attendees'] = [{'email': email} for email in attendees]
    if description:
        event['description'] = description
    if location:
        event['location'] = location
    service.events().insert(calendarId=calendar_id, body=event).execute() 