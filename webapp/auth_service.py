from __future__ import annotations

import hashlib
import hmac
import json
import re
import secrets
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from typing import Any, Dict, List, Optional

from webapp.auth_storage import AuthStore


USERNAME_PATTERN = re.compile(r"^[A-Za-z0-9_]{3,32}$")
PASSWORD_MIN_LENGTH = 6
TOKEN_TTL_HOURS = 24
PBKDF2_ROUNDS = 200_000


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _to_iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _from_iso(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _parse_created_at(value: Any) -> Optional[datetime]:
    text = str(value or "").strip()
    if not text:
        return None

    # ISO style timestamps
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        pass

    # Legacy timestamp style used by inference service
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M:%S.%f"):
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    return None


class AuthService:
    def __init__(self, store: Optional[AuthStore] = None) -> None:
        self.store = store or AuthStore()

    def bootstrap_status(self) -> Dict[str, Any]:
        user_count = self.store.count_users()
        return {
            "user_count": user_count,
            "needs_setup": user_count == 0,
        }

    def register(
        self,
        username: str,
        password: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> Dict[str, Any]:
        normalized_username = self._normalize_username(username)
        self._validate_password(password)

        if self.store.get_user_by_username(normalized_username) is not None:
            raise ValueError("Username already exists.")

        now = _utc_now()
        password_salt = secrets.token_hex(16)
        password_hash = self._hash_password(password, password_salt)

        user = self.store.create_user(
            username=normalized_username,
            password_hash=password_hash,
            password_salt=password_salt,
            created_at=_to_iso(now),
        )
        session = self._create_session(
            user_id=int(user["id"]),
            ip_address=ip_address,
            user_agent=user_agent,
            now=now,
        )

        return {
            "token": session["token"],
            "token_type": "Bearer",
            "expires_at": session["expires_at"],
            "user": self._public_user(user),
        }

    def login(
        self,
        username: str,
        password: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> Dict[str, Any]:
        normalized_username = self._normalize_username(username)
        user = self.store.get_user_by_username(normalized_username)
        if user is None:
            raise ValueError("Username or password is invalid.")

        expected_hash = user.get("password_hash")
        salt = user.get("password_salt")
        if not expected_hash or not salt:
            raise ValueError("User password metadata is invalid.")

        candidate_hash = self._hash_password(password, str(salt))
        if not hmac.compare_digest(str(expected_hash), candidate_hash):
            raise ValueError("Username or password is invalid.")

        now = _utc_now()
        self.store.touch_last_login(int(user["id"]), _to_iso(now))
        session = self._create_session(
            user_id=int(user["id"]),
            ip_address=ip_address,
            user_agent=user_agent,
            now=now,
        )

        user = self.store.get_user_by_id(int(user["id"]))
        if user is None:
            raise ValueError("User was removed unexpectedly.")

        return {
            "token": session["token"],
            "token_type": "Bearer",
            "expires_at": session["expires_at"],
            "user": self._public_user(user),
        }

    def authenticate_token(self, token: str) -> Optional[Dict[str, Any]]:
        token = (token or "").strip()
        if not token:
            return None

        token_hash = self._hash_token(token)
        session = self.store.get_session_by_token_hash(token_hash)
        if session is None:
            return None

        if int(session.get("revoked", 0)) == 1:
            return None

        expires_at = str(session.get("expires_at", ""))
        if not expires_at:
            return None

        if _from_iso(expires_at) <= _utc_now():
            self.store.revoke_session(token_hash)
            return None

        user = {
            "id": int(session["user_id"]),
            "username": str(session["username"]),
            "created_at": session.get("user_created_at"),
            "updated_at": session.get("user_updated_at"),
            "last_login_at": session.get("last_login_at"),
        }
        return user

    def logout(self, token: str) -> None:
        token_hash = self._hash_token(token)
        self.store.revoke_session(token_hash)

    def change_password(self, user_id: int, old_password: str, new_password: str) -> None:
        user = self.store.get_user_by_id(user_id)
        if user is None:
            raise ValueError("User does not exist.")

        self._validate_password(new_password)

        old_hash = self._hash_password(old_password, str(user["password_salt"]))
        if not hmac.compare_digest(str(user["password_hash"]), old_hash):
            raise ValueError("Old password is incorrect.")

        if old_password == new_password:
            raise ValueError("New password must be different from the old password.")

        new_salt = secrets.token_hex(16)
        new_hash = self._hash_password(new_password, new_salt)
        now_iso = _to_iso(_utc_now())

        self.store.update_password(
            user_id=user_id,
            password_hash=new_hash,
            password_salt=new_salt,
            updated_at=now_iso,
        )
        self.store.revoke_sessions_for_user(user_id)

    def log_inference_activity(self, user_id: int, response_payload: Dict[str, Any]) -> None:
        summary = response_payload.get("summary", {}) or {}
        self.store.add_inference_audit(
            user_id=user_id,
            task_type=str(response_payload.get("task_type") or "unknown"),
            source_name=str(response_payload.get("source_name") or ""),
            model_id=str(response_payload.get("model_id") or ""),
            model_label=str(response_payload.get("model_label") or ""),
            detection_count=int(summary.get("detection_count", 0) or 0),
            latency_seconds=float(summary.get("latency_seconds", 0.0) or 0.0),
            record_id=str(response_payload.get("id") or ""),
            summary_json=json.dumps(summary, ensure_ascii=False),
            created_at=str(response_payload.get("created_at") or _to_iso(_utc_now())),
        )

    def list_my_activity(self, user_id: int, limit: int = 50) -> List[Dict[str, Any]]:
        records = self.store.list_inference_audit(user_id=user_id, limit=limit)
        output: List[Dict[str, Any]] = []
        for item in records:
            summary_raw = item.get("summary_json")
            try:
                summary = json.loads(summary_raw) if summary_raw else {}
            except json.JSONDecodeError:
                summary = {}
            output.append(
                {
                    "id": item.get("id"),
                    "task_type": item.get("task_type"),
                    "source_name": item.get("source_name"),
                    "model_id": item.get("model_id"),
                    "model_label": item.get("model_label"),
                    "detection_count": item.get("detection_count"),
                    "latency_seconds": item.get("latency_seconds"),
                    "record_id": item.get("record_id"),
                    "created_at": item.get("created_at"),
                    "summary": summary,
                }
            )
        return output

    def model_performance_summary(self, user_id: int, limit: int = 500) -> List[Dict[str, Any]]:
        records = self.store.list_inference_audit(user_id=user_id, limit=limit)
        grouped: Dict[str, Dict[str, Any]] = {}

        for item in records:
            model_id = str(item.get("model_id") or "")
            model_label = str(item.get("model_label") or "")
            model_key = model_label or model_id or "unknown_model"
            summary_raw = item.get("summary_json")
            try:
                summary = json.loads(summary_raw) if summary_raw else {}
            except json.JSONDecodeError:
                summary = {}

            fps_value = float(summary.get("fps", 0.0) or 0.0)
            pipeline_ms_value = float(summary.get("pipeline_ms", 0.0) or 0.0)
            latency_value = float(item.get("latency_seconds") or 0.0)
            detections_value = int(item.get("detection_count") or 0)
            created_at = str(item.get("created_at") or "")
            created_at_dt = _parse_created_at(created_at)

            if model_key not in grouped:
                grouped[model_key] = {
                    "model_id": model_id,
                    "model_label": model_label or model_id or "unknown_model",
                    "run_count": 0,
                    "total_detections": 0,
                    "avg_latency_seconds": 0.0,
                    "avg_fps": 0.0,
                    "avg_pipeline_ms": 0.0,
                    "first_run_at": created_at,
                    "last_run_at": created_at,
                    "recent_run_times": [],
                    "_latency_sum": 0.0,
                    "_fps_sum": 0.0,
                    "_pipeline_ms_sum": 0.0,
                    "_first_run_dt": created_at_dt,
                    "_last_run_dt": created_at_dt,
                }

            model_stats = grouped[model_key]
            if not model_stats.get("model_id") and model_id:
                model_stats["model_id"] = model_id
            if (not model_stats.get("model_label") or model_stats.get("model_label") == "unknown_model") and model_label:
                model_stats["model_label"] = model_label

            model_stats["run_count"] += 1
            model_stats["total_detections"] += detections_value
            model_stats["_latency_sum"] += latency_value
            model_stats["_fps_sum"] += fps_value
            model_stats["_pipeline_ms_sum"] += pipeline_ms_value

            if created_at:
                recent_times = model_stats["recent_run_times"]
                if created_at not in recent_times and len(recent_times) < 5:
                    recent_times.append(created_at)

            first_dt = model_stats.get("_first_run_dt")
            last_dt = model_stats.get("_last_run_dt")
            if created_at_dt is not None:
                if first_dt is None or created_at_dt < first_dt:
                    model_stats["_first_run_dt"] = created_at_dt
                    model_stats["first_run_at"] = created_at
                if last_dt is None or created_at_dt > last_dt:
                    model_stats["_last_run_dt"] = created_at_dt
                    model_stats["last_run_at"] = created_at
            else:
                if not model_stats.get("first_run_at"):
                    model_stats["first_run_at"] = created_at
                if not model_stats.get("last_run_at"):
                    model_stats["last_run_at"] = created_at

        output: List[Dict[str, Any]] = []
        for stats in grouped.values():
            run_count = max(int(stats["run_count"]), 1)
            stats["avg_latency_seconds"] = round(float(stats["_latency_sum"]) / run_count, 3)
            stats["avg_fps"] = round(float(stats["_fps_sum"]) / run_count, 2)
            stats["avg_pipeline_ms"] = round(float(stats["_pipeline_ms_sum"]) / run_count, 2)
            stats.pop("_latency_sum", None)
            stats.pop("_fps_sum", None)
            stats.pop("_pipeline_ms_sum", None)
            stats.pop("_first_run_dt", None)
            stats.pop("_last_run_dt", None)
            output.append(stats)

        output.sort(key=lambda item: (item["run_count"], item.get("last_run_at", "")), reverse=True)
        return output

    def cleanup_sessions(self) -> int:
        return self.store.purge_expired_sessions(_to_iso(_utc_now()))

    def _normalize_username(self, username: str) -> str:
        candidate = (username or "").strip()
        if not USERNAME_PATTERN.fullmatch(candidate):
            raise ValueError("Username must be 3-32 chars and can only include letters, numbers, and underscore.")
        return candidate

    def _validate_password(self, password: str) -> None:
        if len(password or "") < PASSWORD_MIN_LENGTH:
            raise ValueError(f"Password must be at least {PASSWORD_MIN_LENGTH} characters.")

    def _hash_password(self, password: str, salt: str) -> str:
        value = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            bytes.fromhex(salt),
            PBKDF2_ROUNDS,
        )
        return value.hex()

    def _make_token(self) -> str:
        return secrets.token_urlsafe(48)

    def _hash_token(self, token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    def _create_session(
        self,
        user_id: int,
        ip_address: Optional[str],
        user_agent: Optional[str],
        now: datetime,
    ) -> Dict[str, str]:
        token = self._make_token()
        expires_at = now + timedelta(hours=TOKEN_TTL_HOURS)
        self.store.create_session(
            user_id=user_id,
            token_hash=self._hash_token(token),
            created_at=_to_iso(now),
            expires_at=_to_iso(expires_at),
            ip_address=ip_address,
            user_agent=user_agent,
        )
        return {
            "token": token,
            "expires_at": _to_iso(expires_at),
        }

    def _public_user(self, user: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "id": int(user["id"]),
            "username": str(user["username"]),
            "created_at": user.get("created_at"),
            "updated_at": user.get("updated_at"),
            "last_login_at": user.get("last_login_at"),
        }


@lru_cache(maxsize=1)
def get_auth_service() -> AuthService:
    return AuthService()
