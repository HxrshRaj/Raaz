from __future__ import annotations

from fastapi.testclient import TestClient


class Player:
    """Thin test helper around the REST API; every call asserts on the HTTP status it expects."""

    def __init__(self, client: TestClient, name: str = "Test"):
        self.c = client
        r = client.post("/api/v1/auth/guest", json={"display_name": name})
        assert r.status_code == 201, r.text
        self.token = r.json()["access_token"]
        self.user_id = r.json()["user"]["id"]
        self.h = {"Authorization": f"Bearer {self.token}"}
        self.sid: str | None = None

    def start(self, mode: str = "standard") -> str:
        r = self.c.post("/api/v1/sessions", json={"case_id": "aakhri_gaadi", "mode": mode}, headers=self.h)
        assert r.status_code == 201, r.text
        self.sid = r.json()["id"]
        return self.sid

    def url(self, path: str) -> str:
        return f"/api/v1/sessions/{self.sid}{path}"

    def get(self, path: str, expect: int = 200):
        r = self.c.get(self.url(path), headers=self.h)
        assert r.status_code == expect, f"{path}: {r.status_code} {r.text}"
        return r.json() if r.content else None

    def post(self, path: str, body: dict | None = None, expect: int = 200, headers: dict | None = None):
        r = self.c.post(self.url(path), json=body or {}, headers={**self.h, **(headers or {})})
        assert r.status_code == expect, f"{path}: {r.status_code} {r.text}"
        return r.json() if r.content else None

    def delete(self, path: str, expect: int = 204):
        r = self.c.delete(self.url(path), headers=self.h)
        assert r.status_code == expect, f"{path}: {r.status_code} {r.text}"

    def inspect(self, loc: str, hotspot: str):
        return self.post(f"/locations/{loc}/hotspots/{hotspot}/inspect")

    def examine(self, ev: str):
        return self.post(f"/evidence/{ev}/examine")

    def talk(self, char: str, text: str, evidence: str | None = None, expect: int = 200):
        body = {"text": text}
        if evidence:
            body["evidence_key"] = evidence
        return self.post(f"/conversations/{char}/messages", body, expect=expect)

    def search_everything(self) -> None:
        """Deterministically sweep every visible hotspot (repeats until nothing new unlocks)."""
        for _ in range(6):
            progressed = False
            for loc in self.get("/locations"):
                if loc["locked"]:
                    continue
                for h in self.get(f"/locations/{loc['key']}")["hotspots"]:
                    if not h["searched"]:
                        self.inspect(loc["key"], h["key"])
                        progressed = True
            if not progressed:
                break
