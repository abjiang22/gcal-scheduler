import streamlit as st
import yaml
import os
from calendar_service import authenticate_google
import datetime
import subprocess

CONFIG_PATH = "config.yaml"

# Load config or defaults
if os.path.exists(CONFIG_PATH):
    with open(CONFIG_PATH, "r") as f:
        config = yaml.safe_load(f)
else:
    config = {
        "members": [
            {"name": "Alice", "calendar_id": "alice_calendar_id@group.calendar.google.com"},
            {"name": "Bob", "calendar_id": "bob_calendar_id@group.calendar.google.com"}
        ],
        "meetings": [
            {"name": "Project Kickoff", "members": ["Alice", "Bob"]},
            {"name": "Design Review", "members": ["Bob"]}
        ],
        "penalties": {
            "key_attendee_absence": 100,
            "required_member_absence": 1,
            "key_meeting_absence": 5
        },
        "key_attendees": [],
        "key_meetings": [],
        "active_meetings": [],
        "potential_times_calendar_id": ""
    }

st.title("GCal Scheduler Setup")

st.markdown("""
**Instructions:**
- Use the button below to authenticate with Google (required for calendar access).
- Edit your configuration (members, meetings, penalties, etc.) below.
- Click 'Save Config' to update `config.yaml`.
- To run this UI: `streamlit run ui.py`
""")

# --- Google Auth ---
auth_col1, auth_col2 = st.columns([1, 1])
auth_clicked = auth_col1.button("Authenticate with Google")
reauth_clicked = auth_col2.button("Re-authenticate with Google")
if auth_clicked:
    try:
        authenticate_google()
        st.success("Authentication complete!")
    except Exception as e:
        st.error(f"Authentication failed: {e}")
if reauth_clicked:
    try:
        if os.path.exists('token.pickle'):
            os.remove('token.pickle')
        authenticate_google()
        st.success("Re-authentication complete!")
    except Exception as e:
        st.error(f"Re-authentication failed: {e}")

# --- Potential Meeting Times Calendar ID ---
st.header("Potential Meeting Times Calendar ID")
potential_times_calendar_id = st.text_input("Potential Meeting Times Calendar ID", config.get("potential_times_calendar_id", ""))

# --- Config Editor ---
st.header("Edit Configuration")

# --- Session State for Members and Meetings ---
if "members" not in st.session_state:
    st.session_state["members"] = config.get("members", []).copy()
if "meetings" not in st.session_state:
    st.session_state["meetings"] = config.get("meetings", []).copy()

# --- Members UI ---
st.subheader("Members")
member_cols = st.columns([0.5, 3, 5, 0.7])
member_cols[0].markdown("")
member_cols[1].markdown("**Name**")
member_cols[2].markdown("**Calendar ID**")
member_cols[3].markdown("")
remove_member_idxs = []
for i, member in enumerate(st.session_state["members"]):
    cols = st.columns([0.5, 3, 5, 0.7])
    cols[0].markdown(f"""
        <div style='height: 38px; display: flex; align-items: center; justify-content: flex-end;'>
            {i+1}.
        </div>
        """, unsafe_allow_html=True)
    name = cols[1].text_input("", member["name"], key=f"member_name_{i}")
    cal_id = cols[2].text_input("", member["calendar_id"], key=f"member_calid_{i}")
    if cols[3].button("❌", key=f"remove_member_{i}"):
        remove_member_idxs.append(i)
    st.session_state["members"][i]["name"] = name
    st.session_state["members"][i]["calendar_id"] = cal_id
for idx in reversed(remove_member_idxs):
    st.session_state["members"].pop(idx)
if st.button("Add new name"):
    st.session_state["members"].append({"name": "", "calendar_id": ""})

# --- Meetings UI ---
st.subheader("Meetings")
meeting_remove_idxs = []
member_names = [m["name"] for m in st.session_state["members"] if m["name"]]
meeting_header_cols = st.columns([0.5, 3, 5, 0.7])
meeting_header_cols[0].markdown("")
meeting_header_cols[1].markdown("**Name**")
meeting_header_cols[2].markdown("**Attendees**")
meeting_header_cols[3].markdown("")
for i, meeting in enumerate(st.session_state["meetings"]):
    cols = st.columns([0.5, 3, 5, 0.7])
    cols[0].markdown(f"""
        <div style='height: 38px; display: flex; align-items: center; justify-content: flex-end;'>
            {i+1}.
        </div>
        """, unsafe_allow_html=True)
    mtg_name = cols[1].text_input("", meeting["name"], key=f"meeting_name_{i}")
    attendees = cols[2].multiselect("", member_names, meeting.get("members", []), key=f"meeting_attendees_{i}")
    if cols[3].button("❌", key=f"remove_meeting_{i}"):
        meeting_remove_idxs.append(i)
    st.session_state["meetings"][i]["name"] = mtg_name
    st.session_state["meetings"][i]["members"] = attendees
for idx in reversed(meeting_remove_idxs):
    st.session_state["meetings"].pop(idx)
if st.button("Add new meeting"):
    st.session_state["meetings"].append({"name": "", "members": []})

