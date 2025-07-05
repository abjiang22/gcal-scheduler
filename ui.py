import streamlit as st
import yaml
import os
from calendar_service import authenticate_google
import datetime
import subprocess
import pandas as pd
from streamlit import column_config

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

# Initialize session state
if "unsaved_changes" not in st.session_state:
    st.session_state["unsaved_changes"] = {
        "members": False, "meetings": False, "key_attendees": False,
        "key_meetings": False, "active_meetings": False, "penalties": False, "calendar_id": False
    }

# Always update original_values to match current config
st.session_state["original_values"] = {
    "members": config.get("members", []).copy(),
    "meetings": config.get("meetings", []).copy(),
    "key_attendees": config.get("key_attendees", []).copy(),
    "key_meetings": config.get("key_meetings", []).copy(),
    "active_meetings": config.get("active_meetings", []).copy(),
    "penalties": config.get("penalties", {}).copy(),
    "calendar_id": config.get("potential_times_calendar_id", "")
}

st.title("G-Cal Meeting Scheduler")

st.markdown("""
**Instructions:**
- Use the button below to authenticate with Google (required for calendar access).
- Edit your configuration (members, meetings, penalties, etc.) below.
- Click the save button for each section to update `config.yaml`.
- To run this UI: `streamlit run ui.py`
""")

# CSS for spacing
st.markdown('''
<style>
.block-container > div { margin-bottom: 0.5rem; }
.key-attendees-row { margin-bottom: 0.2rem !important; padding-bottom: 0 !important; }
</style>
''', unsafe_allow_html=True)

# Google Auth
auth_col1, auth_col2 = st.columns([1, 1])
if auth_col1.button("Authenticate with Google"):
    try:
        authenticate_google()
        st.success("Authentication complete!")
    except Exception as e:
        st.error(f"Authentication failed: {e}")

if auth_col2.button("Re-authenticate with Google"):
    try:
        if os.path.exists('token.pickle'):
            os.remove('token.pickle')
        authenticate_google()
        st.success("Re-authentication complete!")
    except Exception as e:
        st.error(f"Re-authentication failed: {e}")

# Calendar ID
st.header("Potential Meeting Times Calendar ID")
potential_times_calendar_id = st.text_input("Potential Meeting Times Calendar ID", config.get("potential_times_calendar_id", ""))

if potential_times_calendar_id != st.session_state["original_values"]["calendar_id"]:
    st.session_state["unsaved_changes"]["calendar_id"] = True
    st.warning("⚠️ You have unsaved changes in Calendar ID")
else:
    st.session_state["unsaved_changes"]["calendar_id"] = False

if st.button("💾 Save Calendar ID", key="save_calendar_id"):
    try:
        config["potential_times_calendar_id"] = potential_times_calendar_id
        with open(CONFIG_PATH, "w") as f:
            yaml.safe_dump(config, f)
        st.session_state["original_values"]["calendar_id"] = potential_times_calendar_id
        st.session_state["unsaved_changes"]["calendar_id"] = False
        st.success("Calendar ID saved!")
    except Exception as e:
        st.error(f"Error saving calendar ID: {e}")

# Config Editor
st.header("Edit Configuration")

