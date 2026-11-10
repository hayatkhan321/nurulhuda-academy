"""Classroom video. Daily (daily.co) powers it now; another provider can be added behind the same three calls."""
import json
import urllib.error
import urllib.request
from datetime import timedelta

from flask import current_app

from nurulhuda.ledger import aware


class VideoError(Exception):
    pass


def configured() -> bool:
    return bool(current_app.config.get("DAILY_API_KEY"))


def _api(method: str, path: str, body: dict | None = None) -> dict:
    req = urllib.request.Request(
        "https://api.daily.co/v1" + path, method=method,
        data=json.dumps(body).encode() if body is not None else None,
        headers={"Authorization": f"Bearer {current_app.config['DAILY_API_KEY']}", "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read() or b"{}")
    except urllib.error.HTTPError as exc:
        detail = exc.read()[:300]
        raise VideoError(f"Daily refused {method} {path} (HTTP {exc.code}): {detail!r}") from exc
    except Exception as exc:
        raise VideoError(f"Daily unreachable: {exc}") from exc


def room_url(cs) -> str:
    """Create (or reuse) the private room for this class and return its URL."""
    end = aware(cs.starts_at) + timedelta(minutes=cs.minutes + 60)
    props = {"exp": int(end.timestamp()), "enable_chat": True, "enable_screenshare": True,
             "enable_recording": False, "enable_knocking": False, "start_video_off": False}
    try:
        return _api("GET", f"/rooms/{cs.room_name}")["url"]
    except VideoError:
        return _api("POST", "/rooms", {"name": cs.room_name, "privacy": "private", "properties": props})["url"]


def token(cs, user_name: str, owner: bool = False, observer: bool = False) -> str:
    end = aware(cs.starts_at) + timedelta(minutes=cs.minutes + 60)
    props = {"room_name": cs.room_name, "user_name": user_name, "is_owner": owner, "exp": int(end.timestamp())}
    if observer:
        props.update({"start_video_off": True, "start_audio_off": True})
    return _api("POST", "/meeting-tokens", {"properties": props})["token"]
