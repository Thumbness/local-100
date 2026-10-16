import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from ...application.ports import SpotifyRateLimited

RETRY_STATUS_CODES = (429, 500, 502, 503, 504)


def _seconds(value) -> int:
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return 0


class FailFastRetry(Retry):
    """A Retry that gives up on long rate-limit waits instead of sleeping through them.

    Short waits are honoured as usual. A long Retry-After (urllib3 would sleep for up to hours)
    raises SpotifyRateLimited straight away so the caller can stop and tell the user.
    """

    MAX_WAIT_SECONDS = 60

    def increment(self, method=None, url=None, response=None, error=None, _pool=None, _stacktrace=None):
        if response is not None and response.status == 429:
            retry_after = _seconds(response.headers.get("Retry-After"))
            if retry_after > self.MAX_WAIT_SECONDS:
                try:
                    response.drain_conn()
                except Exception:
                    pass
                raise SpotifyRateLimited(retry_after)
        return super().increment(method, url, response=response, error=error,
                                 _pool=_pool, _stacktrace=_stacktrace)


def build_session(retries: int = 5, status_retries: int = 5, backoff_factor: float = 0.5) -> requests.Session:
    session = requests.Session()
    retry = FailFastRetry(
        total=retries,
        connect=None,
        read=False,
        allowed_methods=frozenset(["GET", "POST", "PUT", "DELETE"]),
        status=status_retries,
        backoff_factor=backoff_factor,
        status_forcelist=RETRY_STATUS_CODES,
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session
