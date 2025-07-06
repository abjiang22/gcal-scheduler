import json
import os
import uuid
from datetime import timedelta
import pytz
from dateutil.parser import parse as parse_dt
from dateutil.tz import tzutc
from models import Member, Meeting

# Constants
DATA_DIR = 'data'
MEMBERS_FILE = os.path.join(DATA_DIR, 'members.json')
MEETINGS_FILE = os.path.join(DATA_DIR, 'meetings.json')
POTENTIAL_TIMES_FILE = os.path.join(DATA_DIR, 'potential_times.json')
CONFIG_FILE = os.path.join(DATA_DIR, 'config.json')

# Ensure data directory exists
os.makedirs(DATA_DIR, exist_ok=True)

# ===== File I/O Utilities =====

def load_json(path):
    """Load JSON data from a file."""
    if not os.path.exists(path):
        return []
    with open(path, 'r') as f:
        return json.load(f)

def save_json(path, data):
    """Save JSON data to a file."""
    with open(path, 'w') as f:
        json.dump(data, f, indent=2)

# ===== Member Management =====

def add_member(name, calendar_id):
    """Add a new member to the system."""
    members = load_json(MEMBERS_FILE)
    member_id = str(uuid.uuid4())
    member = Member(id=member_id, name=name, calendar_id=calendar_id)
    members.append(member.__dict__)
    save_json(MEMBERS_FILE, members)
    print(f"Added member: {name} (ID: {member_id})")

def list_members():
    """List all members in the system."""
    members = load_json(MEMBERS_FILE)
    if not members:
        print('No members found.')
    for m in members:
        print(f"{m['id']}: {m['name']} (Calendar ID: {m['calendar_id']})")

def remove_member(member_id):
    """Remove a member from the system."""
    members = load_json(MEMBERS_FILE)
    new_members = [m for m in members if m['id'] != member_id]
    save_json(MEMBERS_FILE, new_members)
    print(f"Removed member with ID: {member_id}")

# ===== Meeting Management =====

def add_meeting(name, member_ids, duration):
    """Add a new meeting to the system."""
    meetings = load_json(MEETINGS_FILE)
    meeting_id = str(uuid.uuid4())
    meeting = Meeting(id=meeting_id, name=name, members=member_ids, duration=duration)
    meetings.append(meeting.__dict__)
    save_json(MEETINGS_FILE, meetings)
    print(f"Added meeting: {name} (ID: {meeting_id})")

def list_meetings():
    """List all meetings in the system."""
    meetings = load_json(MEETINGS_FILE)
    if not meetings:
        print('No meetings found.')
    for m in meetings:
        print(f"{m['id']}: {m['name']} (Members: {', '.join(m['members'])}, Duration: {m['duration']} min)")

def remove_meeting(meeting_id):
    """Remove a meeting from the system."""
    meetings = load_json(MEETINGS_FILE)
    new_meetings = [m for m in meetings if m['id'] != meeting_id]
    save_json(MEETINGS_FILE, new_meetings)
    print(f"Removed meeting with ID: {meeting_id}")

# ===== Potential Time Management =====

def add_potential_time(start_time, end_time):
    """Add a new potential meeting time to the system."""
    times = load_json(POTENTIAL_TIMES_FILE)
    time_id = str(uuid.uuid4())
    entry = {
        'id': time_id,
        'start_time': start_time,
        'end_time': end_time
    }
    times.append(entry)
    save_json(POTENTIAL_TIMES_FILE, times)
    print(f"Added potential time: {start_time} to {end_time} (ID: {time_id})")

def list_potential_times():
    """List all potential meeting times in the system."""
    times = load_json(POTENTIAL_TIMES_FILE)
    if not times:
        print('No potential meeting times found.')
    for t in times:
        print(f"{t['id']}: {t['start_time']} to {t['end_time']}")

def remove_potential_time(time_id):
    """Remove a potential meeting time from the system."""
    times = load_json(POTENTIAL_TIMES_FILE)
    new_times = [t for t in times if t['id'] != time_id]
    save_json(POTENTIAL_TIMES_FILE, new_times)
    print(f"Removed potential time with ID: {time_id}")

# ===== Configuration Management =====

def set_potential_times_calendar(calendar_id):
    """Set the potential meeting times calendar ID in configuration."""
    config = {}
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f:
            config = json.load(f)
    config['potential_times_calendar_id'] = calendar_id
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=2)
    print(f"Set potential meeting times calendar ID: {calendar_id}")

def get_potential_times_calendar():
    """Get the potential meeting times calendar ID from configuration."""
    if not os.path.exists(CONFIG_FILE):
        print('No potential meeting times calendar set.')
        return None
    with open(CONFIG_FILE, 'r') as f:
        config = json.load(f)
    return config.get('potential_times_calendar_id')

def set_timezone(timezone):
    """Set the default timezone in configuration."""
    config = {}
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f:
            config = json.load(f)
    config['timezone'] = timezone
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=2)
    print(f"Set default timezone: {timezone}")

def get_timezone():
    """Get the default timezone from configuration."""
    if not os.path.exists(CONFIG_FILE):
        return 'America/New_York'
    with open(CONFIG_FILE, 'r') as f:
        config = json.load(f)
    return config.get('timezone', 'America/New_York')

# ===== Calendar Integration =====

def fetch_potential_times_from_calendar(service, week_start, week_end):
    """Fetch potential meeting times from the configured Google Calendar."""
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

def fetch_member_conflicts(service, calendar_id, week_start, week_end):
    """Fetch conflicts for a member from their Google Calendar."""
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

# ===== Time and Scheduling Utilities =====

def overlaps(slot_start, slot_end, conflict_start, conflict_end):
    """Check if two time slots overlap."""
    # All times are ISO strings
    s1 = parse_dt(slot_start)
    e1 = parse_dt(slot_end)
    s2 = parse_dt(conflict_start)
    e2 = parse_dt(conflict_end)
    # Make all datetimes timezone-aware (UTC) if naive
    if s1.tzinfo is None:
        s1 = s1.replace(tzinfo=tzutc())
    if e1.tzinfo is None:
        e1 = e1.replace(tzinfo=tzutc())
    if s2.tzinfo is None:
        s2 = s2.replace(tzinfo=tzutc())
    if e2.tzinfo is None:
        e2 = e2.replace(tzinfo=tzutc())
    return max(s1, s2) < min(e1, e2)

def build_availability_matrix(members, slots, conflicts_by_member):
    """Build a matrix showing which members are available for each time slot."""
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
    """Generate possible meeting slots within a time window."""
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