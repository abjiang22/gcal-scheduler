from dataclasses import dataclass, field
from typing import List, Optional

@dataclass
class Member:
    id: str
    name: str
    calendar_id: str

@dataclass
class Meeting:
    id: str
    name: str
    members: List[str]
    duration: int  # in minutes
    scheduled_time: Optional[str] = None  # ISO format

@dataclass
class PotentialMeetingTime:
    id: str
    start_time: str  # ISO format
    end_time: str    # ISO format 