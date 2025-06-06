"""Config class module

This class set up configuration to manage application settings and Google Calendar API.

Pip install requires:
    - google.auth.transport.requests
    - google.oauth2.credentials
    - google_auth_oauthlib.flow
    - validator_collection
"""

import configparser
import os
import json

from pathlib import Path
from typing import Optional
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow  # type: ignore[import-untyped]
from validator_collection import checkers  # type: ignore[import-untyped]
from logger_class import Logger


# Implements Singleton pattern to ensure only one instance exists throughout the application.
class Config:
    """Configuration class to manage application settings and Google Calendar API tokens.

    This class reads configuration from a file, manages OAuth 2.0 credentials, and provides
    methods to create and refresh tokens for accessing the Google Calendar API.  

    If run directly it will create or refresh tokens.  

    Attributes:
        scopes (list): List of OAuth 2.0 scopes for the Google Calendar API.
        calendar_id (str): The ID of the calendar to be accessed.
        target_calendar_id (str): The ID of the target calendar for synchronization.
        webhook_url (str): The URL to which notifications will be sent.
        prefix (Optional[str]): Optional prefix for event summaries.
        color (Optional[str]): Optional color for event summaries.
        suffix (Optional[str]): Optional suffix for event description.
        same_user (bool): Flag indicating whether to use the same user for both calendars.
        token_path (Path): Path to the token file for the master calendar.
        target_token_path (Path): Path to the token file for the target calendar.
        credentials_path (Path): Path to the credentials file for OAuth 2.0 authentication.
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"]: Update Environment Variable

    This class contains following methods:
        - create_token(token_path, credentials_path, credentials, scopes) - 
            Creates the OAuth 2.0 token for accessing the Google Calendar API.
    """

    def __init__(self) -> None:
        self.folder_path, self.config_file_path = self.get_paths()
        self.config = configparser.ConfigParser()
        self.config.read(self.config_file_path)

        self.scopes: list = json.loads(self.config.get("configuration", "SCOPES"))
        if not isinstance(self.scopes, list) or not all(
            checkers.is_url(scope) for scope in self.scopes
        ):
            raise ValueError("SCOPES must be a list of valid URLs.")
        self.calendar_id: str = self.config.get("configuration", "CALENDAR_ID")
        if not checkers.is_email(self.calendar_id):
            raise ValueError(
                f"Invalid CALENDAR_ID: {self.calendar_id}. "
                "Must be a valid email address."
            )
        self.target_calendar_id: str = self.config.get(
            "configuration", "TARGET_CALENDAR_ID"
        )
        if not checkers.is_email(self.target_calendar_id):
            raise ValueError(
                f"Invalid TARGET_CALENDAR_ID: {self.target_calendar_id}. "
                "Must be a valid email address."
            )
        self.webhook_url: str = self.config.get("configuration", "WEBHOOK_URL")
        if not checkers.is_url(self.webhook_url) or not self.webhook_url.startswith(
            "https://"
        ):
            raise ValueError(
                f"Invalid WEBHOOK_URL: {self.webhook_url}. Must be a valid HTTPS URL."
            )
        self.prefix: Optional[str] = self.config.get(
            "configuration", "PREFIX", fallback=None
        )
        self.color: Optional[str] = self.config.get(
            "configuration", "COLOR", fallback=None
        )
        self.suffix: Optional[str] = self.config.get(
            "configuration", "SUFFIX", fallback=None
        )
        self.same_user: bool = self.config.getboolean(
            "configuration", "SAME_USER", fallback=False
        )
        self.token_path = self.folder_path / self.config.get(
            "configuration", "TOKEN_PATH"
        )
        self.target_token_path = self.folder_path / self.config.get(
            "configuration", "TARGET_TOKEN_PATH"
        )
        self.credentials_path = self.folder_path / self.config.get(
            "configuration", "CREDENTIALS_PATH"
        )
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = self.config.get(
            "configuration", "GOOGLE_APPLICATION_CREDENTIALS"
        )

    def create_token(
        self,
        token_path: Path,
        credentials_path: Path,
        credentials,
    ) -> str:
        """Creates a token for the Google Calendar API.

        This method is implementation from https://developers.google.com/people/quickstart/python  
        Link above also shows how to enable Google Calendar API and how to create OAuth 2.0 creds.  
        It checks if the token file exists and is valid. If not, it prompts the user to log in
        and saves the new credentials to the token file.  

        Args:
            token_path: Path to the token file.
            credentials_path: Path to the credentials file.
            credentials (object): OAuth 2.0 credentials object.
        
        Returns:
            Credentials object containing the access token.
        """

        # --- Load OAuth 2.0 Credentials ---
        if os.path.exists(token_path):
            credentials = Credentials.from_authorized_user_file(token_path, self.scopes)
        # If there are no (valid) credentials available, let the user log in.
        if not credentials or not credentials.valid:
            if credentials and credentials.expired and credentials.refresh_token:
                credentials.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    credentials_path, self.scopes
                )
                credentials = flow.run_local_server(port=0)
            # Save the credentials for the next run
            with open(token_path, "w", encoding="utf-8") as token:
                token.write(credentials.to_json())

        return credentials  # type: ignore[import-untyped]

    def get_paths(self) -> tuple[Path, Path]:
        """Function get absolute path to folder and config.ini and checks if file exists.

        Returns:
            path to parent folder and configuration file 'config.ini'
        """

        # Absolute path to the folder containing config.ini and token files.
        folder_path = Path(__file__).parent.resolve()
        # When using PythonAnywhere, can't use "Path(__file__).resolve()" because it returns wrong
        # path. That's why I add "config.ini" to the folder_path
        config_file_path = folder_path / "config.ini"
        if not config_file_path.exists():
            raise FileNotFoundError(
                f"Configuration file not found at {config_file_path}"
            )
        return folder_path, config_file_path


if __name__ == "__main__":
    config = Config()
    CREDENTIALS = config.create_token(
        config.token_path, config.credentials_path, credentials=None
    )
    if CREDENTIALS is not None:
        AUTH_TOKEN: str = CREDENTIALS.token  # type: ignore[attr-defined]
    else:
        AUTH_TOKEN = ""
        Logger().error(
            "Error: CREDENTIALS is None. Check config.ini and credentials.json files.",
            __name__,
        )
    # If both calendars belong to the same user, then target_token == token
    if config.same_user:
        data = config.token_path.read_bytes()
        config.target_token_path.write_bytes(data)
    else:
        TARGET_CREDENTIALS = config.create_token(
            config.target_token_path, config.credentials_path, credentials=None
        )