# Members
st.subheader("Members")
with st.expander("Member Details", expanded=True):
    if "members" not in st.session_state:
        st.session_state["members"] = config.get("members", []).copy()

    # Initialize members change tracking
    if "members_changed" not in st.session_state:
        st.session_state["members_changed"] = False

    members_df = pd.DataFrame(st.session_state["members"])
    edited_members = st.data_editor(
        members_df,
        num_rows="dynamic",
        use_container_width=True,
        hide_index=True,
        column_config={
            "name": st.column_config.TextColumn("Name", width="medium"),
            "calendar_id": st.column_config.TextColumn("Calendar ID", width="large")
        },
        column_order=["name", "calendar_id"],
        key="edited_members_df"
    )

    # Always update session state with the returned data
    if edited_members is not None:
        new_members_data = edited_members.to_dict("records")
        if new_members_data != st.session_state["members"]:
            st.session_state["members"] = new_members_data
            st.session_state["members_changed"] = True

    current_members = [m for m in st.session_state["members"] if m["name"] and m["calendar_id"]]
    if current_members != st.session_state["original_values"]["members"]:
        st.session_state["unsaved_changes"]["members"] = True
        st.warning("⚠️ You have unsaved changes in Members")
    else:
        st.session_state["unsaved_changes"]["members"] = False

    if st.button("💾 Save Members", key="save_members"):
        try:
            # Handle cascading updates when member names change
            for old_member in st.session_state["original_values"]["members"]:
                old_name = old_member["name"]
                for new_member in current_members:
                    if new_member.get("calendar_id") == old_member.get("calendar_id"):
                        new_name = new_member["name"]
                        if old_name != new_name:
                            # Update all references to this member name in the config
                            for meeting in config.get("meetings", []):
                                if old_name in meeting.get("members", []):
                                    meeting["members"] = [new_name if m == old_name else m for m in meeting["members"]]
                            for ka in config.get("key_attendees", []):
                                if old_name in ka.get("members", []):
                                    ka["members"] = [new_name if m == old_name else m for m in ka["members"]]
                            break
            
            config["members"] = current_members
            with open(CONFIG_PATH, "w") as f:
                yaml.safe_dump(config, f)
            
            # Reload config and update session state
            with open(CONFIG_PATH, "r") as f:
                updated_config = yaml.safe_load(f)
                if updated_config is None:
                    updated_config = {}
            
            st.session_state["original_values"]["members"] = current_members.copy()
            st.session_state["original_values"]["meetings"] = updated_config.get("meetings", []).copy()
            st.session_state["original_values"]["key_attendees"] = updated_config.get("key_attendees", []).copy()
            st.session_state["original_values"]["key_meetings"] = updated_config.get("key_meetings", []).copy()
            st.session_state["original_values"]["active_meetings"] = updated_config.get("active_meetings", []).copy()
            
            st.session_state["meetings"] = updated_config.get("meetings", []).copy()
            st.session_state["key_attendees"] = updated_config.get("key_attendees", []).copy()
            st.session_state["key_meetings"] = updated_config.get("key_meetings", []).copy()
            st.session_state["active_meetings"] = updated_config.get("active_meetings", []).copy()
            
            st.session_state["unsaved_changes"]["members"] = False
            st.success("Members saved!")
        except Exception as e:
            st.error(f"Error saving members: {e}")

