class MLMonitorError(Exception):
    """Base exception for the mlmonitor SDK."""


class AuthenticationError(MLMonitorError):
    """Raised when login fails or the token is invalid."""


class APIError(MLMonitorError):
    """Raised when the server returns a non-2xx response."""

    def __init__(self, status_code, detail):
        self.status_code = status_code
        self.detail = detail
        super().__init__(f'HTTP {status_code}: {detail}')
