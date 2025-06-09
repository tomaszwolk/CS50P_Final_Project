"""Calendar Synchronization aplication.

This application synchronizes events between two Google Calendar accounts.
It uses Google Calendar API to create a webhook for receiving notifications about events.
When an event is created, updated, or deleted in the master calendar, then the application will
synchronize the changes in the target calendar.  

This application is designed to work with flask,
that's why it calls app.run() when __name__ == "__main__".  

Functions to be performed by the application:  
    1. Automatically generate tokens when they are missing or expired.  
    2. Create a webhook with google calendar API.  
    3. Retrieve the list of events that has been changed in last 10 seconds 
       from master calendar upon receipt of the webhook  
    4. Script won't create an event in the target calendar if:  
        - the event type is not "default" (e.g. "workingLocation", "birthday" etc.)  
        - both calendars are in the event as attendees  
        - webhook was received faster than a second after the last operation  
    5. Checking the status of the event:  
        - adding a new event to the target calendar if it was created by the owner
            or appeared as a guest  
        - remove the event from the target calendar if the event is “cancelled”
            or the invitation was not accepted  
        - update the event in the target calendar if it already exists  
    6. Script modyfies color and the event summary by adding a prefix according to the config file
       and adds info in the description about the script that created the event.  

How to use script:
    - create Google Cloud project (example https://developers.google.com/people/quickstart/python)  
        - enable Google Calendar API
        - create desktop client
        - download credentials as credentials.json
    - configure app with config.ini
    - create tokens
        - start project.py on your own serwer or
        - run python project_config_class.py if you are using external services and copy tokens
    - run your own HTTPS serwer (for example use nginx) or run it on external service like
        PythonAnywhere.com
        - in PythonAnywhere configure flask serwer
        - copy all files and folders to /home/username/mysite - rename project.py to flask_app.py
    - test it

Required pip modules:
    - flask                     (pip install flask)
    - google-api-python-client  (pip install google-api-python-client)
    - google-auth-httplib2      (pip install google-auth-httplib2)
    - google-auth-oauthlib      (pip install google-auth-oauthlib)
    - validator-collection      (pip install validator-collection)

The module contains the following functions:
    - time_now_minus_seconds_iso(time_now, seconds) - 
        Checks actual time and subtract from it 10 seconds.  
    - check_if_event_type_is_default(event) - 
        Checks if the event type is 'default'.  
    - check_what_to_do_with_event(target_event, status, response_status) - 
        Check conditionals and return str with info what to do with event.  

Additional info:
I'm using MyPy, if library does not have type hints, then I use # type: ignore[...]"""

from datetime import timezone, datetime, timedelta
from typing import Optional
from flask import Flask
from googleapiclient.discovery import build  # type: ignore[import-untyped]
from googleapiclient.errors import HttpError  # type: ignore[import-untyped]
from project_notification_channel_class import NotificationChannel
from project_config_class import Config
from project_event_data import EventData
from logger_class import Logger

app = Flask(__name__)

# Timezone and last_update_timestamp needed to validate Post requests
# Choose your serwer timezone
SERVER_TIMEZONE = timezone(timedelta(hours=0))
last_update_timestamp = datetime(2025, 4, 1, 8, 0, tzinfo=SERVER_TIMEZONE)

CREDENTIALS = None
TARGET_CREDENTIALS = None


