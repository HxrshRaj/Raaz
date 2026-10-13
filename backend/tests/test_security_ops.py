from __future__ import annotations

import subprocess
import sys
import threading
from pathlib import Path

import pytest
from sqlalchemy import create_engine, inspect, select, text
from sqlalchemy.exc import IntegrityError

from app import db as dbmod
from app.config import get_settings
from app.jobs import submit, wait
from app.models import AuditEvent, EvidenceDiscovery, GameSession, User
from app.ratelimit import reset_limiter
from app.security import create_token, hash_password, verify_password
from tests.helpers import Player

BACKEND = Path(__file__).resolve().parent.parent


# ============================================================================ auth
def test_register_login_me_flow(client):
    body = {"email": "Case.Officer@example.com", "password": "monsoon-night-99", "display_name": "Officer"}
    r = client.post("/api/v1/auth/register", json=body)
    assert r.status_code == 201 and r.json()["user"]["is_guest"] is False
    dup = client.post("/api/v1/auth/register", json={**body, "email": "case.officer@example.com"})
    assert dup.status_code == 409 and dup.json()["error"]["code"] == "registration_failed"
    ok = client.post("/api/v1/auth/login", json={"email": body["email"], "password": body["password"]})
    assert ok.status_code == 200
    tok = ok.json()["access_token"]
    me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {tok}"})
    assert me.json()["display_name"] == "Officer"
    bad = client.post("/api/v1/auth/login", json={"email": body["email"], "password": "wrong-password"})
    assert bad.status_code == 401 and bad.json()["error"]["code"] == "invalid_credentials"
    unknown = client.post("/api/v1/auth/login", json={"email": "nobody@example.com", "password": "whatever-123"})
    assert unknown.status_code == 401 and unknown.json() == bad.json() | {"error": {**bad.json()["error"], "request_id": unknown.json()["error"]["request_id"]}}


def test_passwords_are_hashed_never_stored_plain(client):
    client.post("/api/v1/auth/register", json={"email": "h@example.com", "password": "correct-horse-battery", "display_name": "H"})
    with dbmod.SessionLocal() as db:
        u = db.scalar(select(User).where(User.email == "h@example.com"))
        assert u.password_hash and "correct-horse" not in u.password_hash and u.password_hash.startswith("$2")
    assert verify_password("correct-horse-battery", u.password_hash)
    assert not verify_password("nope", u.password_hash) and not verify_password("x", None)
    with pytest.raises(ValueError):
        hash_password("x" * 80)


def test_weak_or_malformed_registration_rejected(client):
    for body in ({"email": "not-an-email", "password": "longenough1", "display_name": "x"},
                 {"email": "a@example.com", "password": "short", "display_name": "x"},
                 {"email": "a@example.com", "password": "longenough1", "display_name": "x", "is_admin": True}):
        assert client.post("/api/v1/auth/register", json=body).status_code == 422


def test_protected_routes_need_a_valid_token(client, player: Player):
    assert client.get("/api/v1/sessions").status_code == 401
    assert client.get(player.url(""), headers={"Authorization": "Bearer garbage"}).status_code == 401
    expired = create_token(player.user_id, minutes=-5)
    assert client.get(player.url(""), headers={"Authorization": f"Bearer {expired}"}).status_code == 401
    forged = create_token(player.user_id).rsplit(".", 1)[0] + ".AAAA"
    assert client.get(player.url(""), headers={"Authorization": f"Bearer {forged}"}).status_code == 401
    r = client.get(player.url(""), headers={"Authorization": "Bearer garbage"})
    assert r.json()["error"]["code"] == "unauthenticated"


def test_player_cannot_touch_another_players_state_through_any_route(client, player: Player):
    player.inspect("carriage", "h_body")
    mallory = Player(client, "Mallory")
    mallory.sid = player.sid
    for path in ("", "/locations", "/evidence", "/evidence/ev_autopsy_prelim", "/contradictions", "/board", "/timeline",
                 "/hypotheses", "/dossiers/rohan", "/events", "/accusation/options", "/accusation/history", "/reports",
                 "/nazar", "/investigations", "/ml/leads", "/ml/anomalies", "/conversations"):
        r = client.get(mallory.url(path), headers=mallory.h)
        assert r.status_code == 404, (path, r.status_code)
    assert client.post(mallory.url("/evidence/ev_autopsy_prelim/examine"), headers=mallory.h).status_code == 404
    assert client.post(mallory.url("/accusation"), headers=mallory.h,
                       json={"culprit": "rohan", "motive": "m_ip_dispute"}).status_code == 404
    assert client.post(mallory.url("/nazar"), headers=mallory.h, json={"question": "hi"}).status_code == 404
    assert client.post(mallory.url("/board/items"), headers=mallory.h,
                       json={"kind": "note", "text": "hax"}).status_code == 404
    # ...and the owner's state is untouched
    assert [e["key"] for e in player.get("/evidence")] == ["ev_autopsy_prelim"]


