import json
import argparse
from calendar_service import authenticate_google, list_calendars, list_events, get_or_create_calendar, create_event
from models import Member, Meeting
from utils import add_member, list_members, remove_member, add_meeting, list_meetings, remove_meeting, add_potential_time, list_potential_times, remove_potential_time, set_potential_times_calendar, get_potential_times_calendar, fetch_potential_times_from_calendar, set_timezone, get_timezone, load_json, generate_possible_slots, fetch_member_conflicts, overlaps
import re
from datetime import datetime
import pytz
from pysat.formula import IDPool
from pysat.solvers import Glucose3
from pysat.examples.rc2 import RC2
from pysat.formula import WCNF
from pysat.card import CardEnc
import yaml
import uuid
import os

def main():
    parser = argparse.ArgumentParser(description='gcal-scheduler CLI')
    subparsers = parser.add_subparsers(dest='command')

    # Google Calendar commands
    parser_auth = subparsers.add_parser('auth', help='Authenticate with Google Calendar')
    parser_list_cal = subparsers.add_parser('list-calendars', help='List all calendars')
    parser_list_events = subparsers.add_parser('list-events', help='List events for a calendar')
    parser_list_events.add_argument('calendar_id', type=str, help='Calendar ID')

    # Member management
    parser_add_member = subparsers.add_parser('add-member', help='Add a member')
    parser_add_member.add_argument('name', type=str, help='Member name')
    parser_add_member.add_argument('calendar_id', type=str, help='Google Calendar ID')
    parser_list_members = subparsers.add_parser('list-members', help='List all members')
    parser_remove_member = subparsers.add_parser('remove-member', help='Remove a member')
    parser_remove_member.add_argument('member_id', type=str, help='Member ID')

    # Meeting management
    parser_add_meeting = subparsers.add_parser('add-meeting', help='Add a meeting')
    parser_add_meeting.add_argument('name', type=str, help='Meeting name')
    parser_add_meeting.add_argument('member_ids', nargs='+', help='Member IDs')
    parser_add_meeting.add_argument('--duration', type=int, default=60, help='Duration in minutes')
    parser_list_meetings = subparsers.add_parser('list-meetings', help='List all meetings')
    parser_remove_meeting = subparsers.add_parser('remove-meeting', help='Remove a meeting')
    parser_remove_meeting.add_argument('meeting_id', type=str, help='Meeting ID')

    # Potential meeting time management
    parser_add_time = subparsers.add_parser('add-potential-time', help='Add a potential meeting time')
    parser_add_time.add_argument('start_time', type=str, help='Start time (ISO format)')
    parser_add_time.add_argument('end_time', type=str, help='End time (ISO format)')
    parser_list_times = subparsers.add_parser('list-potential-times', help='List all potential meeting times')
    parser_remove_time = subparsers.add_parser('remove-potential-time', help='Remove a potential meeting time')
    parser_remove_time.add_argument('time_id', type=str, help='Potential time ID')

    # Potential meeting times calendar management
    parser_set_cal = subparsers.add_parser('set-potential-times-calendar', help='Set the potential meeting times calendar ID')
    parser_set_cal.add_argument('calendar_id', type=str, help='Calendar ID')
    parser_show_cal = subparsers.add_parser('show-potential-times-calendar', help='Show the current potential meeting times calendar ID')
    parser_fetch_times = subparsers.add_parser('fetch-potential-times', help='Fetch and list potential meeting times from the calendar for a given week')
    parser_fetch_times.add_argument('week_start', type=str, help='Week start (ISO format)')
    parser_fetch_times.add_argument('week_end', type=str, help='Week end (ISO format)')

    # Timezone management
    parser_set_tz = subparsers.add_parser('set-timezone', help='Set the default timezone (e.g., America/New_York)')
    parser_set_tz.add_argument('timezone', type=str, help='Timezone name')
    parser_show_tz = subparsers.add_parser('show-timezone', help='Show the current default timezone')

    # New command
    parser_schedule = subparsers.add_parser('schedule-meetings', help='Schedule meetings for the given week')
    parser_schedule.add_argument('week_start', type=str, help='Week start (YYYY-MM-DD or ISO)')
    parser_schedule.add_argument('week_end', type=str, help='Week end (YYYY-MM-DD or ISO)')
    parser_schedule.add_argument('--save-calendar', nargs='?', const=True, help='Calendar ID to save the meeting schedule to (if no value, use config)')

    # Load config command
    parser_load_config = subparsers.add_parser('load-config', help='Load members, meetings, and potential times calendar from a YAML config file')
    parser_load_config.add_argument('config_file', type=str, help='YAML config file path')

    # New command
    parser_set_save_cal = subparsers.add_parser('set-save-calendar', help='Set the save calendar ID for scheduled meetings')
    parser_set_save_cal.add_argument('calendar_id', type=str, help='Calendar ID')

    # New command
    parser_add_constraint = subparsers.add_parser('add-constraint', help='Add a fixed constraint that mandates a member must attend a meeting')
    parser_add_constraint.add_argument('meeting', type=str, help='Meeting name')
    parser_add_constraint.add_argument('member', type=str, help='Member name')

    args = parser.parse_args()

    if args.command in ['auth', 'list-calendars', 'list-events']:
        service = authenticate_google()
        if args.command == 'list-calendars':
            list_calendars(service)
        elif args.command == 'list-events':
            list_events(service, args.calendar_id)
        else:
            print('Authenticated with Google Calendar.')
    elif args.command == 'add-member':
        add_member(args.name, args.calendar_id)
    elif args.command == 'list-members':
        list_members()
    elif args.command == 'remove-member':
        remove_member(args.member_id)
    elif args.command == 'add-meeting':
        add_meeting(args.name, args.member_ids, args.duration)
    elif args.command == 'list-meetings':
        list_meetings()
    elif args.command == 'remove-meeting':
        remove_meeting(args.meeting_id)
    elif args.command == 'add-potential-time':
        add_potential_time(args.start_time, args.end_time)
    elif args.command == 'list-potential-times':
        list_potential_times()
    elif args.command == 'remove-potential-time':
        remove_potential_time(args.time_id)
    elif args.command == 'set-potential-times-calendar':
        set_potential_times_calendar(args.calendar_id)
    elif args.command == 'show-potential-times-calendar':
        cal_id = get_potential_times_calendar()
        if cal_id:
            print(f"Potential meeting times calendar ID: {cal_id}")
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
        tz_name = get_timezone()
        week_start = to_utc_iso(args.week_start, True, tz_name)
        week_end = to_utc_iso(args.week_end, False, tz_name)
        # Fetch data
        meetings = load_json('data/meetings.json')
        members = load_json('data/members.json')
        service = authenticate_google()
        slots = fetch_potential_times_from_calendar(service, week_start, week_end)
        # Always use 60 minutes as the meeting duration
        duration_minutes = 60
        print("\nPossible meeting slots (on the hour and half-hour) for each window:")
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
                    'location': window.get('location')  # propagate location
                })
                slot_index += 1
        print(f"Total possible slots: {len(all_possible_slots)}")
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
        # Load fixed constraints
        constraints_path = 'data/constraints.json'
        if os.path.exists(constraints_path):
            with open(constraints_path, 'r') as f:
                fixed_constraints = json.load(f)
        else:
            fixed_constraints = []
        # MaxSAT encoding
        wcnf = WCNF()
        # 1. Each meeting is scheduled exactly once (hard)
        for meeting in meetings:
            vars_for_meeting = [var_map[(meeting['id'], slot['slot_id'])] for slot in all_possible_slots]
            cnf = CardEnc.equals(lits=vars_for_meeting, bound=1, vpool=vpool)
            for clause in cnf.clauses:
                wcnf.append(clause)
        # 1b. Fixed constraints (hard): for each, require the member to be available for the meeting in the chosen slot
        for constraint in fixed_constraints:
            meeting_name = constraint['meeting']
            member_name = constraint['member']
            # Find meeting and member IDs
            meeting_obj = next((m for m in meetings if m['name'] == meeting_name), None)
            member_obj = next((m for m in members if m['name'] == member_name), None)
            if not meeting_obj or not member_obj:
                print(f"Warning: Could not find meeting/member for constraint: {constraint}")
                continue
            meeting_id = meeting_obj['id']
            member_id = member_obj['id']
            # For all slots, only allow scheduling if member is available
            for slot in all_possible_slots:
                slot_id = slot['slot_id']
                available = slot_availability[slot_id]
                v = var_map[(meeting_id, slot_id)]
                if member_id not in available:
                    wcnf.append([-v])  # Hard: cannot schedule meeting in this slot if member is not available
        # 2. Only one meeting per slot (hard)
        for slot in all_possible_slots:
            slot_id = slot['slot_id']
            meetings_in_slot = [var_map[(meeting['id'], slot_id)] for meeting in meetings]
            if len(meetings_in_slot) > 1:
                cnf = CardEnc.atmost(lits=meetings_in_slot, bound=1, vpool=vpool)
                for clause in cnf.clauses:
                    wcnf.append(clause)
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
                        wcnf.append([-v], weight=1)
        # 4. No double-booking for any member (soft, large penalty)
        for i, slot1 in enumerate(all_possible_slots):
            slot1_start = slot1['start_time']
            slot1_end = slot1['end_time']
            for j, slot2 in enumerate(all_possible_slots):
                if j <= i:
                    continue
                slot2_start = slot2['start_time']
                slot2_end = slot2['end_time']
                # If slots overlap
                if overlaps(slot1_start, slot1_end, slot2_start, slot2_end):
                    for member in members:
                        member_id = member['id']
                        for meeting1 in meetings:
                            if member_id in meeting1['members']:
                                for meeting2 in meetings:
                                    if meeting2['id'] == meeting1['id']:
                                        continue
                                    if member_id in meeting2['members']:
                                        v1 = var_map[(meeting1['id'], slot1['slot_id'])]
                                        v2 = var_map[(meeting2['id'], slot2['slot_id'])]
                                        # Soft: penalize double-booking
                                        wcnf.append([-v1, -v2], weight=100)
        # Solve
        print("Solving with MaxSAT...")
        with RC2(wcnf) as rc2:
            if rc2.compute():
                model = rc2.model
                true_vars = set(v for v in model if v > 0)
                print(f"\nBest possible schedule (may have some violations). Total penalty: {rc2.cost}")
                scheduled = []
                for (meeting_id, slot_id), var in var_map.items():
                    if var in true_vars:
                        meeting = next(m for m in meetings if m['id'] == meeting_id)
                        slot = slot_map[slot_id]
                        member_names = [member_lookup[mid]['name'] for mid in meeting['members']]
                        missing = [member_lookup[mid]['name'] for mid in meeting['members'] if mid not in slot_availability[slot_id]]
                        print(f"Meeting '{meeting['name']}' scheduled at {slot['start_time']} to {slot['end_time']} for members: {', '.join(member_names)}" + (f" (Missing: {', '.join(missing)})" if missing else ""))
                        scheduled.append({'meeting': meeting, 'slot': slot, 'missing': missing})
                # Display conflicts
                print("\nConflicts:")
                # 1. Member absences
                for item in scheduled:
                    meeting = item['meeting']
                    slot = item['slot']
                    for m in item['missing']:
                        print(f"{m} can't attend {meeting['name']} ({slot['start_time']} to {slot['end_time']})")
                # 2. Double-bookings
                # Build a list of (member, slot, meeting)
                member_slot_meeting = []
                for item in scheduled:
                    meeting = item['meeting']
                    slot = item['slot']
                    for mid in meeting['members']:
                        if member_lookup[mid]['name'] not in item['missing']:
                            member_slot_meeting.append({'member_id': mid, 'member_name': member_lookup[mid]['name'], 'slot': slot, 'meeting': meeting})
                # Check for double-bookings
                for i, a in enumerate(member_slot_meeting):
                    for j, b in enumerate(member_slot_meeting):
                        if j <= i:
                            continue
                        if a['member_id'] == b['member_id']:
                            if overlaps(a['slot']['start_time'], a['slot']['end_time'], b['slot']['start_time'], b['slot']['end_time']):
                                print(f"{a['member_name']} is double-booked: {a['meeting']['name']} and {b['meeting']['name']} overlap at {a['slot']['start_time']} to {a['slot']['end_time']}")
                # Save schedule to user-specified Google Calendar if requested
                cal_id = args.save_calendar
                if cal_id is True:
                    # --save-calendar was provided with no value, use config
                    try:
                        with open('data/config.json', 'r') as f:
                            config_data = json.load(f)
                            cal_id = config_data.get('save_calendar_id')
                    except Exception as e:
                        cal_id = None
                if cal_id and cal_id is not True:
                    print(f"\nSaving schedule to calendar: {cal_id} ...")
                    # Build double-booking info for each member/slot
                    double_booked = set()
                    for i, a in enumerate(member_slot_meeting):
                        for j, b in enumerate(member_slot_meeting):
                            if j <= i:
                                continue
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
                    print(f"Schedule saved to calendar: {cal_id}")
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
        # Potential times calendar and save calendar
        config_json = {}
        if 'potential_times_calendar_id' in config:
            config_json['potential_times_calendar_id'] = config['potential_times_calendar_id']
        # Save calendar id
        if 'save_calendar_id' in config:
            config_json['save_calendar_id'] = config['save_calendar_id']
        # Fixed constraints
        if 'fixed_constraints' in config:
            with open('data/constraints.json', 'w') as f:
                json.dump(config['fixed_constraints'], f, indent=2)
        with open('data/config.json', 'w') as f:
            json.dump(config_json, f, indent=2)
        print('Configuration loaded successfully.')
    elif args.command == 'set-save-calendar':
        # Set or update save_calendar_id in config.json
        config_path = 'data/config.json'
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                config = json.load(f)
        else:
            config = {}
        config['save_calendar_id'] = args.calendar_id
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)
        print(f"Set save calendar ID: {args.calendar_id}")
    elif args.command == 'add-constraint':
        # Add a fixed constraint to data/constraints.json
        constraints_path = 'data/constraints.json'
        if os.path.exists(constraints_path):
            with open(constraints_path, 'r') as f:
                constraints = json.load(f)
        else:
            constraints = []
        constraints.append({'meeting': args.meeting, 'member': args.member})
        with open(constraints_path, 'w') as f:
            json.dump(constraints, f, indent=2)
        print(f"Added constraint: {args.member} must attend {args.meeting}")
    else:
        parser.print_help()

if __name__ == '__main__':
    main() 