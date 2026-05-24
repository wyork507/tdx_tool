# Dependencies
from logging import Logger
from requests import post
from datetime import datetime
from threading import Lock
# Local imports
from .utils import TDX_AUTH

class _tdx_auth_meta(type):
    _instances = {}
    _lock = Lock()
    def __call__(cls, *args, **kwargs):
        client_id = kwargs.get("client_id") or (args[0] if len(args) > 0 else None)
        key = (cls, client_id)

        with cls._lock:
            if key not in cls._instances:
                instance = super().__call__(*args, **kwargs)
                cls._instances[key] = instance
            return cls._instances[key]

class tdx_auth(metaclass=_tdx_auth_meta):
    """
    A class that manages TDX API authentication tokens with automatic refresh and caching.
    
    Parameters
    ----------
    client_id: str
        TDX API Client ID (required)
    client_key: str
        TDX API Client Key (required)
    logger: Logger
        Logger instance for logging (required)
    
    Attributes
    ----------
    client_id: str
        TDX API Client ID
    client_key: str
        TDX API Client Key
    logger: Logger
        Logger instance for logging
    token: str
        Current valid token
    expire_time: datetime
        Timestamp of when the current token expires

    Methods
    -------
    update_token() -> str
        Force a token refresh and return the new token
    
    Notes
    -----
    - This class can be called directly to get the current valid token, same as accessing the `token` property.
    - Regularly, the token would be refreshed when it expires, with a 60 second buffer.
    
    Examples
    --------
    To create an instance of tdx_auth, you need to provide your TDX API client ID and key, then enter:
    >>> auth = tdx_auth(client_id="your_client_id", client_key="your_client_key", logger=your_logger)
    
    Or without a logger (using a default logger that does not output anywhere):
    >>> auth = tdx_auth.without_logger(client_id="your_client_id", client_key="your_client_key")

    When you need to get an API token, you can do either of the following:
    >>> token = auth.token # 1. Get token via property 
    >>> token = auth()     # 2. Alternative way to get token
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
        self._token: str | None = None
        self._expire_time = self.__timenow - 60 # Force initial token retrieval
        self.logger.debug(f"[TDXAuth]-Initialized: {client_id}")
        self._token_lock = Lock() # Lock for thread-safe token refresh
    
    @classmethod
    def without_logger(cls, client_id: str, client_key: str) -> "tdx_auth":
        """
        Alternative constructor that creates a tdx_auth instance without requiring a logger.

        Parameters
        ----------
        client_id: str
            TDX API Client ID (required)
        client_key: str
            TDX API Client Key (required)
        
        Returns
        -------
        tdx_auth
            A new instance of tdx_auth with a default logger
        """
        import logging
        logger = logging.getLogger(__name__)
        return cls(client_id, client_key, logger)

    @property
    def __timenow(self) -> float:
        """INTERNAL: Get the current time as a timestamp (seconds since epoch)"""
        return datetime.now().timestamp()
    
    @property
    def expire_time(self) -> datetime:
        """Get the timestamp of when the current token expires"""
        return datetime.fromtimestamp(self._expire_time)

    def update_token(self) -> str:
        """
        Fetch a new token from the TDX API and update the cache with the new token and its expiration time.

        Returns
        -------
        str
            The new token obtained from the TDX API
        
        Raises
        ------
        requests.exceptions.Timeout
            No response received over 10 seconds while trying to obtain a new token
        requests.exceptions.HTTPError
            Non-successful HTTP status code received while trying to obtain a new token
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
        # If successful, update the token and expiration time in the cache
        token_data = response.json()
        self._expire_time = self.__timenow + token_data["expires_in"] - 60
        self.logger.debug("[TDXAuth]-New token obtained successfully")
        return token_data["access_token"]

    @property
    def token(self) -> str:
        """
        Get the current valid token, refreshing it if it has expired.
        
        Returns
        -------
        str
            The current valid token for TDX API access
        
        Raises
        ------
        RuntimeError
            If the token is not available after an attempted refresh (e.g., due to network issues)
        RequestException
            If an error occurs while trying to refresh the token (e.g., network error, API error)
        """
        from requests.exceptions import RequestException
        if self.__timenow > self._expire_time:
            with self._token_lock:
                self.logger.debug("[TDXAuth]-Token expired, fetching a new one and updating cache")
                if self.__timenow > self._expire_time:
                    try:
                        self._token = self.update_token()
                    except RequestException as e:
                        if self._token is not None:
                            self.logger.warning(
                                f"[TDXAuth]-Token refresh failed, keeping cached token: {e}"
                            )
                        else:
                            self.logger.error(f"[TDXAuth]-Error occurred while fetching new token: {e}")
                            raise e
        else:
            self.logger.debug("[TDXAuth]-Taking token from cache")
        if self._token is None:
            raise RuntimeError("TDXAuth token is not available.")
        return self._token
    
    def __call__(self) -> str:
        return self.token
    
    def __str__(self) -> str:
        return f"tdx_auth(client_id={self.client_id}, expire_time={self.expire_time.strftime('%Y-%m-%d %H:%M:%S')})"

    def __repr__(self) -> str:
        return self.__str__()
    
    def _repr_markdown_(self) -> str:
        return f"""
        tdx_auth
        client_id: {self.client_id}
        expire_time: {self.expire_time.strftime('%Y-%m-%d %H:%M:%S')}
        """
    