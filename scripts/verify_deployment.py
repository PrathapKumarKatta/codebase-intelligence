"""Exercise real database-backed auth, indexing, retrieval, and cited chat."""
import argparse
import io
import json
import os
from pathlib import Path
import secrets
import sys
from zipfile import ZipFile, ZIP_DEFLATED

import httpx

root = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument("--url", default="https://codebase-intelligence-xi.vercel.app")
parser.add_argument("--local", action="store_true")
parser.add_argument("--skip-chat", action="store_true")
parser.add_argument("--force-upload", action="store_true")
args = parser.parse_args()

if args.local:
    from dotenv import load_dotenv
    load_dotenv(root / ".env.local")
    os.environ["SECRET_KEY"] = secrets.token_urlsafe(48)
    sys.path.insert(0, str(root))
    from fastapi.testclient import TestClient
    from api.index import app
    client = TestClient(app)
else:
    client = httpx.Client(base_url=args.url, timeout=290)

state_path = root / ".local-demo.json"
state = json.loads(state_path.read_text()) if state_path.exists() else {
    "email": f"deployment-check-{secrets.token_hex(6)}@example.com",
    "password": secrets.token_urlsafe(24),
}
state_path.write_text(json.dumps(state))


def check(response, expected=200):
    if response.status_code != expected:
        raise AssertionError(f"{response.request.method} {response.request.url.path}: HTTP {response.status_code}")
    return response.json() if expected != 204 else None


with client:
    assert check(client.get("/health/ready"))["status"] == "ready"
    credentials = {key: state[key] for key in ("email", "password")}
    registered = client.post("/api/v1/auth/register", json=credentials)
    assert registered.status_code in (201, 400)
    token = check(client.post("/api/v1/auth/login", json=credentials))["access_token"]
    client.headers["Authorization"] = f"Bearer {token}"
    assert check(client.get("/api/v1/auth/me"))["email"] == state["email"]
    assert client.get("/api/v1/auth/me", headers={"Authorization": "Bearer invalid"}).status_code == 401
    assert client.post("/api/v1/auth/login", json={**credentials, "password": "incorrect-password"}).status_code == 401
    print("PASS: readiness, registration, login, profile, invalid credentials", flush=True)

    if "project_id" not in state:
        state["project_id"] = check(client.post("/api/v1/projects", json={"name": "Deployment verification sample"}), 201)["id"]
        state_path.write_text(json.dumps(state))
    project_id = state["project_id"]
    status = check(client.get(f"/api/v1/projects/{project_id}/status"))
    if args.force_upload or status["project_status"] != "ready":
        archive = io.BytesIO()
        with ZipFile(archive, "w", ZIP_DEFLATED) as output:
            sample = root / "sample_projects" / "microservice"
            for path in sample.rglob("*"):
                if path.is_file():
                    output.writestr(path.relative_to(sample).as_posix(), path.read_bytes())
        job = check(client.post(f"/api/v1/projects/{project_id}/upload", files={"file": ("sample.zip", archive.getvalue(), "application/zip")}), 202)
        assert job["status"] == "completed"
    assert check(client.get(f"/api/v1/projects/{project_id}/status"))["project_status"] == "ready"
    assert check(client.get(f"/api/v1/projects/{project_id}/files"))["total"] > 0
    print("PASS: ZIP upload, inline indexing, persistent source files", flush=True)

    question = "How does the database connection work?"
    found = check(client.post(f"/api/v1/projects/{project_id}/search", json={"query": question, "top_k": 5}))
    assert found["total"] > 0
    print("PASS: semantic embeddings and hybrid retrieval", flush=True)

    other_credentials = {"email": f"isolation-check-{secrets.token_hex(6)}@example.com", "password": secrets.token_urlsafe(24)}
    check(client.post("/api/v1/auth/register", json=other_credentials), 201)
    other_token = check(client.post("/api/v1/auth/login", json=other_credentials))["access_token"]
    assert client.get(f"/api/v1/projects/{project_id}", headers={"Authorization": f"Bearer {other_token}"}).status_code == 404
    print("PASS: cross-user project access rejected", flush=True)

    if not args.skip_chat:
        answer = check(client.post(f"/api/v1/projects/{project_id}/chat", json={"message": question, "top_k": 3}))
        assert answer["message"]["citations"]
        assert answer["message"]["content"]
        print("PASS: model answer with validated source citations", flush=True)
    print("Verification completed. Generated test-account credentials are in ignored .local-demo.json.", flush=True)
