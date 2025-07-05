# G-Cal Meeting Scheduler

A powerful Python application that intelligently schedules meetings across your organization using Google Calendar integration and advanced constraint solving.

## 🚀 Features

- **Smart Scheduling**: Uses MaxSAT solver to find optimal meeting schedules while minimizing conflicts
- **Google Calendar Integration**: Seamless connection to Google Calendar API for real-time availability
- **Conflict Resolution**: Automatically detects and reports scheduling conflicts
- **Flexible Configuration**: Support for YAML configuration files and command-line interface
- **Web UI**: Modern Streamlit-based interface for easy configuration and scheduling
- **Advanced Constraints**: Support for key attendees, required members, and priority meetings
- **Location Support**: Preserves meeting locations from potential time slots
- **Calendar Export**: Creates new Google Calendars with scheduled meetings and conflict information

## 📋 Table of Contents

- [Quick Start](#quick-start)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [Web Interface](#web-interface)
- [Advanced Features](#advanced-features)
- [Troubleshooting](#troubleshooting)
- [API Reference](#api-reference)

## 🏃‍♂️ Quick Start

1. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Set up Google Calendar API**:
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Create a project and enable Google Calendar API
   - Create OAuth 2.0 credentials (Desktop app)
   - Download `credentials.json` to project root

3. **Authenticate**:
   ```bash
   python main.py auth
   ```

4. **Configure your organization** (see [Configuration](#configuration) section)

5. **Run the scheduler**:
   ```bash
   python main.py schedule-meetings 2024-11-21 2024-11-24 --save-calendar "Weekly Schedule"
   ```

## 📦 Installation

### Prerequisites

- Python 3.7 or higher
- Google Calendar API access
- Internet connection for Google Calendar integration

### Dependencies

```bash
pip install -r requirements.txt
```

**Key Dependencies:**
- `google-api-python-client`: Google Calendar API integration
- `pysat`: MaxSAT constraint solver
- `streamlit`: Web interface
- `pyyaml`: YAML configuration support
- `python-dateutil`: Date parsing and manipulation

## ⚙️ Configuration

### YAML Configuration (Recommended)

Create a `config.yaml` file in your project root:

```yaml
# Organization Members
members:
  - name: Alice Johnson
    calendar_id: alice.johnson@company.com
  - name: Bob Smith
    calendar_id: bob.smith@company.com
  - name: Carol Davis
    calendar_id: carol.davis@company.com

# Potential Meeting Times Calendar
potential_times_calendar_id: potential-meetings@company.com

# Meetings to Schedule
meetings:
  - name: Weekly Standup
    members: [Alice Johnson, Bob Smith, Carol Davis]
  - name: Project Review
    members: [Alice Johnson, Bob Smith]
  - name: Design Discussion
    members: [Bob Smith, Carol Davis]

# Key Attendees (Strongly preferred but not required)
key_attendees:
  - meeting: Weekly Standup
    members: [Alice Johnson]
  - meeting: Project Review
    members: [Bob Smith]

# Priority Meetings (Higher penalty for absences)
key_meetings:
  - Weekly Standup
  - Project Review

# Active Meetings (Only these will be scheduled)
active_meetings:
  - Weekly Standup
  - Project Review

# Penalty Configuration
penalties:
  key_attendee_absence: 100    # High penalty for key attendee missing
  required_member_absence: 1   # Standard penalty for any member missing
  key_meeting_absence: 5       # Penalty for missing priority meetings
```

### Load Configuration

```bash
python main.py load-config config.yaml
```

## 🎯 Usage

### Command Line Interface

#### List Available Calendars
```bash
python main.py list-calendars
```

#### Schedule Meetings
```bash
# Basic scheduling
python main.py schedule-meetings 2024-01-15 2024-01-19

# Save to new Google Calendar
python main.py schedule-meetings 2024-01-15 2024-01-19 --save-calendar "Weekly Schedule"

# Custom penalties
python main.py schedule-meetings 2024-01-15 2024-01-19 \
  --save-calendar "Weekly Schedule" \
  --penalty-key-attendee-absence 100 \
  --penalty-required-member-absence 1 \
  --penalty-key-meeting-absence 5
```

#### Manage Members
```bash
# Add member
python main.py add-member "Alice Johnson" alice.johnson@company.com

# List members
python main.py list-members
```

#### Manage Meetings
```bash
# Add meeting
python main.py add-meeting "Weekly Standup" <MEMBER_ID_1> <MEMBER_ID_2>

# List meetings
python main.py list-meetings
```

#### Set Constraints
```bash
# Set potential times calendar
python main.py set-potential-times-calendar <CALENDAR_ID>

# Add fixed constraint (member must attend meeting)
python main.py add-constraint "Weekly Standup" "Alice Johnson"

# Set active meetings
python main.py set-active-meetings "Weekly Standup" "Project Review"
```

### Web Interface

For a more user-friendly experience, use the Streamlit web interface:

```bash
streamlit run ui.py
```

**Features of the Web Interface:**
- Visual configuration editor
- Real-time validation
- Google Calendar authentication
- Interactive scheduling
- Conflict visualization
- Success notifications

## 🌟 Advanced Features

### Key Attendees
Specify essential meeting participants. The scheduler will strongly prefer their attendance but won't fail if they're unavailable.

```yaml
key_attendees:
  - meeting: Weekly Standup
    members: [Alice Johnson, Bob Smith]
```

### Priority Meetings
Mark certain meetings as high-priority. Missing these meetings incurs higher penalties.

```yaml
key_meetings:
  - Weekly Standup
  - Project Review
```

### Conflict Resolution
The scheduler automatically:
- Detects double-bookings
- Reports member absences
- Provides attendance percentages
- Creates detailed conflict reports

### Location Support
Meeting locations from potential time slots are preserved in the final schedule.

### No Overlapping Meetings
Within the same potential time window, no two meetings can be scheduled in overlapping slots. This ensures realistic scheduling constraints.

## 🔧 Troubleshooting

### Authentication Issues

**Problem**: "Authentication failed" or "Invalid credentials"

**Solutions**:
1. Delete `token.pickle` and re-authenticate:
   ```bash
   rm token.pickle
   python main.py auth
   ```

2. Verify `credentials.json` is in the project root
3. Check Google Cloud Console API permissions

### Configuration Issues

**Problem**: "No members/meetings found"

**Solutions**:
1. Ensure `config.yaml` is properly formatted
2. Run `python main.py load-config config.yaml`
3. Check member calendar IDs are valid

### Scheduling Issues

**Problem**: "No schedule possible"

**Solutions**:
1. Verify potential times calendar has events
2. Check member calendar IDs are accessible
3. Ensure date range is valid
4. Review penalty configuration

### Common Error Messages

| Error | Solution |
|-------|----------|
| `FileNotFoundError: credentials.json` | Download credentials from Google Cloud Console |
| `No valid scheduling constraints found` | Check potential times calendar and member availability |
| `Authentication failed` | Re-authenticate with `python main.py auth` |

## 📚 API Reference

### Main Commands

| Command | Description | Example |
|---------|-------------|---------|
| `auth` | Authenticate with Google Calendar | `python main.py auth` |
| `list-calendars` | List available calendars | `python main.py list-calendars` |
| `schedule-meetings` | Schedule meetings for date range | `python main.py schedule-meetings 2024-01-15 2024-01-19` |
| `load-config` | Load configuration from YAML | `python main.py load-config config.yaml` |
| `add-member` | Add organization member | `python main.py add-member "Alice" alice@company.com` |
| `add-meeting` | Add meeting definition | `python main.py add-meeting "Standup" <MEMBER_IDS>` |

### Configuration Options

| Option | Type | Description | Default |
|--------|------|-------------|---------|
| `--save-calendar` | string | Calendar name for saving schedule | None |
| `--penalty-key-attendee-absence` | int | Penalty for key attendee missing | 100 |
| `--penalty-required-member-absence` | int | Penalty for any member missing | 1 |
| `--penalty-key-meeting-absence` | int | Penalty for missing priority meeting | 5 |

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 🆘 Support

For issues and questions:
1. Check the [Troubleshooting](#troubleshooting) section
2. Review the [Configuration](#configuration) examples
3. Open an issue on GitHub

---

**Happy Scheduling! 🎉**