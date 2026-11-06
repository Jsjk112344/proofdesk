"""Server-owned recurring Mountain Time schedule, bounded by session and run quotas."""

from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from ..execution.controller import now
from ..execution.runner import RunError


def next_due(at=None):
    current = (at or datetime.now(UTC)).astimezone(ZoneInfo("America/Denver"))
    due = current.replace(hour=2, minute=0, second=0, microsecond=0)
    if due <= current:
        due += timedelta(days=1)
    # Normalize a spring-forward nonexistent local time to the next valid instant.
    return due.astimezone(UTC).isoformat()


def set_schedule(store, owner, enabled):
    if type(enabled) is not bool:
        raise RunError("invalid_schedule")
    with store.transaction() as conn:
        store.group(conn, owner)
        conn.execute(
            "INSERT INTO dealer_schedules VALUES(?,?,?,?,NULL) ON CONFLICT(owner) "
            "DO UPDATE SET enabled=excluded.enabled,next_due=excluded.next_due,"
            "expires_at=excluded.expires_at,last_error=NULL",
            (
                owner,
                int(enabled),
                next_due() if enabled else None,
                (datetime.now(UTC) + timedelta(days=1)).isoformat(),
            ),
        )
        return dict(
            conn.execute("SELECT * FROM dealer_schedules WHERE owner=?", (owner,)).fetchone()
        )


def dispatch_due(store):
    import os

    with store.reading() as conn:
        rows = [
            dict(r)
            for r in conn.execute(
                "SELECT * FROM dealer_schedules WHERE enabled=1 AND next_due<=?", (now(),)
            )
        ]
    for row in rows:
        error = None
        try:
            if row["expires_at"] < now():
                raise RunError("session_schedule_expired")
            mode = (
                "live_model"
                if os.environ.get("PROOFDESK_PUBLIC_DEMO") == "1"
                or os.environ.get("SALESDESK_DEALER_LIVE_PLANS")
                else "deterministic"
            )
            # Stable request identity across restarts around dispatch.
            from ..execution.artifacts import sha256

            store.start_review(
                row["owner"], sha256((row["owner"] + row["next_due"]).encode())[:32], mode=mode
            )
        except RunError as exc:
            error = exc.reason
        with store.transaction() as conn:
            conn.execute(
                "UPDATE dealer_schedules SET enabled=?,next_due=?,last_error=? WHERE owner=?",
                (int(error is None), None if error else row["next_due"], error, row["owner"]),
            )