def test_cannot_forge_case_truth_via_request_bodies(player: Player):
    # every body model forbids unknown fields, so solution-ish fields are rejected, not ignored
    r = player.c.post(player.url("/accusation"), headers=player.h,
                      json={"culprit": "rohan", "motive": "m_ip_dispute", "verdict": "case_closed", "score": 100})
    assert r.status_code == 422
    r = player.c.post(player.url("/contradictions/check"), headers=player.h, json={"a": "ev_x", "b": "ev_y", "force": True})
    assert r.status_code == 422


# ============================================================================ rate limiting, headers, errors
def test_rate_limit_returns_429_with_retry_after(player: Player, monkeypatch):
    monkeypatch.setattr(get_settings(), "rate_limit_per_min", 4)
    reset_limiter()
    codes = [player.c.get(player.url("/evidence"), headers=player.h).status_code for _ in range(7)]
    assert codes[:4] == [200] * 4 and 429 in codes
    r = player.c.get(player.url("/evidence"), headers=player.h)
    assert r.status_code == 429 and int(r.headers["Retry-After"]) >= 1 and r.json()["error"]["code"] == "rate_limited"


def test_login_is_ip_rate_limited(client):
    reset_limiter()
    codes = [client.post("/api/v1/auth/login", json={"email": "x@example.com", "password": "nope-nope-1"}).status_code
             for _ in range(25)]
    assert 429 in codes
    reset_limiter()


def test_security_headers_request_id_and_error_envelope(client, player: Player):
    r = client.get("/health", headers={"X-Request-ID": "abc123"})
    assert r.headers["X-Request-ID"] == "abc123" and r.headers["X-Content-Type-Options"] == "nosniff"
    assert r.headers["Cache-Control"] == "no-store"
    r = client.get(player.url("/locations/nope"), headers=player.h)
    err = r.json()["error"]
    assert r.status_code == 404 and set(err) == {"code", "message", "details", "request_id"}
    assert "Traceback" not in r.text and "sqlalchemy" not in r.text.lower()


def test_cors_is_restricted(client):
    ok = client.options("/api/v1/cases", headers={"Origin": "http://localhost:5173", "Access-Control-Request-Method": "GET"})
    assert ok.headers.get("access-control-allow-origin") == "http://localhost:5173"
    evil = client.options("/api/v1/cases", headers={"Origin": "https://evil.example", "Access-Control-Request-Method": "GET"})
    assert "access-control-allow-origin" not in evil.headers


def test_openapi_exposes_no_case_content(client):
    spec = client.get("/api/openapi.json").text.lower()
    for secret in ("pathfinder", "paperweight", "kaveri", "olive", "siding 4", "sunita"):
        assert secret not in spec


def test_audit_log_records_sensitive_actions(client, player: Player):
    player.post("/accusation", {"culprit": "tanvi", "motive": "m_exposure", "event_sequence": [], "evidence": [],
                                "contradictions": []})
    with dbmod.SessionLocal() as db:
        actions = [a.action for a in db.scalars(select(AuditEvent).where(AuditEvent.user_id == player.user_id))]
        assert "session.create" in actions and "accusation.submit" in actions and "auth.guest" in actions
        details = [a.detail for a in db.scalars(select(AuditEvent).where(AuditEvent.action == "accusation.submit"))]
        assert all("password" not in str(d).lower() for d in details)


def test_metrics_and_health_endpoints(client, player: Player):
    player.get("")
    m = client.get("/metrics").text
    assert "raaz_http_requests_total" in m and "raaz_http_request_seconds_bucket" in m
    assert client.get("/health").json() == {"status": "ok"}
    assert client.get("/ready").json()["db"] is True