# Meetings
st.subheader("Meetings")
with st.expander("Meeting Details", expanded=True):
    if "meetings" not in st.session_state:
        st.session_state["meetings"] = config.get("meetings", []).copy()

    if "meeting_remove_idxs" not in st.session_state:
        st.session_state["meeting_remove_idxs"] = []

    member_names = [m["name"] for m in config.get("members", []) if m["name"]]

    # Table header
    meeting_header_cols = st.columns([4, 7, 1])
    meeting_header_cols[0].markdown("<div style='margin-bottom:-18px'><b>Meeting Name</b></div>", unsafe_allow_html=True)
    meeting_header_cols[1].markdown("<div style='margin-bottom:-18px'><b>Attendees</b></div>", unsafe_allow_html=True)

    # Process meetings
    for i, meeting in enumerate(st.session_state["meetings"]):
        cols = st.columns([4, 7, 1])
        
        name_key = f"meeting_name_{i}"
        attendees_key = f"meeting_attendees_{i}"
        remove_key = f"remove_meeting_{i}"
        
        mtg_name = cols[0].text_input("", meeting["name"], key=name_key)
        saved_member_names = [m["name"] for m in config.get("members", []) if m["name"]]
        attendees = cols[1].multiselect("", saved_member_names, meeting.get("members", []), key=attendees_key)
        
        cols[2].markdown("<div style='height: 27px'></div>", unsafe_allow_html=True)
        if cols[2].button("❌", key=remove_key):
            st.session_state["meeting_remove_idxs"].append(i)
        
        # Update session state immediately
        if st.session_state["meetings"][i]["name"] != mtg_name:
            st.session_state["meetings"][i]["name"] = mtg_name
            st.rerun()
        if st.session_state["meetings"][i].get("members") != attendees:
            st.session_state["meetings"][i]["members"] = attendees
            st.rerun()

    # Remove meetings marked for deletion
    for idx in reversed(st.session_state["meeting_remove_idxs"]):
        if idx < len(st.session_state["meetings"]):
            st.session_state["meetings"].pop(idx)
    st.session_state["meeting_remove_idxs"] = []

    if st.button("Add new meeting", key="add_meeting"):
        st.session_state["meetings"].append({"name": "", "members": []})
        st.rerun()

    # Check for changes in meetings - compare against actual config file data
    current_meetings = [m for m in st.session_state["meetings"] if m["name"]]
    if current_meetings != config.get("meetings", []):
        st.session_state["unsaved_changes"]["meetings"] = True
        st.warning("⚠️ You have unsaved changes in Meetings")
    else:
        st.session_state["unsaved_changes"]["meetings"] = False

    if st.button("💾 Save Meetings", key="save_meetings"):
        try:
            # Handle cascading updates when meeting names change
            for old_meeting in st.session_state["original_values"]["meetings"]:
                old_name = old_meeting["name"]
                old_members = set(old_meeting.get("members", []))
                
                for new_meeting in st.session_state["meetings"]:
                    new_name = new_meeting.get("name")
                    new_members = set(new_meeting.get("members", []))
                    
                    # Match by members (using sets to ignore order)
                    if new_name and old_members == new_members:
                        if old_name != new_name:
                            # Update all references to this meeting name in the config
                            for ka in config.get("key_attendees", []):
                                if ka.get("meeting") == old_name:
                                    ka["meeting"] = new_name
                            
                            # Update key_meetings list - replace old_name with new_name
                            if "key_meetings" not in config:
                                config["key_meetings"] = []
                            if old_name in config["key_meetings"]:
                                config["key_meetings"] = [new_name if m == old_name else m for m in config["key_meetings"]]
                            
                            # Update active_meetings list - replace old_name with new_name
                            if "active_meetings" not in config:
                                config["active_meetings"] = []
                            if old_name in config["active_meetings"]:
                                config["active_meetings"] = [new_name if m == old_name else m for m in config["active_meetings"]]
                            break
            
            config["meetings"] = [m for m in st.session_state["meetings"] if m["name"]]
            with open(CONFIG_PATH, "w") as f:
                yaml.safe_dump(config, f)
            
            # Reload config and update session state
            with open(CONFIG_PATH, "r") as f:
                updated_config = yaml.safe_load(f)
                if updated_config is None:
                    updated_config = {}
            
            st.session_state["original_values"]["meetings"] = config["meetings"].copy()
            st.session_state["original_values"]["key_attendees"] = updated_config.get("key_attendees", []).copy()
            st.session_state["original_values"]["key_meetings"] = updated_config.get("key_meetings", []).copy()
            st.session_state["original_values"]["active_meetings"] = updated_config.get("active_meetings", []).copy()
            
            st.session_state["key_attendees"] = updated_config.get("key_attendees", []).copy()
            st.session_state["key_meetings"] = updated_config.get("key_meetings", []).copy()
            st.session_state["active_meetings"] = updated_config.get("active_meetings", []).copy()
            
            st.session_state["unsaved_changes"]["meetings"] = False
            st.session_state["unsaved_changes"]["key_attendees"] = False
            st.session_state["unsaved_changes"]["key_meetings"] = False
            st.session_state["unsaved_changes"]["active_meetings"] = False
            st.success("Meetings saved!")
        except Exception as e:
            st.error(f"Error saving meetings: {e}")

