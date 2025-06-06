"""NotificationChannel Class module

This module manages notification channels for Google Calendar API.
"""

import uuid
from datetime import datetime, timedelta

import requests  # type: ignore[import-untyped]
from flask import request
from logger_class import Logger # type: ignore[import-not-found]


class NotificationChannel:
    """Class to manage notification channels for Google Calendar API.

    This class allows creating a notification channel for a specific calendar
    and validating POST requests sent to the webhook URL.  
    It generates a unique channel ID and handles the creation of the channel.  

    Attributes:
        calendar_id (str): The ID of the calendar to create the notification channel for.
        webhook_url (str): The URL to which notifications will be sent.
        auth_token (str): The OAuth 2.0 token for authentication.
        channel_id (str): A unique identifier for the notification channel, generated using UUID.
    
    This class contains following methods:
        - create_notification_channel() - 
            Creates a notification channel for given calendar and returns the response from
                the Google Calendar API.
        - validate_post_request(time_now, last_update_timestamp) - 
            Validates the POST request for the notification channel based on the current time
                and last update timestamp.
    """

    def __init__(self, calendar_id: str, webhook_url: str, auth_token: str):
        """Initialize an instance.
        
        Args:
            calendar_id: The ID of the calendar to create the notification channel for
                                Expected format: email address
            webhook_url: The URL to which notifications will be sent
                                Expected format: HTTPS URL
            auth_token: The OAuth 2.0 token for authentication
            channel_id (str): A unique identifier for the notification channel, generated using UUID
        """

        self.calendar_id = calendar_id
        self.webhook_url = webhook_url
        self.auth_token = auth_token
        self.channel_id = str(uuid.uuid4())  # Generate a unique channel ID

    def create_notification_channel(self) -> dict:
        """Creates a notification channel for a given calendar.

        This method sends a POST request to the Google Calendar API to create a notification channel
        
        Returns:
            Json response from the Google Calendar API.  
                If the request is successful (HTTP status code 200), the response contains
                    details of the created channel.  
                If the request fails, the response contains an error message.
        """

        url = f"https://www.googleapis.com/calendar/v3/calendars/{self.calendar_id}/events/watch"
        headers = {
            "Authorization": f"Bearer {self.auth_token}",
            "Content-Type": "application/json",
        }
        payload = {
            "id": self.channel_id,
            "type": "web_hook",
            "address": self.webhook_url,
        }

        response = requests.post(url, headers=headers, json=payload, timeout=2)

        if response.status_code == 200:
            Logger().info("Notification channel created successfully!", __name__)
            Logger().debug(kwargs=response.json())
            return response.json()
        Logger().info("Notification channel HAS NOT BEEN created.", __name__)
        Logger().warning(kwargs=response.json())
        return response.json()

    @staticmethod
    def validate_post_request(
        time_now: datetime, last_update_timestamp: datetime
    ) -> str:
        """Validates the POST request for the notification channel.

        This method checks if the request is valid based on the current time
            and the last update timestamp.  
        It ensures that the request method is POST and checks the resource state in the headers.  
        
        Args:
            time_now: The current time when the request is received.
            last_update_timestamp: The timestamp of the last update.
        
        Returns:
            Resource state if == "exists'.
            HTTP status code indicating the result of the validation.
        """

        if last_update_timestamp > (time_now - timedelta(seconds=1)):
            Logger().debug("208 - Already Reported", __name__)
            return "208"  # Already Reported
        if request.method != "POST":
            Logger().warning("405 - Method Not Allowed", __name__)
            return "405"  # Method Not Allowed

        # print(f"Full headers: {request.headers}")  # Keep for debugging
        resource_state = request.headers.get("X-Goog-Resource-State")
        if resource_state == "sync":
            Logger().debug("This is a sync message.", __name__)
            return "200"  # OK
        if resource_state == "exists":
            return "exists"
        if resource_state is None:
            Logger().warning("No resource state in headers.", __name__)
            return "400"  # Bad Request
        Logger().warning(
            f"Resource state: {resource_state}. "
            "Waiting for resource state == 'exists'.", __name__
        )
        return "202"  # Accepted, waiting for resource state to be 'exists'
