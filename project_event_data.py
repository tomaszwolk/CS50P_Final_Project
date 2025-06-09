"""Event Data Class module

This class allows user to create, modyfi or delete events in Google Calendar.

Script requires googleapiclient.errors.

This module contains class EventData.
"""

from typing import Optional
from googleapiclient.errors import HttpError  # type: ignore[import-untyped]
from logger_class import Logger
from project_config_class import Config
import googleapiclient.discovery


class EventData:
    """Class to handle event data for Google Calendar API operations.

    This class is responsible for creating, updating, and managing Google Calendar event data.

    Attributes:
        data (dict): A dictionary to store event data,
                        which is populated by the get_event details method.

    This class contains following methods:
        - create_new_event(calendar_id, target_service, send_updates) -
            Creates a new event in the specified calendar using the Google Calendar API.
        - update_event(target_service, target_event_id) -
            Updates an existing event in the target calendar using the Google Calendar API.
        - get_event_details(event) -
            Copies all event data to self.data and modifies or adds additional information
            from config.ini.
        - pop_unnecessary_keys() -
            Removes keys from the event data that are not required
            or may cause errors during event creation or update.
        - get_attendee_response_status(event, email) -
            Get invitation response status if there are attendees.
        - check_if_id_exists_in_target_calendar(event_id, target_service) -
            Checks if an event with the given ID exists in the target calendar.
        - delete_event(calendar_id, event_id, target_service) -
            Deletes an event from the specified calendar using the Google Calendar API.
        - check_calendars_in_attendees(event) -
            Check if main or target calendars are in the event attendees.
    """

    def __init__(self):
        self.data = {}

    def create_new_event(
        self,
        calendar_id: str,
        target_service: googleapiclient.discovery.Resource,
        send_updates: str = "none",
    ) -> None:
        """Creates a new event in the specified calendar.

        This method uses the Google Calendar API to insert a new event into the target calendar.
        It takes event data from the instance's 'data' - created by get_event_details method.
        It also supports attachments and conference data,
            and by default does not send updates to attendees.

        Args:
            calendar_id: The ID of the calendar to create the event in target calendar
            target_service: The Google Calendar API service instance
                                used to interact with the calendar
            send_updates: Who gets information about changes in the event.
                Options:
                    - all
                    - externalOnly
                    - none
        """

        Logger().debug(
            f"Creating event with summary: {self.data.get('summary', 'No summary')}, "
            f"ID: {self.data.get('id', 'Unknown ID')}.",
            __name__,
        )
        try:
            event = (
                target_service.events()  # type: ignore
                .insert(
                    calendarId=calendar_id,
                    body=self.data,
                    conferenceDataVersion=1,
                    supportsAttachments=True,
                    sendUpdates=send_updates,
                )
                .execute()
            )
            Logger().info(
                f"Event created: {event.get('htmlLink')}\n{self.data}\n", __name__
            )
        except HttpError as e:
            Logger().error(
                f"HttpError creating event, ID: {self.data.get('id', 'Unknown ID')}",
                f"error: {e}.",
                __name__,
            )
        except Exception as e:
            Logger.error(
                f"Error creating event, ID: {self.data.get('id', 'Unknown ID')}, err: {e}.",
                __name__,
            )

    def update_event(
        self,
        target_service: googleapiclient.discovery.Resource,
        target_event_id: str,
        config: Config,
    ) -> None:
        """Updates existing event in target calendar.

        This method uses the Google Calendar API to update event in the target calendar.
        It takes event data from the instance's 'data' attribute - created by get_event_details.
        If the 'target_event_id' is not found in the target calendar, error is printed.
        It also supports attachments and conference data, and does not send updates to attendees.

        Args:
            target_service: The Google Calendar API service instance
                                used to interact with the calendar
            target_event_id: The ID of the event to update in the target calendar
            config: Instance of configuration class to manage application settings and
                Google Calendar API tokens.
        """

        try:
            target_service.events().update(  # type: ignore
                calendarId=config.target_calendar_id,
                eventId=target_event_id,
                body=self.data,
                conferenceDataVersion=1,
                supportsAttachments=True,
                sendUpdates="none",
            ).execute()
            Logger().info(
                f"Event: {self.data.get('summary', 'No summary')}, "
                f"ID: {target_event_id} has been updated.",
                __name__,
            )
        except Exception as e:
            Logger.error(
                f"Error updating event {self.data.get('summary', 'No summary')}, "
                f"ID: {target_event_id}: {e}",
                __name__,
            )

    def get_event_details(self, event: dict[str, str], config: Config) -> None:
        """Copies all event data to self.data and modify or add information from config.ini.

        It is used to prepare event data for creating or updating an event in the target calendar.
        This method modifies the event data by adding a prefix to the summary if in the config.ini.
        It also adds a colorId if it exists in the config.ini and appends a description -
            information that it was created by a script - if it is not already present.

        Args:
            event (dict): The event data
            config (instance): Instance of configuration class to manage application settings and
                Google Calendar API tokens.
        """

        self.data = event.copy()
        # Add prefix to summary if it exists in config.ini
        if config.prefix:
            event_summary = event.get("summary", "")
            if not event_summary.startswith(config.prefix):
                self.data["summary"] = f"{config.prefix} {event_summary}"
        # Add colorId if it exists in config.ini
        if config.color:
            self.data["colorId"] = config.color
        # Add description if it already is not added.
        description_added = config.suffix
        description = event.get("description", "")
        # Checks if already added - this is to avoid adding the same description multiple times.
        if description_added:
            if description_added not in description:
                # strip() is used to remove added \n\n if originaly there is no description.
                self.data["description"] = (
                    description + "\n\n" + description_added
                ).strip()

    def pop_unnecessary_keys(self) -> None:
        """Removes keys from the event data that are not required or may cause errors.

        The excluded keys are typically metadata or system-generated fields that are not necessary
        for creating or updating events in the target calendar:

        - "originalStartTime", "recurringEventId": These are related to recurring events and
                    may conflict with new event creation.
        - "created", "creator", "etag", "htmlLink", "kind", "organizer", "sequence", "updated":
                    These are system-generated fields that are not modifiable.
        - "iCalUID": This is a unique identifier for the event in iCalendar format.
                    Can't use if 'id' is passed to the API.
        """

        keys_to_pop = (
            "created",
            "creator",
            "etag",
            "htmlLink",
            "iCalUID",
            "kind",
            "originalStartTime",
            "organizer",
            "recurringEventId",
            "sequence",
            "updated",
        )
        try:
            self.data = {  # type: ignore
                key: value for key, value in self.data.items() if key not in keys_to_pop  # type: ignore
            }
        except Exception as e:
            Logger().error(f"Exception pop_unnecessary_keys: {e}", __name__)

    @staticmethod
    def get_attendee_response_status(
        event: dict[str, str], email: str
    ) -> Optional[str]:
        """Get invitation response status if there are attendees.

        Email address is taken from Config.CALENDAR_ID or Config.TARGET_CALENDAR_ID.

        Args:
            event: The event data
            email: The email address of the attendee whose response status is to be checked

        Returns:
            'needsAction' - invitation not accepted (default) ->
                create new event or do nothing if event already created
            'declined' - invitation declined ->
                delete the event (it was created when the invitation was received)
            'tentative' - the invitation is being considered ->
                create new event or do nothing if event already created
            'accepted' - invitation accepted ->
                create new event or do nothing if event already created
        """

        try:
            attendees = event.get("attendees")
            response_status = None
            if attendees is not None:
                for attendee in attendees:
                    if attendee.get("email") == email:  # type: ignore
                        return attendee.get("responseStatus", None)  # type: ignore
            return response_status
        except AttributeError as e:
            Logger().error(
                f"AttributeError getting response status. ID: {event.get('id')} - {e}.",
                __name__,
            )
            return None
        except Exception as e:
            Logger().error(
                f"Exception getting response status. ID: {event.get('id')} - {e}.",
                __name__,
            )
            return None

    @staticmethod
    def check_if_id_exists_in_target_calendar(
        event_id: str,
        target_service: googleapiclient.discovery.Resource,
        config: Config,
    ) -> Optional[dict[str, str]]:
        """Checks if an event with the given ID exists in the target calendar.

        Args:
            event_id: The event ID to check in the target calendar
            target_service (service instance): The Google Calendar API service instance
                                used to interact with the calendar
            config (instance): Instance of configuration class to manage application settings and
                Google Calendar API tokens.

        Returns:
            dict: The event data from the target calendar if it exists
            None: If the event does not exist in the target calendar or if an error occurs
        """

        try:
            target_event = (
                target_service.events()  # type: ignore
                .get(calendarId=config.target_calendar_id, eventId=event_id)
                .execute()
            )
            return target_event
        except HttpError:
            Logger.info(
                f"Event ID: {event_id} doesn't exist in target calendar", __name__
            )
            return None

    @staticmethod
    def delete_event(
        calendar_id: str,
        event_id: str,
        target_service: googleapiclient.discovery.Resource,
    ) -> None:
        """Deletes an event from the specified calendar.

        Args:
            calendar_id: The ID of the calendar from which to delete the event
            event_id: The ID of the event to delete
            target_service (service instance): The Google Calendar API service instance
                                used to interact with the calendar
        """

        try:
            target_service.events().delete(  # type: ignore
                calendarId=calendar_id, eventId=event_id
            ).execute()
            Logger().info(f"Event ID: {event_id} deleted", __name__)
        except HttpError as e:
            Logger().error(f"HttpError deleting event {event_id}: {e}.", __name__)
        except Exception as e:
            Logger().error(f"Error deleting event {event_id}: {e}.", __name__)

    @staticmethod
    def check_calendars_in_attendees(
        event: dict[str, str], config: Config
    ) -> Optional[str]:
        """Check if main or target calendars are in the event attendees.

        This function expects the "event" dictionary to have an optional "attendees" key,
        which shoul be a list of dictionaries, each representing an attendee with an "email" key.

        If both calendars are in the event attendees, then return "Both" and skip the event.
        If only main or target calendar is in the event attendees,
        then return "Main" or "Target" and create or update the event.
        If none of the calendars are in the event attendees, then return None.

        Args:
            event (dict): The event data
            config (instance): Instance of configuration class to manage application settings and
                Google Calendar API tokens.

        Returns:
            str: "Both" | "Main" | "Target"
            None: If neither calendar is in the event attendees
        """

        calendar_id_in_attendees = False
        target_calendar_id_in_attendees = False
        try:
            attendees = event.get("attendees", [])  # type: ignore
            if not attendees:
                return None
            for attendee in attendees:
                if attendee.get("email", "") == config.calendar_id:  # type: ignore
                    calendar_id_in_attendees = True
                if attendee.get("email", "") == config.target_calendar_id:  # type: ignore
                    target_calendar_id_in_attendees = True

            if calendar_id_in_attendees and target_calendar_id_in_attendees:
                return "Both"
            if calendar_id_in_attendees and not target_calendar_id_in_attendees:
                return "Main"
            if not calendar_id_in_attendees and target_calendar_id_in_attendees:
                return "Target"
            return None
        except Exception as e:
            Logger().error(
                f"Error checking attendees for event ID: {event.get('id')}. "
                f"Summary: {event.get('summary', 'No summary')} - {e}",
                __name__,
            )
            return None