# Key Attendees
st.subheader("Key Attendees")
with st.expander("Key Attendee Details", expanded=True):
    if "key_attendees" not in st.session_state:
        st.session_state["key_attendees"] = config.get("key_attendees", []).copy()

    if "ka_remove_idxs" not in st.session_state:
        st.session_state["ka_remove_idxs"] = []

    meeting_names = [m["name"] for m in config.get("meetings", []) if m["name"]]
    member_names = [m["name"] for m in config.get("members", []) if m["name"]]

    # Table header
    ka_header_cols = st.columns([4, 7, 1])
    ka_header_cols[0].markdown("<div style='margin-bottom:-18px'><b>Meeting</b></div>", unsafe_allow_html=True)
    ka_header_cols[1].markdown("<div style='margin-bottom:-18px'><b>Attendees</b></div>", unsafe_allow_html=True)

    for i, ka in enumerate(st.session_state["key_attendees"]):
        # Skip key attendees that reference non-existent meetings
        if ka.get("meeting") not in meeting_names:
            continue
            
        cols = st.columns([4, 7, 1])
        
        meeting_key = f"ka_meeting_{i}"
        attendees_key = f"ka_attendees_{i}"
        remove_key = f"remove_ka_{i}"
        
        meeting = cols[0].selectbox("", meeting_names, index=meeting_names.index(ka["meeting"]) if ka.get("meeting") in meeting_names else 0, key=meeting_key)
        saved_member_names = [m["name"] for m in config.get("members", []) if m["name"]]
        attendees = cols[1].multiselect("", saved_member_names, ka.get("members", []), key=attendees_key)
        
        cols[2].markdown("<div style='height: 28px'></div>", unsafe_allow_html=True)
        if cols[2].button("❌", key=remove_key):
            st.session_state["ka_remove_idxs"].append(i)
        
        # Update session state immediately
        if st.session_state["key_attendees"][i]["meeting"] != meeting:
            st.session_state["key_attendees"][i]["meeting"] = meeting
            st.rerun()
        if st.session_state["key_attendees"][i].get("members") != attendees:
            st.session_state["key_attendees"][i]["members"] = attendees
            st.rerun()

    # Remove key attendees marked for deletion
    for idx in reversed(st.session_state["ka_remove_idxs"]):
        if idx < len(st.session_state["key_attendees"]):
            st.session_state["key_attendees"].pop(idx)
    st.session_state["ka_remove_idxs"] = []

    if st.button("Add new key attendee", key="add_ka"):
        st.session_state["key_attendees"].append({"meeting": meeting_names[0] if meeting_names else "", "members": []})
        st.rerun()

    # Check for changes in key attendees - compare against actual config file data
    current_key_attendees = [ka for ka in st.session_state["key_attendees"] if ka["meeting"] and ka["members"]]
    if current_key_attendees != st.session_state["original_values"]["key_attendees"]:
        st.session_state["unsaved_changes"]["key_attendees"] = True
        st.warning("⚠️ You have unsaved changes in Key Attendees")
    else:
        st.session_state["unsaved_changes"]["key_attendees"] = False

    if st.button("💾 Save Key Attendees", key="save_ka"):
        try:
            config["key_attendees"] = [ka for ka in st.session_state["key_attendees"] if ka["meeting"] and ka["members"]]
            with open(CONFIG_PATH, "w") as f:
                yaml.safe_dump(config, f)
            st.session_state["original_values"]["key_attendees"] = config["key_attendees"].copy()
            st.session_state["unsaved_changes"]["key_attendees"] = False
            st.success("Key attendees saved!")
        except Exception as e:
            st.error(f"Error saving key attendees: {e}")

