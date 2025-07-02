import os
import json
import uuid
from models import Member, Meeting
import pytz
from dateutil.parser import parse as parse_dt
from datetime import timedelta

data_dir = 'data'
members_file = os.path.join(data_dir, 'members.json')
meetings_file = os.path.join(data_dir, 'meetings.json')
potential_times_file = os.path.join(data_dir, 'potential_times.json')
config_file = os.path.join(data_dir, 'config.json')

os.makedirs(data_dir, exist_ok=True)

def load_json(path):
    if not os.path.exists(path):
        return []
    with open(path, 'r') as f:
        return json.load(f)

def save_json(path, data):
    with open(path, 'w') as f:
        json.dump(data, f, indent=2)

def add_member(name, calendar_id):
    members = load_json(members_file)
    member_id = str(uuid.uuid4())
    member = Member(id=member_id, name=name, calendar_id=calendar_id)
    members.append(member.__dict__)
    save_json(members_file, members)
    print(f"Added member: {name} (ID: {member_id})")

def list_members():
    members = load_json(members_file)
    if not members:
        print('No members found.')
    for m in members:
        print(f"{m['id']}: {m['name']} (Calendar ID: {m['calendar_id']})")

def remove_member(member_id):
    members = load_json(members_file)
    new_members = [m for m in members if m['id'] != member_id]
    save_json(members_file, new_members)
    print(f"Removed member with ID: {member_id}")

def add_meeting(name, member_ids, duration):
    meetings = load_json(meetings_file)
    meeting_id = str(uuid.uuid4())
    meeting = Meeting(id=meeting_id, name=name, members=member_ids, duration=duration)
    meetings.append(meeting.__dict__)
    save_json(meetings_file, meetings)
    print(f"Added meeting: {name} (ID: {meeting_id})")

def list_meetings():
    meetings = load_json(meetings_file)
    if not meetings:
        print('No meetings found.')
    for m in meetings:
        print(f"{m['id']}: {m['name']} (Members: {', '.join(m['members'])}, Duration: {m['duration']} min)")

def remove_meeting(meeting_id):
    meetings = load_json(meetings_file)
    new_meetings = [m for m in meetings if m['id'] != meeting_id]
    save_json(meetings_file, new_meetings)
    print(f"Removed meeting with ID: {meeting_id}")

def add_potential_time(start_time, end_time):
    times = load_json(potential_times_file)
    time_id = str(uuid.uuid4())
    entry = {
        'id': time_id,
        'start_time': start_time,
        'end_time': end_time
    }
    times.append(entry)
    save_json(potential_times_file, times)
    print(f"Added potential time: {start_time} to {end_time} (ID: {time_id})")

def list_potential_times():
    times = load_json(potential_times_file)
    if not times:
        print('No potential meeting times found.')
    for t in times:
        print(f"{t['id']}: {t['start_time']} to {t['end_time']}")

def remove_potential_time(time_id):
    times = load_json(potential_times_file)
    new_times = [t for t in times if t['id'] != time_id]
    save_json(potential_times_file, new_times)
    print(f"Removed potential time with ID: {time_id}")

def set_potential_times_calendar(calendar_id):
    config = {}
    if os.path.exists(config_file):
        with open(config_file, 'r') as f:
            config = json.load(f)
    config['potential_times_calendar_id'] = calendar_id
    with open(config_file, 'w') as f:
        json.dump(config, f, indent=2)
    print(f"Set potential meeting times calendar ID: {calendar_id}")

def get_potential_times_calendar():
    if not os.path.exists(config_file):
        print('No potential meeting times calendar set.')
        return None
    with open(config_file, 'r') as f:
        config = json.load(f)
    return config.get('potential_times_calendar_id')

def fetch_potential_times_from_calendar(service, week_start, week_end):
    calendar_id = get_potential_times_calendar()
    if not calendar_id:
        print('No potential meeting times calendar set.')
        return []
    events_result = service.events().list(
        calendarId=calendar_id,
        timeMin=week_start,
        timeMax=week_end,
        singleEvents=True,
        orderBy='startTime'
    ).execute()
    events = events_result.get('items', [])
    slots = []
    for event in events:
        start = event['start'].get('dateTime', event['start'].get('date'))
        end = event['end'].get('dateTime', event['end'].get('date'))
        location = event.get('location')
        slots.append({'start_time': start, 'end_time': end, 'summary': event.get('summary', ''), 'location': location})
    return slots

def set_timezone(timezone):
    config = {}
    if os.path.exists(config_file):
        with open(config_file, 'r') as f:
            config = json.load(f)
    config['timezone'] = timezone
    with open(config_file, 'w') as f:
        json.dump(config, f, indent=2)
    print(f"Set default timezone: {timezone}")

def get_timezone():
    if not os.path.exists(config_file):
        return 'America/New_York'
    with open(config_file, 'r') as f:
        config = json.load(f)
    return config.get('timezone', 'America/New_York')

def fetch_member_conflicts(service, calendar_id, week_start, week_end):
    events_result = service.events().list(
        calendarId=calendar_id,
        timeMin=week_start,
        timeMax=week_end,
        singleEvents=True,
        orderBy='startTime'
    ).execute()
    events = events_result.get('items', [])
    conflicts = []
    for event in events:
        start = event['start'].get('dateTime', event['start'].get('date'))
        end = event['end'].get('dateTime', event['end'].get('date'))
        conflicts.append((start, end))
    return conflicts

def overlaps(slot_start, slot_end, conflict_start, conflict_end):
    # All times are ISO strings
    s1 = parse_dt(slot_start)
    e1 = parse_dt(slot_end)
    s2 = parse_dt(conflict_start)
    e2 = parse_dt(conflict_end)
    return max(s1, s2) < min(e1, e2)

def build_availability_matrix(members, slots, conflicts_by_member):
    matrix = {}
    for i, slot in enumerate(slots):
        slot_id = slot.get('id', str(i))
        slot_start = slot['start_time']
        slot_end = slot['end_time']
        available = []
        for member in members:
            member_id = member['id']
            conflicts = conflicts_by_member.get(member_id, [])
            if not any(overlaps(slot_start, slot_end, c[0], c[1]) for c in conflicts):
                available.append(member_id)
        matrix[slot_id] = available
    return matrix

def generate_possible_slots(window_start, window_end, duration_minutes):
    # window_start, window_end: ISO strings
    # Returns list of (slot_start, slot_end) ISO strings
    s = parse_dt(window_start)
    e = parse_dt(window_end)
    slots = []
    # Round up to next half hour if needed
    minute = s.minute
    if minute not in (0, 30):
        s = s.replace(minute=30 if minute < 30 else 0, second=0, microsecond=0)
        if minute > 30:
            s += timedelta(hours=1)
    else:
        s = s.replace(second=0, microsecond=0)
    while s + timedelta(minutes=duration_minutes) <= e:
        slot_start = s
        slot_end = s + timedelta(minutes=duration_minutes)
        slots.append((slot_start.isoformat(), slot_end.isoformat()))
        # Increment by 30 minutes
        s += timedelta(minutes=30)
    return slots 