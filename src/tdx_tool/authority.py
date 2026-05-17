# Dependencies
from logging import Logger
from requests import post
from datetime import datetime
from threading import Lock
import logging
# Local imports
from .utils import TDX_AUTH

class tdx_auth:
    """
    Automatically handles TDX API token retrieval and caching.
    Check token validity on each access and refreshes if expired.
    
    Parameters for initialization:
    -   `client_id`: TDX API Client ID (required)
    -   `client_key`: TDX API Client Key (required)
    -   `logger`: Logger instance
    ---
    Attributes:
    -   `client_id`: TDX API Client ID
    -   `client_key`: TDX API Client Key
    -   `logger`: Logger instance for logging
    -   `token`: Cached token value
    ---
    Example usage:
    >>> auth = tdx_auth(client_id="your_client_id", client_key="your_client_key")
    >>> token = auth.token  # Get current token (refreshes if expired)
    >>> token = auth()  # Alternative way to get token
    >>> print(auth)  # Print auth instance details
    """
    def __init__(
        self,
        client_id: str,
        client_key: str,
        logger: Logger
    ):
        self.client_id = client_id
        self.client_key = client_key
        self.logger = logger
        self._expire_time = self.__timenow - 60 # Force initial token retrieval
        self.logger.debug(f"tdx_auth initialized with client_id: {client_id}")
        self._token_lock = Lock() # Lock for thread-safe token refresh

    @property
    def __timenow(self) -> float:
        return datetime.now().timestamp()

    def update_token(self) -> str:
        """
        Retrieve a new token from user id and key
        """
        # Request a new token
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
        }
        data = {
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": self.client_key
        }

        response = post(TDX_AUTH, data=data, headers=headers, timeout=10)
        response.raise_for_status()
        token_data = response.json()
        self._expire_time = self.__timenow + token_data["expires_in"] - 60
        self.logger.debug("New token obtained successfully")
        return token_data["access_token"]

    @property
    def token(self) -> str:
        if self.__timenow > self._expire_time:
            with self._token_lock:
                self.logger.debug("Token expired, fetching a new one and updating cache")  
                if self.__timenow > self._expire_time:
                    self._token = self.update_token()
        else:
            self.logger.debug("Take token from cache")
        return self._token
    
    def __call__(self) -> str:
        return self.token
    
    def __str__(self) -> str:
        return f"tdx_auth(client_id={self.client_id}, expire_time={self._expire_time})"

    def __repr__(self) -> str:
        return self.__str__()