@app.route("/notifications", methods=["POST"])  # type: ignore
def main() -> str:
    """Main function. It's called when webhook is received.
    
    Returns:
        HTTP status code
    """

    global last_update_timestamp

    time_now = datetime.now(timezone.utc)
    resource_state = NotificationChannel.validate_post_request(
        time_now, last_update_timestamp
    )
    if resource_state != "exists":
        return resource_state

    # If resource_state == "exists", then update LAST_UPDATE_TIMESTAMP and last modified events
    last_update_timestamp = time_now
    try:
        # Building the service to retrieve events from main calendar
        service = build(
            "calendar", "v3", credentials=CREDENTIALS, cache_discovery=False
        )
        # Building the service to create, update, or delete events in target calendar
        target_service = build(
            "calendar", "v3", credentials=TARGET_CREDENTIALS, cache_discovery=False
        )
    except HttpError as error:
        Logger().error(f"An error occurred during building the service: {error}")
        return "500"  # Internal Server Error

    page_token = ""

    while True:
        # Retrieve the list of events from the master calendar
        # that has been changed in last 10 seconds
        try:
            events_result = (
                service.events()  # type: ignore
                .list(
                    calendarId=config.calendar_id,
                    updatedMin=time_now_minus_seconds_iso(time_now, seconds=10),
                    singleEvents=False,
                    maxResults=250,
                    pageToken=page_token,
                )
                .execute()
            )
        except Exception as e:
            Logger().error(f"An error occurred while retrieving events: {e}")
            return "500"
        events = events_result.get("items", [])
        if events:
            for event in events:
                # For debugging print whole event.
                Logger().debug(f"Checking event: {event}")
                event_data = EventData()

                # Check if event type is default.
                if not check_if_event_type_is_default(event):  # type: ignore[arg-type]
                    Logger().info(
                        f"Event ID: {event.get('id')}, summary: {event.get('summary')} "
                        f"Event type is not default: {event.get('eventType')}. Skip."
                    )
                    continue
                # Check if CALENDAR_ID and TARGET_CALENDAR_ID are attendees in event.
                if event_data.check_calendars_in_attendees(event, config) == "Both":  # type: ignore
                    Logger().info(
                        f"Event ID: {event.get('id')}, summary: {event.get('summary')} "
                        "Both calendars are in the event. Skip."
                    )
                    continue

                event_id = event.get("id", "")
                status = event.get("status", "")
                target_event = event_data.check_if_id_exists_in_target_calendar(
                    event_id, target_service, config
                )
                response_status = event_data.get_attendee_response_status(
                    event, config.calendar_id  # type: ignore[arg-type]
                )
                match check_what_to_do_with_event(target_event, status, response_status):
                    # If event doesn't exists in Target Calendar and it's not been cancelled or
                    # declined then create new one in Target Calendar.
                    case "create":
                        Logger().info(
                            f"Event ID: {event['id']}, summary: {event['summary']}. "
                            "Creating new event."
                        )
                        event_data.get_event_details(event, config)  # type: ignore[arg-type]
                        event_data.pop_unnecessary_keys()
                        event_data.create_new_event(
                            config.target_calendar_id, target_service
                        )
                        continue

                    # If event does exists in Target Calendar and it is cancelled or declined
                    # then delete event in Target Calendar.
                    case "delete":
                        Logger().info(
                            f"Event ID: {event['id']}, summary: {event['summary']}. "
                            "Deleting event."
                        )
                        event_data.delete_event(
                            config.target_calendar_id, event_id, target_service
                        )
                        continue

                    # If event does exists in Target Calendar and it's not been cancelled or
                    # declined then update event in Target Calendar.
                    case "update":
                        Logger().info(
                            f"Event ID: {event['id']}, summary: {event['summary']}. "
                            "Updating event."
                        )
                        event_data.get_event_details(event, config)  # type: ignore[arg-type]
                        event_data.pop_unnecessary_keys()
                        event_data.update_event(target_service, event_id, config)
        # Check if there is more events using 'nextPageToken
        page_token = events_result.get("nextPageToken", "")
        if not page_token:
            break
    return "200"  # OK


def time_now_minus_seconds_iso(time_now: datetime, seconds: int = 10) -> str:
    """Checks actual time and subtract from it given seconds.

    It's used for getting list of events.

    Args:
        time_now: The current time when the request is received.
        seconds: Amount of seconds is being substracted from actual time

    Returns:
        Actual time minus given time in seconds. In ISO format.
    """

    now_minus_x_seconds = time_now - timedelta(seconds=seconds)
    return now_minus_x_seconds.isoformat()


def check_if_event_type_is_default(event: dict) -> bool:
    """Checks if the event type is 'default'.

    Possible event types:
        - 'default'
        - 'workingLocation'
        - 'birthday'
        - 'outOfOffice'
        - 'focusTime'
        - 'fromGmail'

    Args:
        event: The event data dictionary.

    Returns:
        True if event is default, False otherwise.
    """

    event_type = event.get("eventType")
    return bool(event_type == "default")


def check_what_to_do_with_event(
    target_event: Optional[dict], status: str, response_status: Optional[str]
) -> str:
    """Check conditionals and return str with info what to do with event.

    Args:
        target_event: If target event exists, then it's a dict. Else -> None
        status: status of the event. Options: "confirmed", "tentative" or "cancelled"
        response_status: string if attendees are in event contains invitation response status. 
            Else -> None

    Returns:
        "create", "delete" or "update"
    """

    if not target_event and status != "cancelled" and response_status != "declined":
        return "create"
    if target_event and (status == "cancelled" or response_status == "declined"):
        return "delete"
    return "update"


# --- Run the channel creation when the app starts ---
with app.app_context():
    config = Config()
    CREDENTIALS = config.create_token(
        config.token_path, config.credentials_path, CREDENTIALS
    )
    if CREDENTIALS is not None:
        AUTH_TOKEN: str = CREDENTIALS.token  # type: ignore[attr-defined]
    else:
        AUTH_TOKEN = ""
        Logger().critical(
            "Error: CREDENTIALS is None. Check your config.ini and credentials.json files."
        )
    # If both calendars belong to the same user, then target_token == token
    if config.same_user:
        data = config.token_path.read_bytes()
        config.target_token_path.write_bytes(data)
    else:
        TARGET_CREDENTIALS = config.create_token(
            config.target_token_path, config.credentials_path, TARGET_CREDENTIALS
        )

    notification_channel = NotificationChannel(
        config.calendar_id, config.webhook_url, AUTH_TOKEN
    )
    notification_channel.create_notification_channel()


# --- Run Flask app ---
if __name__ == "__main__":
    app.run()
