import argparse
import json
import os
import re
import uuid
from collections import defaultdict
from datetime import datetime
import pytz
import yaml
from pysat.card import CardEnc
from pysat.examples.rc2 import RC2
from pysat.formula import IDPool, WCNF
from pysat.solvers import Glucose3

from calendar_service import (
    authenticate_google, create_event, get_or_create_calendar, 
    list_calendars, list_events
)
from models import Member, Meeting
from utils import (
    add_member, add_meeting, add_potential_time, fetch_member_conflicts,
    fetch_potential_times_from_calendar, generate_possible_slots, get_potential_times_calendar,
    get_timezone, list_meetings, list_members, list_potential_times, load_json,
    overlaps, remove_meeting, remove_member, remove_potential_time,
    set_potential_times_calendar, set_timezone
)

def main():
    """Main entry point for the gcal-scheduler CLI application."""
    # Configure pysat data directory
    import pysat
    pysat.params['data_dirs'] = os.path.join(os.getcwd(), 'pysatData')
    
    parser = argparse.ArgumentParser(description='gcal-scheduler CLI')
    subparsers = parser.add_subparsers(dest='command')

    # ===== Google Calendar Commands =====
    parser_auth = subparsers.add_parser('auth', help='Authenticate with Google Calendar')
    parser_list_cal = subparsers.add_parser('list-calendars', help='List all calendars')
    parser_list_events = subparsers.add_parser('list-events', help='List events for a calendar')
    parser_list_events.add_argument('calendar_id', type=str, help='Calendar ID')

    # ===== Member Management Commands =====
    parser_add_member = subparsers.add_parser('add-member', help='Add a member')
    parser_add_member.add_argument('name', type=str, help='Member name')
    parser_add_member.add_argument('calendar_id', type=str, help='Google Calendar ID')
    parser_list_members = subparsers.add_parser('list-members', help='List all members')
    parser_remove_member = subparsers.add_parser('remove-member', help='Remove a member')
    parser_remove_member.add_argument('member_id', type=str, help='Member ID')

    # ===== Meeting Management Commands =====
    parser_add_meeting = subparsers.add_parser('add-meeting', help='Add a meeting')
    parser_add_meeting.add_argument('name', type=str, help='Meeting name')
    parser_add_meeting.add_argument('member_ids', nargs='+', help='Member IDs')
    parser_add_meeting.add_argument('--duration', type=int, default=60, help='Duration in minutes')
    parser_list_meetings = subparsers.add_parser('list-meetings', help='List all meetings')
    parser_remove_meeting = subparsers.add_parser('remove-meeting', help='Remove a meeting')
    parser_remove_meeting.add_argument('meeting_id', type=str, help='Meeting ID')

    # ===== Potential Meeting Time Management =====
    parser_add_time = subparsers.add_parser('add-potential-time', help='Add a potential meeting time')
    parser_add_time.add_argument('start_time', type=str, help='Start time (ISO format)')
    parser_add_time.add_argument('end_time', type=str, help='End time (ISO format)')
    parser_list_times = subparsers.add_parser('list-potential-times', help='List all potential meeting times')
    parser_remove_time = subparsers.add_parser('remove-potential-time', help='Remove a potential meeting time')
    parser_remove_time.add_argument('time_id', type=str, help='Potential time ID')

    # ===== Calendar Configuration Commands =====
    parser_set_cal = subparsers.add_parser('set-potential-times-calendar', help='Set the potential meeting times calendar ID')
    parser_set_cal.add_argument('calendar_id', type=str, help='Calendar ID')
    parser_show_cal = subparsers.add_parser('show-potential-times-calendar', help='Show the current potential meeting times calendar ID')
    parser_fetch_times = subparsers.add_parser('fetch-potential-times', help='Fetch and list potential meeting times from the calendar for a given week')
    parser_fetch_times.add_argument('week_start', type=str, help='Week start (ISO format)')
    parser_fetch_times.add_argument('week_end', type=str, help='Week end (ISO format)')

    # ===== Timezone Management =====
    parser_set_tz = subparsers.add_parser('set-timezone', help='Set the default timezone (e.g., America/New_York)')
    parser_set_tz.add_argument('timezone', type=str, help='Timezone name')
    parser_show_tz = subparsers.add_parser('show-timezone', help='Show the current default timezone')

    # ===== Scheduling Commands =====
    parser_schedule = subparsers.add_parser('schedule-meetings', help='Schedule meetings for the given week')
    parser_schedule.add_argument('week_start', type=str, help='Week start (YYYY-MM-DD or ISO)')
    parser_schedule.add_argument('week_end', type=str, help='Week end (YYYY-MM-DD or ISO)')
    parser_schedule.add_argument('--save-calendar', type=str, metavar='CALENDAR_NAME', help='Name of the calendar to create and save the meeting schedule to')
    parser_schedule.add_argument('--penalty-key-attendee-absence', type=int, default=None, help='Penalty for key attendee absence (overrides config)')
    parser_schedule.add_argument('--penalty-required-member-absence', type=int, default=None, help='Penalty for required member absence (overrides config)')
    parser_schedule.add_argument('--penalty-key-meeting-absence', type=int, default=None, help='Penalty for key meeting absence (overrides config)')

    # ===== Configuration Commands =====
    parser_load_config = subparsers.add_parser('load-config', help='Load members, meetings, and potential times calendar from a YAML config file')
    parser_load_config.add_argument('config_file', type=str, help='YAML config file path')
    parser_add_constraint = subparsers.add_parser('add-constraint', help='Add a fixed constraint that mandates members must attend a meeting')
    parser_add_constraint.add_argument('meeting', type=str, help='Meeting name')
    parser_add_constraint.add_argument('members', nargs='+', help='Member name(s)')
    parser_set_active_meetings = subparsers.add_parser('set-active-meetings', help='Set the list of active meetings to schedule')
    parser_set_active_meetings.add_argument('meeting_names', nargs='+', help='Names of meetings to schedule')

    args = parser.parse_args()

    # ===== Google Calendar Commands =====
    if args.command in ['auth', 'list-calendars', 'list-events']:
        service = authenticate_google()
        if args.command == 'list-calendars':
            list_calendars(service)
        elif args.command == 'list-events':
            list_events(service, args.calendar_id)
        else:
            print('Authenticated with Google Calendar.')
    
    # ===== Member Management Commands =====
    elif args.command == 'add-member':
        add_member(args.name, args.calendar_id)
    elif args.command == 'list-members':
        list_members()
    elif args.command == 'remove-member':
        remove_member(args.member_id)
    
    # ===== Meeting Management Commands =====
    elif args.command == 'add-meeting':
        add_meeting(args.name, args.member_ids, args.duration)
    elif args.command == 'list-meetings':
        list_meetings()
    elif args.command == 'remove-meeting':
        remove_meeting(args.meeting_id)
    
    # ===== Potential Time Management Commands =====
    elif args.command == 'add-potential-time':
        add_potential_time(args.start_time, args.end_time)
    elif args.command == 'list-potential-times':
        list_potential_times()
    elif args.command == 'remove-potential-time':
        remove_potential_time(args.time_id)
    
    # ===== Calendar Configuration Commands =====
    elif args.command == 'set-potential-times-calendar':
        set_potential_times_calendar(args.calendar_id)
    elif args.command == 'show-potential-times-calendar':
        cal_id = get_potential_times_calendar()
        if cal_id:
            print(f"Potential meeting times calendar ID: {cal_id}")
    
    # ===== Timezone Management Commands =====
    elif args.command == 'set-timezone':
        set_timezone(args.timezone)
    elif args.command == 'show-timezone':
        print(f"Default timezone: {get_timezone()}")
    elif args.command == 'fetch-potential-times':
        # Accept YYYY-MM-DD or full ISO, interpret in user's timezone
        def to_utc_iso(dt_str, is_start, tz_name):
            date_pattern = r'^\d{4}-\d{2}-\d{2}$'
            tz = pytz.timezone(tz_name)
            if re.match(date_pattern, dt_str):
                dt = datetime.strptime(dt_str, '%Y-%m-%d')
                if is_start:
                    dt = tz.localize(dt.replace(hour=0, minute=0, second=0))
                else:
                    dt = tz.localize(dt.replace(hour=23, minute=59, second=59))
                return dt.astimezone(pytz.utc).isoformat().replace('+00:00', 'Z')
            # If already ISO, try to parse and convert
            try:
                dt = datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
                if dt.tzinfo is None:
                    dt = tz.localize(dt)
                return dt.astimezone(pytz.utc).isoformat().replace('+00:00', 'Z')
            except Exception:
                return dt_str
        tz_name = get_timezone()
        week_start = to_utc_iso(args.week_start, True, tz_name)
        week_end = to_utc_iso(args.week_end, False, tz_name)
        service = authenticate_google()
        slots = fetch_potential_times_from_calendar(service, week_start, week_end)
        if not slots:
            print('No potential meeting times found in the calendar.')
        else:
            tz = pytz.timezone(tz_name)
            for slot in slots:
                # Convert UTC to local timezone for display
                try:
                    start_dt = datetime.fromisoformat(slot['start_time'].replace('Z', '+00:00')).astimezone(tz)
                    end_dt = datetime.fromisoformat(slot['end_time'].replace('Z', '+00:00')).astimezone(tz)
                    print(f"{start_dt.strftime('%Y-%m-%d %H:%M:%S %Z')} to {end_dt.strftime('%Y-%m-%d %H:%M:%S %Z')} - {slot['summary']}")
                except Exception:
                    print(f"{slot['start_time']} to {slot['end_time']} - {slot['summary']}")
    elif args.command == 'schedule-meetings':
        # Parse week range in user's timezone
        def to_utc_iso(dt_str, is_start, tz_name):
            date_pattern = r'^\d{4}-\d{2}-\d{2}$'
            tz = pytz.timezone(tz_name)
            if re.match(date_pattern, dt_str):
                dt = datetime.strptime(dt_str, '%Y-%m-%d')
                if is_start:
                    dt = tz.localize(dt.replace(hour=0, minute=0, second=0))
                else:
                    dt = tz.localize(dt.replace(hour=23, minute=59, second=59))
                return dt.astimezone(pytz.utc).isoformat().replace('+00:00', 'Z')
            try:
                dt = datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
                if dt.tzinfo is None:
                    dt = tz.localize(dt)
                return dt.astimezone(pytz.utc).isoformat().replace('+00:00', 'Z')
            except Exception:
                return dt_str
        # Load penalties from config if available
        penalties = {
            'key_attendee_absence': 100,
            'required_member_absence': 1,
            'key_meeting_absence': 5
        }
        config_path = 'data/config.json'
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                config_json = json.load(f)
            if 'penalties' in config_json:
                penalties.update({k: v for k, v in config_json['penalties'].items() if v is not None})
        # Override with CLI if provided
        if args.penalty_key_attendee_absence is not None:
            penalties['key_attendee_absence'] = args.penalty_key_attendee_absence
        if args.penalty_required_member_absence is not None:
            penalties['required_member_absence'] = args.penalty_required_member_absence
        if args.penalty_key_meeting_absence is not None:
            penalties['key_meeting_absence'] = args.penalty_key_meeting_absence
        tz_name = get_timezone()
        week_start = to_utc_iso(args.week_start, True, tz_name)
        week_end = to_utc_iso(args.week_end, False, tz_name)
        # Fetch data
        meetings = load_json('data/meetings.json')
        # Filter meetings if active_meetings is set
        active_meetings_path = 'data/active_meetings.json'
        if os.path.exists(active_meetings_path):
            with open(active_meetings_path, 'r') as f:
                active_meetings = set(json.load(f))
            meetings = [m for m in meetings if m['name'] in active_meetings]
        members = load_json('data/members.json')
        service = authenticate_google()
        slots = fetch_potential_times_from_calendar(service, week_start, week_end)
        # Always use 60 minutes as the meeting duration
        duration_minutes = 60
        all_possible_slots = []
        slot_index = 0
        for i, window in enumerate(slots):
            window_start = window['start_time']
            window_end = window['end_time']
            possible_slots = generate_possible_slots(window_start, window_end, duration_minutes)
            for slot_start, slot_end in possible_slots:
                all_possible_slots.append({
                    'slot_id': f'slot{slot_index}',
                    'start_time': slot_start,
                    'end_time': slot_end,
                    'location': window.get('location'),
                    'window_id': i  # Track which window/event this slot comes from
                })
                slot_index += 1
        # Build member lookup
        member_lookup = {m['id']: m for m in members}
        # SAT variable pool
        vpool = IDPool()
        var_map = {}
        slot_map = {}
        for meeting in meetings:
            for slot in all_possible_slots:
                var = vpool.id(f"m{meeting['id']}_s{slot['slot_id']}")
                var_map[(meeting['id'], slot['slot_id'])] = var
                slot_map[slot['slot_id']] = slot
        # Fetch member conflicts
        conflicts_by_member = {}
        for member in members:
            conflicts = fetch_member_conflicts(service, member['calendar_id'], week_start, week_end)
            conflicts_by_member[member['id']] = conflicts
        # Build availability matrix for all slots
        slot_availability = {}
        for slot in all_possible_slots:
            slot_id = slot['slot_id']
            slot_start = slot['start_time']
            slot_end = slot['end_time']
            available = []
            for member in members:
                member_id = member['id']
                conflicts = conflicts_by_member.get(member_id, [])
                if not any(overlaps(slot_start, slot_end, c[0], c[1]) for c in conflicts):
                    available.append(member_id)
            slot_availability[slot_id] = available
        # Load key_attendees constraints
        key_attendees_path = 'data/key_attendees.json'
        if os.path.exists(key_attendees_path):
            with open(key_attendees_path, 'r') as f:
                key_attendees = json.load(f)
        else:
            key_attendees = []
        # Filter key_attendees to only those for meetings being scheduled
        meeting_names_set = set(m['name'] for m in meetings)
        key_attendees = [c for c in key_attendees if c['meeting'] in meeting_names_set]
        # Load key_meetings
        key_meetings_path = 'data/key_meetings.json'
        if os.path.exists(key_meetings_path):
            with open(key_meetings_path, 'r') as f:
                key_meetings = set(json.load(f))
        else:
            key_meetings = set()
        # MaxSAT encoding
        wcnf = WCNF()
        # 1. Each meeting is scheduled exactly once (hard)
        for meeting in meetings:
            vars_for_meeting = [var_map[(meeting['id'], slot['slot_id'])] for slot in all_possible_slots]
            if vars_for_meeting:  # Only add constraint if there are possible slots
                cnf = CardEnc.equals(lits=vars_for_meeting, bound=1, vpool=vpool)
                for clause in cnf.clauses:
                    wcnf.append(clause)
            else:
                print(f"Warning: No possible slots found for meeting '{meeting['name']}' - all slots have conflicts")
        # 1b. Key attendees constraints (soft, high penalty): for each, penalize if the member(s) cannot attend the meeting in the chosen slot
        for constraint in key_attendees:
            meeting_name = constraint['meeting']
            members_list = constraint['members']
            meeting_obj = next((m for m in meetings if m['name'] == meeting_name), None)
            if not meeting_obj:
                print(f"Warning: Could not find meeting for key_attendees: {constraint}")
                continue
            meeting_id = meeting_obj['id']
            for member_name in members_list:
                member_obj = next((m for m in members if m['name'] == member_name), None)
                if not member_obj:
                    print(f"Warning: Could not find member for key_attendees: {constraint}")
                    continue
                member_id = member_obj['id']
                for slot in all_possible_slots:
                    slot_id = slot['slot_id']
                    available = slot_availability[slot_id]
                    v = var_map[(meeting_id, slot_id)]
                    if member_id not in available:
                        wcnf.append([-v], weight=penalties['key_attendee_absence'])  # Soft: penalize if this member can't attend this meeting
        # 2. Only one meeting per slot (hard)
        for slot in all_possible_slots:
            slot_id = slot['slot_id']
            meetings_in_slot = [var_map[(meeting['id'], slot_id)] for meeting in meetings]
            if len(meetings_in_slot) > 1:
                cnf = CardEnc.atmost(lits=meetings_in_slot, bound=1, vpool=vpool)
                for clause in cnf.clauses:
                    wcnf.append(clause)
        # 2b. No two meetings in overlapping slots from the same window/event (hard)
        # Group slots by window_id
        slots_by_window = defaultdict(list)
        for slot in all_possible_slots:
            slots_by_window[slot['window_id']].append(slot)
        for window_slots in slots_by_window.values():
            for i, slot1 in enumerate(window_slots):
                for j, slot2 in enumerate(window_slots):
                    if j <= i:
                        continue
                    # If slots overlap
                    if overlaps(slot1['start_time'], slot1['end_time'], slot2['start_time'], slot2['end_time']):
                        for meeting1 in meetings:
                            for meeting2 in meetings:
                                v1 = var_map[(meeting1['id'], slot1['slot_id'])]
                                v2 = var_map[(meeting2['id'], slot2['slot_id'])]
                                if v1 != v2:
                                    wcnf.append([-v1, -v2])
        # 3. Meetings only scheduled in slots where all required members are available (soft)
        for meeting in meetings:
            required_members = meeting['members']
            for slot in all_possible_slots:
                slot_id = slot['slot_id']
                available = slot_availability[slot_id]
                for m in required_members:
                    v = var_map[(meeting['id'], slot_id)]
                    if m not in available:
                        # Soft: penalize if this member can't attend
                        wcnf.append([-v], weight=penalties['required_member_absence'])
        # 3b. Key meetings: penalize by 5 for each member who misses a key meeting
        for meeting in meetings:
            if meeting['name'] in key_meetings:
                required_members = meeting['members']
                for slot in all_possible_slots:
                    slot_id = slot['slot_id']
                    available = slot_availability[slot_id]
                    for m in required_members:
                        v = var_map[(meeting['id'], slot_id)]
                        if m not in available:
                            wcnf.append([-v], weight=penalties['key_meeting_absence'])
        # 4. No double-booking for any member (soft, large penalty)
        # (Removed: no longer penalize double-booking)
        # Check if we have any constraints to solve
        if not wcnf.hard:
            print("No valid scheduling constraints found. This may happen if:")
            print("- All meetings have conflicts in all available time slots")
            print("- No potential meeting times are available")
            print("- No meetings are configured")
            return
        
        # Solve
        with RC2(wcnf) as rc2:
            if rc2.compute():
                model = rc2.model
                true_vars = set(v for v in model if v > 0)
                scheduled = []
                for (meeting_id, slot_id), var in var_map.items():
                    if var in true_vars:
                        meeting = next(m for m in meetings if m['id'] == meeting_id)
                        slot = slot_map[slot_id]
                        member_names = [member_lookup[mid]['name'] for mid in meeting['members']]
                        missing = [member_lookup[mid]['name'] for mid in meeting['members'] if mid not in slot_availability[slot_id]]
                        scheduled.append({'meeting': meeting, 'slot': slot, 'missing': missing})
                # Attendance percentage calculation
                total_assignments = 0
                total_present = 0
                for item in scheduled:
                    meeting = item['meeting']
                    missing = item['missing']
                    total_assignments += len(meeting['members'])
                    total_present += len(meeting['members']) - len(missing)
                if total_assignments > 0:
                    attendance_pct = 100.0 * total_present / total_assignments
                    print(f"\nAttendance percentage: {total_present} / {total_assignments} = {attendance_pct:.2f}%")
                else:
                    print("\nAttendance percentage: N/A (no meetings)")
                # Count conflicts
                key_attendee_absences = 0
                key_meeting_absences = 0
                required_member_absences = 0
                # Build lookup for key_attendees for quick access
                key_attendees_lookup = {}
                for c in key_attendees:
                    key_attendees_lookup.setdefault(c['meeting'], set()).update(c['members'])
                for item in scheduled:
                    meeting = item['meeting']
                    missing = item['missing']
                    meeting_name = meeting['name']
                    required_member_absences += len(missing)
                    for m in missing:
                        # Key attendee absence
                        if meeting_name in key_attendees_lookup and m in key_attendees_lookup[meeting_name]:
                            key_attendee_absences += 1
                        # Key meeting absence
                        if meeting_name in key_meetings:
                            key_meeting_absences += 1
                # Double-bookings
                member_slot_meeting = []
                for item in scheduled:
                    meeting = item['meeting']
                    slot = item['slot']
                    for mid in meeting['members']:
                        if member_lookup[mid]['name'] not in item['missing']:
                            member_slot_meeting.append({'member_id': mid, 'member_name': member_lookup[mid]['name'], 'slot': slot, 'meeting': meeting})
                double_booking_set = set()
                for i, a in enumerate(member_slot_meeting):
                    for j, b in enumerate(member_slot_meeting):
                        if j <= i:
                            continue
                        if a['meeting']['id'] == b['meeting']['id']:
                            continue  # skip same meeting
                        if a['member_id'] == b['member_id']:
                            if overlaps(a['slot']['start_time'], a['slot']['end_time'], b['slot']['start_time'], b['slot']['end_time']):
                                # Use tuple to avoid double-counting
                                double_booking_set.add(tuple(sorted([(a['member_id'], a['slot']['start_time'], a['slot']['end_time'], a['meeting']['id']), (b['member_id'], b['slot']['start_time'], b['slot']['end_time'], b['meeting']['id'])])))
                print("\nConflicts:")
                # Show detailed conflicts for each meeting
                for item in scheduled:
                    meeting = item['meeting']
                    slot = item['slot']
                    missing = item['missing']
                    if missing:
                        print(f"  {meeting['name']}: {', '.join(missing)}")
                # Save schedule to user-specified Google Calendar if requested
                if args.save_calendar:
                    calendar_name = args.save_calendar
                    cal_id = get_or_create_calendar(service, calendar_name)
                    # Build double-booking info for each member/slot
                    double_booked = set()
                    for i, a in enumerate(member_slot_meeting):
                        for j, b in enumerate(member_slot_meeting):
                            if j <= i:
                                continue
                            if a['meeting']['id'] == b['meeting']['id']:
                                continue  # skip same meeting
                            if a['member_id'] == b['member_id']:
                                if overlaps(a['slot']['start_time'], a['slot']['end_time'], b['slot']['start_time'], b['slot']['end_time']):
                                    double_booked.add((a['member_id'], a['slot']['start_time'], a['slot']['end_time']))
                                    double_booked.add((b['member_id'], b['slot']['start_time'], b['slot']['end_time']))
                    for item in scheduled:
                        meeting = item['meeting']
                        slot = item['slot']
                        missing = item['missing']
                        db_members = [member_lookup[mid]['name'] for mid in meeting['members'] if (mid, slot['start_time'], slot['end_time']) in double_booked]
                        description_lines = []
                        if missing:
                            description_lines.append('Missing: ' + ', '.join(missing))
                        if db_members:
                            description_lines.append('Double-booked: ' + ', '.join(db_members))
                        description = '\n'.join(description_lines) if description_lines else None
                        location = slot.get('location')
                        try:
                            create_event(service, cal_id, meeting['name'], slot['start_time'], slot['end_time'], description=description, location=location)
                        except Exception as e:
                            print(f"Failed to create event for {meeting['name']} at {slot['start_time']}: {e}")
            else:
                print("No schedule possible (should not happen unless no slots exist).")
    elif args.command == 'load-config':
        with open(args.config_file, 'r') as f:
            config = yaml.safe_load(f)
        # Members
        members = []
        name_to_id = {}
        for m in config.get('members', []):
            member_id = str(uuid.uuid4())
            members.append({'id': member_id, 'name': m['name'], 'calendar_id': m['calendar_id']})
            name_to_id[m['name']] = member_id
        with open('data/members.json', 'w') as f:
            json.dump(members, f, indent=2)
        # Meetings
        meetings = []
        for mtg in config.get('meetings', []):
            meeting_id = str(uuid.uuid4())
            member_ids = [name_to_id[name] for name in mtg['members']]
            meetings.append({'id': meeting_id, 'name': mtg['name'], 'members': member_ids})
        with open('data/meetings.json', 'w') as f:
            json.dump(meetings, f, indent=2)
        # active_meetings
        if 'active_meetings' in config:
            with open('data/active_meetings.json', 'w') as f:
                json.dump(config['active_meetings'], f, indent=2)
        # Potential times calendar and save calendar
        config_json = {}
        if 'potential_times_calendar_id' in config:
            config_json['potential_times_calendar_id'] = config['potential_times_calendar_id']
        # Save calendar id
        if 'save_calendar_id' in config:
            config_json['save_calendar_id'] = config['save_calendar_id']
        # Key attendees constraints
        key_attendees_path = 'data/key_attendees.json'
        key_attendees = []
        if 'key_attendees' in config:
            for c in config['key_attendees']:
                if 'members' in c:
                    members = c['members']
                elif 'member' in c:
                    members = [c['member']]
                else:
                    continue
                key_attendees.append({'meeting': c['meeting'], 'members': members})
        # Always overwrite key_attendees.json, even if empty
        with open(key_attendees_path, 'w') as f:
            json.dump(key_attendees, f, indent=2)
        # Key meetings
        key_meetings_path = 'data/key_meetings.json'
        if 'key_meetings' in config:
            with open(key_meetings_path, 'w') as f:
                json.dump(config['key_meetings'], f, indent=2)
        with open('data/config.json', 'w') as f:
            json.dump(config_json, f, indent=2)
        print('Configuration loaded successfully.')
    elif args.command == 'add-constraint':
        # Add a fixed constraint to data/constraints.json
        constraints_path = 'data/constraints.json'
        if os.path.exists(constraints_path):
            with open(constraints_path, 'r') as f:
                constraints = json.load(f)
        else:
            constraints = []
        constraints.append({'meeting': args.meeting, 'members': args.members})
        with open(constraints_path, 'w') as f:
            json.dump(constraints, f, indent=2)
        print(f"Added constraint: {args.members} must attend {args.meeting}")
    elif args.command == 'set-active-meetings':
        # Save the list of active meetings to data/active_meetings.json
        os.makedirs('data', exist_ok=True)
        with open('data/active_meetings.json', 'w') as f:
            json.dump(args.meeting_names, f, indent=2)
        print(f"Set active meetings: {', '.join(args.meeting_names)}")
    else:
        parser.print_help()

if __name__ == '__main__':
    main() 