# --- Key Attendees UI ---
st.subheader("Key Attendees")
if "key_attendees" not in st.session_state:
    st.session_state["key_attendees"] = config.get("key_attendees", []).copy()
key_attendee_remove_idxs = []
meeting_names = [m["name"] for m in st.session_state["meetings"] if m["name"]]
for i, ka in enumerate(st.session_state["key_attendees"]):
    cols = st.columns([4, 6, 1])
    meeting = cols[0].selectbox("Meeting", meeting_names, index=meeting_names.index(ka["meeting"]) if ka.get("meeting") in meeting_names else 0, key=f"ka_meeting_{i}")
    attendees = cols[1].multiselect("Attendees", member_names, ka.get("members", []), key=f"ka_attendees_{i}")
    if cols[2].button("❌", key=f"remove_ka_{i}"):
        key_attendee_remove_idxs.append(i)
    st.session_state["key_attendees"][i]["meeting"] = meeting
    st.session_state["key_attendees"][i]["members"] = attendees
for idx in reversed(key_attendee_remove_idxs):
    st.session_state["key_attendees"].pop(idx)
if st.button("Add new key attendee"):
    st.session_state["key_attendees"].append({"meeting": meeting_names[0] if meeting_names else "", "members": []})

# --- Key Meetings UI ---
st.subheader("Key Meetings")
if "key_meetings" not in st.session_state:
    st.session_state["key_meetings"] = config.get("key_meetings", []).copy()
key_meeting_remove_idxs = []
for i, km in enumerate(st.session_state["key_meetings"]):
    cols = st.columns([10, 1])
    meeting = cols[0].selectbox("Meeting", meeting_names, index=meeting_names.index(km) if km in meeting_names else 0, key=f"km_meeting_{i}")
    if cols[1].button("❌", key=f"remove_km_{i}"):
        key_meeting_remove_idxs.append(i)
    st.session_state["key_meetings"][i] = meeting
for idx in reversed(key_meeting_remove_idxs):
    st.session_state["key_meetings"].pop(idx)
if st.button("Add new key meeting"):
    st.session_state["key_meetings"].append(meeting_names[0] if meeting_names else "")

# --- Active Meetings UI ---
st.subheader("Active Meetings")
if "active_meetings" not in st.session_state:
    st.session_state["active_meetings"] = config.get("active_meetings", []).copy()
st.session_state["active_meetings"] = st.multiselect("Select active meetings", meeting_names, st.session_state["active_meetings"])

# --- Penalties UI at the end ---
st.subheader("Penalties")
if "penalties" not in st.session_state:
    st.session_state["penalties"] = config.get("penalties", {}).copy()
penalty_items = list(st.session_state["penalties"].items())
penalty_cols = st.columns([4, 2, 1])
penalty_cols[0].markdown("**Penalty Name**")
penalty_cols[1].markdown("**Value**")
penalty_cols[2].markdown("")
for i, (pen_name, pen_val) in enumerate(penalty_items):
    cols = st.columns([4, 2, 1])
    cols[0].markdown(f"<div style='height: 38px; display: flex; align-items: center;'>{pen_name}</div>", unsafe_allow_html=True)
    value = cols[1].number_input("", value=pen_val, key=f"penalty_value_{i}")
    penalty_items[i] = (pen_name, value)
st.session_state["penalties"] = {k: v for k, v in penalty_items if k}

if st.button("Save Config"):
    try:
        config["members"] = [m for m in st.session_state["members"] if m["name"] and m["calendar_id"]]
        config["meetings"] = [m for m in st.session_state["meetings"] if m["name"]]
        config["penalties"] = st.session_state["penalties"]
        config["key_attendees"] = [ka for ka in st.session_state["key_attendees"] if ka["meeting"] and ka["members"]]
        config["key_meetings"] = [km for km in st.session_state["key_meetings"] if km]
        config["active_meetings"] = st.session_state["active_meetings"]
        config["potential_times_calendar_id"] = potential_times_calendar_id
        with open(CONFIG_PATH, "w") as f:
            yaml.safe_dump(config, f)
        st.success("Config saved!")
    except Exception as e:
        st.error(f"Error saving config: {e}")

st.header("Run Scheduler")

today = datetime.date.today()
week_start = st.date_input("Week Start", today)
week_end = st.date_input("Week End", today + datetime.timedelta(days=6))

calendar_name = st.text_input("Schedule Calendar Name", "")

if st.button("Run Scheduler"):
    if not calendar_name:
        st.error("Please enter a calendar name.")
    else:
        cmd = [
            "python", "main.py", "schedule-meetings",
            week_start.isoformat(), week_end.isoformat(),
            "--save-calendar", calendar_name
        ]
        with st.spinner("Running scheduler..."):
            try:
                result = subprocess.run(cmd, capture_output=True, text=True, check=True)
                st.success("Scheduler completed!")
                st.text_area("Scheduler Output", result.stdout, height=300)
            except subprocess.CalledProcessError as e:
                st.error("Scheduler failed!")
                st.text_area("Error Output", e.stderr or str(e), height=300) 