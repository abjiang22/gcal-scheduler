# gcal-scheduler

A local Python CLI application to help schedule meetings across a small organization using Google Calendar.

## Features
- Connects to a master Google Calendar account
- Lists all member calendars
- Fetches conflicts for each member
- Allows creation of meetings and assignment of members
- Supports potential meeting times from a dedicated calendar
- Uses MaxSAT solver to find the best possible schedule (minimizing absences and double-bookings)
- Supports fixed constraints (mandate a member must attend a meeting)
- Saves the final schedule to a specified Google Calendar (with location and conflict info)
- All configuration can be done via YAML or CLI

## Setup

1. **Clone the repository**
2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```
3. **Set up Google Calendar API**
   - Go to the [Google Cloud Console](https://console.cloud.google.com/)
   - Create a project and enable the Google Calendar API
   - Create OAuth 2.0 credentials (Desktop app)
   - Download `credentials.json` and place it in the project root
4. **Authenticate**
   ```bash
   python main.py auth
   ```
   - This will open a browser window for you to log in and authorize access. Credentials are saved in `token.pickle` for future use.

## Configuration

### **YAML Example**
```yaml
members:
  - name: Alice
    calendar_id: alice_calendar_id@group.calendar.google.com
  - name: Bob
    calendar_id: bob_calendar_id@group.calendar.google.com

potential_times_calendar_id: org_potential_times@group.calendar.google.com
save_calendar_id: your_calendar_id@group.calendar.google.com

meetings:
  - name: Project Kickoff
    members: [Alice, Bob]
  - name: Design Review
    members: [Bob]

fixed_constraints:
  - meeting: Project Kickoff
    member: Alice
```

### **Load YAML Config**
```bash
python main.py load-config config.yaml
```

### **Manual CLI Configuration**
- Add members, meetings, potential times, and constraints using CLI commands (see below).
- Set the potential times calendar:
  ```bash
  python main.py set-potential-times-calendar <CALENDAR_ID>
  ```
- Set the save calendar:
  ```bash
  python main.py set-save-calendar <CALENDAR_ID>
  ```
- Add a fixed constraint:
  ```bash
  python main.py add-constraint "Meeting Name" "Member Name"
  ```

## Scheduling Meetings

1. **List your calendars to get IDs:**
   ```bash
   python main.py list-calendars
   ```
2. **Run the scheduler:**
   ```bash
   python main.py schedule-meetings <WEEK_START> <WEEK_END> [--save-calendar [CALENDAR_ID]]
   ```
   - If you use `--save-calendar` with no value, it uses the value from your config.
   - If you use `--save-calendar <CALENDAR_ID>`, it saves to that calendar.
   - If you omit the flag, the schedule is only printed.

3. **Check your Google Calendar for the scheduled events.**

## Authentication Troubleshooting
- Credentials are saved in `token.pickle` after first authentication.
- If you ever need to re-authenticate (e.g., after deleting `token.pickle` or changing Google account permissions), just run:
  ```bash
  python main.py auth
  ```

## Advanced Features
- **Fixed constraints:** Mandate that a specific member must attend a specific meeting (via YAML or CLI).
- **Location support:** If a potential meeting time has a location, it is preserved in the scheduled event.
- **Conflict reporting:** The schedule output lists all absences and double-bookings.

## Example CLI Commands
```bash
python main.py add-member "Alice" alice_calendar_id@group.calendar.google.com
python main.py add-meeting "Project Kickoff" <MEMBER_ID_1> <MEMBER_ID_2>
python main.py set-potential-times-calendar <CALENDAR_ID>
python main.py set-save-calendar <CALENDAR_ID>
python main.py add-constraint "Project Kickoff" "Alice"
python main.py schedule-meetings 2025-07-02 2025-07-05 --save-calendar
```

## Notes
- All meetings are assumed to be 1 hour long.
- The tool is designed for small to medium organizations (tens of meetings/people per week).

---
If you have questions or want to extend the tool, see the code comments or open an issue!