# ============================================================================ database & concurrency
def test_database_constraints(player: Player):
    with dbmod.SessionLocal() as db:
        sess = db.get(GameSession, player.sid)
        assert sess is not None
        # duplicate discovery violates the primary key
        db.add(EvidenceDiscovery(session_id=sess.id, evidence_key="ev_clock_slow", case_id="aakhri_gaadi", source="t"))
        db.commit()
        db.add(EvidenceDiscovery(session_id=sess.id, evidence_key="ev_clock_slow", case_id="aakhri_gaadi", source="t"))
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()
        # evidence must exist in the catalog (composite FK)
        db.add(EvidenceDiscovery(session_id=sess.id, evidence_key="ev_not_real", case_id="aakhri_gaadi", source="t"))
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()
        # CHECK constraint
        sess.attempts = -1
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()


def test_parallel_inspections_discover_each_clue_exactly_once(player: Player):
    results: list[dict] = []
    lock = threading.Lock()

    def go():
        r = player.c.post(player.url("/locations/carriage/hotspots/h_phone/inspect"), headers=player.h)
        assert r.status_code == 200, r.text
        with lock:
            results.append(r.json())

    ts = [threading.Thread(target=go) for _ in range(10)]
    [t.start() for t in ts]
    [t.join() for t in ts]
    winners = [r for r in results if r["new_evidence"]]
    assert len(winners) == 1 and {e["key"] for e in winners[0]["new_evidence"]} == {"ev_sms_thread", "ev_call_log"}
    assert sum(len(r["already_found"]) for r in results if not r["new_evidence"]) >= 2
    keys = [e["key"] for e in player.get("/evidence")]
    assert sorted(keys) == ["ev_call_log", "ev_sms_thread"]
    assert player.get("")["actions"] >= 1  # counter updated atomically, never negative or lost entirely


def test_parallel_examine_counts_first_examination_once(player: Player):
    player.inspect("carriage", "h_body")
    firsts: list[bool] = []
    lock = threading.Lock()

    def go():
        r = player.c.post(player.url("/evidence/ev_autopsy_prelim/examine"), headers=player.h)
        with lock:
            firsts.append(r.json()["first_examination"])

    ts = [threading.Thread(target=go) for _ in range(8)]
    [t.start() for t in ts]
    [t.join() for t in ts]
    assert firsts.count(True) == 1


# ============================================================================ background jobs
def test_job_failure_is_persisted_and_reported():
    def boom():
        raise ValueError("kaboom")

    j = wait(submit("test_fail", boom, max_attempts=1))
    assert j.status == "failed" and "kaboom" in j.error and j.finished_at is not None


def test_job_retries_transient_errors_with_backoff_then_succeeds():
    calls = []

    def flaky():
        calls.append(1)
        if len(calls) < 3:
            raise TimeoutError("slow upstream")
        return {"ok": True}

    j = wait(submit("test_flaky", flaky, max_attempts=4, base_delay=0.01))
    assert j.status == "succeeded" and j.attempts == 3 and j.result == {"ok": True}


def test_job_gives_up_after_bounded_retries():
    calls = []

    def always():
        calls.append(1)
        raise ConnectionError("down")

    j = wait(submit("test_down", always, max_attempts=3, base_delay=0.01))
    assert j.status == "failed" and len(calls) == 3 and j.attempts == 3


def test_non_transient_errors_are_not_retried():
    calls = []

    def bad():
        calls.append(1)
        raise ValueError("deterministic bug")

    wait(submit("test_bug", bad, max_attempts=5, base_delay=0.01))
    assert len(calls) == 1


# ============================================================================ migrations
def test_alembic_migration_matches_models(tmp_path):
    url = f"sqlite:///{(tmp_path / 'mig.db').as_posix()}"
    env = {**__import__("os").environ, "RAAZ_DATABASE_URL": url}
    r = subprocess.run([sys.executable, "-m", "alembic", "upgrade", "head"], cwd=BACKEND, env=env, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr[-800:]
    insp = inspect(create_engine(url))
    migrated = set(insp.get_table_names()) - {"alembic_version"}
    assert migrated == set(dbmod.Base.metadata.tables), migrated ^ set(dbmod.Base.metadata.tables)
    # a second autogenerate against the migrated DB should detect no drift
    r2 = subprocess.run([sys.executable, "-m", "alembic", "check"], cwd=BACKEND, env=env, capture_output=True, text=True)
    assert r2.returncode == 0, r2.stdout[-500:] + r2.stderr[-500:]
    eng = create_engine(url)
    with eng.connect() as c:
        c.execute(text("select 1"))
