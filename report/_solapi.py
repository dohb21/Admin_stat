import hashlib
import hmac
import uuid
from datetime import datetime, timezone


def solapi_auth_header(api_key: str, api_secret: str) -> str:
    date = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    salt = uuid.uuid4().hex
    sig = hmac.new(api_secret.encode(), f"{date}{salt}".encode(), hashlib.sha256).hexdigest()
    return f"HMAC-SHA256 apiKey={api_key}, date={date}, salt={salt}, signature={sig}"
