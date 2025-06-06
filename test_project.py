from datetime import datetime
import pytest  # type: ignore

from project import (
    time_now_minus_seconds_iso,
    check_if_event_type_is_default,
    check_what_to_do_with_event,
)
from project_event_data import EventData
from project_config_class import Config

event1 = {
    "kind": "calendar#event",
    "etag": '"3497041779813086"',
    "id": "19aqq9l97lldnafvarg401icu4",
    "status": "confirmed",
    "htmlLink": "https://www.google.com/calendar/event?eid=MTlhcXE5bDk3bGxkbmFmdmFyZzQwMWljdTQgd29say50b21hc3pAbQ",
    "created": "2025-05-29T11:36:44.000Z",
    "updated": "2025-05-29T12:14:49.906Z",
    "summary": "CS50P",
    "creator": {"email": "wolk.tomasz@gmail.com", "self": True},
    "organizer": {"email": "wolk.tomasz@gmail.com", "self": True},
    "start": {"dateTime": "2025-05-30T21:00:00+02:00", "timeZone": "Europe/Warsaw"},
    "end": {"dateTime": "2025-05-30T21:30:00+02:00", "timeZone": "Europe/Warsaw"},
    "iCalUID": "19aqq9l97lldnafvarg401icu4@google.com",
    "sequence": 1,
    "reminders": {"useDefault": True},
    "eventType": "default",
}

event2 = {
    "kind": "calendar#event",
    "id": "bgaqqy97yldnafvargfd1isd",
    "eventType": "workingLocation",
    "attendees": [
        {"email": "test@gmail.com", "responseStatus": "needsAction"},
        {"email": "wolk.tomasz@gmail.com", "responseStatus": "accepted"},
    ],
}

event3 = {
    "kind": "calendar#event",
    "id": "bgaqqy97yldnafvargfd1isd",
    "eventType": "birthday",
    "attendees": [
        {"email": "jerry@gmail.com", "responseStatus": "needsAction"},
        {"email": "wolk.tomasz@gmail.com", "responseStatus": "accepted"},
    ],
}


@pytest.mark.parametrize(
    "time_now, seconds, expected",
    [
        (datetime(2025, 5, 29, 12, 0, 0), 10, "2025-05-29T11:59:50"),
        (datetime(2025, 5, 29, 0, 0, 0), 10, "2025-05-28T23:59:50"),
        (datetime(2025, 5, 29, 0, 0, 5), 10, "2025-05-28T23:59:55"),
    ],
)
def test_time_now_minus_seconds_iso(time_now, seconds, expected):
    assert time_now_minus_seconds_iso(time_now, seconds) == expected


@pytest.mark.parametrize(
    "event, expected",
    [
        (event1, True),
        (event2, False),
        (event3, False),
    ],
)
def test_check_if_event_type_is_default(event, expected):
    assert check_if_event_type_is_default(event) == expected


def test_get_event_details(monkeypatch):
    event_data = EventData()
    config = Config()
    monkeypatch.setattr(config, "color", "11")
    monkeypatch.setattr(config, "prefix", "[TEST]")
    event_data.get_event_details(event1, config)
    assert event_data.data["summary"] == "[TEST] CS50P"
    assert event_data.data["colorId"] == "11"


def test_pop_unnecessary_keys():
    keys = [
        "recurringEventId",
        "kind",
        "created",
        "updated",
        "etag",
        "creator",
        "organizer",
        "originalStartTime",
        "htmlLink",
        "iCalUID",
        "sequence",
    ]
    event_data = EventData()
    event_data.data = event1
    event_data.pop_unnecessary_keys()
    assert all(key not in event_data.data for key in keys)


@pytest.mark.parametrize(
    "event, expected", [(event1, None), (event2, "Both"), (event3, "Main")]
)
def test_check_calendars_in_attendees(monkeypatch, event, expected):
    event_data = EventData()
    config = Config()
    monkeypatch.setattr(config, "calendar_id", "wolk.tomasz@gmail.com")
    monkeypatch.setattr(config, "target_calendar_id", "test@gmail.com")
    assert event_data.check_calendars_in_attendees(event, config) == expected


@pytest.mark.parametrize(
    "target_event, status, response_status, expected",
    [
        (None, "", "", "create"),
        ({"id": "123"}, "cancelled", "", "delete"),
        ({"id": "123"}, "", "declined", "delete"),
        ({"id": "123"}, "", "", "update"),
    ],
)
def test_check_what_to_do_with_event(target_event, status, response_status, expected):
    assert check_what_to_do_with_event(target_event, status, response_status) == expected