# Key Meetings
st.subheader("Key Meetings")
with st.expander("Key Meeting Details", expanded=True):
    if "key_meetings_touched" not in st.session_state:
        st.session_state["key_meetings_touched"] = False

    config_key_meetings = config.get("key_meetings", [])
    valid_key_meetings = [m for m in config_key_meetings if m in meeting_names]

    current_key_meetings = st.multiselect(
        "",
        meeting_names,
        valid_key_meetings,
        key="key_meetings_multiselect",
        on_change=lambda: st.session_state.update({"key_meetings_touched": True})
    )

    if st.session_state["key_meetings_touched"] and current_key_meetings != valid_key_meetings:
        st.session_state["key_meetings"] = current_key_meetings
        st.session_state["unsaved_changes"]["key_meetings"] = True
        st.warning("⚠️ You have unsaved changes in Key Meetings")
    else:
        st.session_state["unsaved_changes"]["key_meetings"] = False

    if st.button("💾 Save Key Meetings", key="save_key_meetings"):
        try:
            config["key_meetings"] = st.session_state["key_meetings"]
            with open(CONFIG_PATH, "w") as f:
                yaml.safe_dump(config, f)
            st.session_state["original_values"]["key_meetings"] = st.session_state["key_meetings"].copy()
            st.session_state["unsaved_changes"]["key_meetings"] = False
            st.success("Key meetings saved!")
        except Exception as e:
            st.error(f"Error saving key meetings: {e}")

# Penalties
st.subheader("Penalties")
with st.expander("Penalty Details", expanded=True):
    if "penalties" not in st.session_state:
        st.session_state["penalties"] = config.get("penalties", {}).copy()

    penalty_items = list(st.session_state["penalties"].items())
    penalty_cols = st.columns([4, 2, 1])
    penalty_cols[0].markdown("**Penalty Name**")
    penalty_cols[1].markdown("**Value**")
    penalty_cols[2].markdown("")

    for i, (pen_name, pen_val) in enumerate(penalty_items):
        cols = st.columns([4, 2, 1])
        cols[0].markdown(f"<div style='line-height:100px; vertical-align: middle;'>{pen_name}</div>", unsafe_allow_html=True)
        value = cols[1].number_input("", value=pen_val, key=f"penalty_value_{i}")
        penalty_items[i] = (pen_name, value)

    st.session_state["penalties"] = {k: v for k, v in penalty_items if k}

    if st.session_state["penalties"] != st.session_state["original_values"]["penalties"]:
        st.session_state["unsaved_changes"]["penalties"] = True
        st.warning("⚠️ You have unsaved changes in Penalties")
    else:
        st.session_state["unsaved_changes"]["penalties"] = False

    if st.button("💾 Save Penalties", key="save_penalties"):
        try:
            config["penalties"] = st.session_state["penalties"]
            with open(CONFIG_PATH, "w") as f:
                yaml.safe_dump(config, f)
            st.session_state["original_values"]["penalties"] = st.session_state["penalties"].copy()
            st.session_state["unsaved_changes"]["penalties"] = False
            st.success("Penalties saved!")
        except Exception as e:
            st.error(f"Error saving penalties: {e}")

# Active Meetings
st.subheader("Active Meetings")
if "active_meetings_touched" not in st.session_state:
    st.session_state["active_meetings_touched"] = False

config_active_meetings = config.get("active_meetings", [])
valid_active_meetings = [m for m in config_active_meetings if m in meeting_names]

current_active_meetings = st.multiselect(
    "",
    meeting_names,
    valid_active_meetings,
    key="active_meetings_multiselect",
    on_change=lambda: st.session_state.update({"active_meetings_touched": True})
)

if st.session_state["active_meetings_touched"] and current_active_meetings != valid_active_meetings:
    st.session_state["active_meetings"] = current_active_meetings
    st.session_state["unsaved_changes"]["active_meetings"] = True
    st.warning("⚠️ You have unsaved changes in Active Meetings")
else:
    st.session_state["unsaved_changes"]["active_meetings"] = False

if st.button("💾 Save Active Meetings", key="save_active_meetings"):
    try:
        config["active_meetings"] = st.session_state["active_meetings"]
        with open(CONFIG_PATH, "w") as f:
            yaml.safe_dump(config, f)
        st.session_state["original_values"]["active_meetings"] = st.session_state["active_meetings"].copy()
        st.session_state["unsaved_changes"]["active_meetings"] = False
        st.success("Active meetings saved!")
    except Exception as e:
        st.error(f"Error saving active meetings: {e}")

# Run Scheduler
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
 