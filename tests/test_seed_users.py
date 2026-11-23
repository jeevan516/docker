import importlib.util
import sys

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("seed_users", ROOT / "scripts" / "seed_users.py")
seed_users = importlib.util.module_from_spec(spec)
spec.loader.exec_module(seed_users)


def test_make_users_is_deterministic():
    assert seed_users.make_users(20, seed=42) == seed_users.make_users(20, seed=42)
    assert seed_users.make_users(20, seed=42) != seed_users.make_users(20, seed=7)


def test_make_users_have_unique_emails_on_reserved_domains():
    users = seed_users.make_users(200, seed=1)
    emails = [u["email"] for u in users]
    assert len(set(emails)) == 200
    assert all(e.rsplit("@", 1)[1] in seed_users.DOMAINS for e in emails)
    assert all(e == e.lower() for e in emails)
    assert all(len(u["name"].split()) == 2 for u in users)


def through_test_client(client):
    def post_user(base_url, user):
        assert base_url == "http://api.test"
        return client.post("/users", json=user).status_code

    return post_user


def test_main_seeds_then_skips_existing_users(client, monkeypatch, capsys):
    monkeypatch.setattr(seed_users, "post_user", through_test_client(client))
    monkeypatch.setattr(sys, "argv", ["seed_users.py", "--count", "5", "--url", "http://api.test/"])

    assert seed_users.main() == 0
    assert "Created 5, skipped 0 existing, failed 0" in capsys.readouterr().out
    assert len(client.get("/users").json()) == 5

    assert seed_users.main() == 0
    assert "Created 0, skipped 5 existing, failed 0" in capsys.readouterr().out


def test_main_reports_failures(monkeypatch, capsys):
    monkeypatch.setattr(seed_users, "post_user", lambda url, user: 500)
    monkeypatch.setattr(sys, "argv", ["seed_users.py", "--count", "2"])
    assert seed_users.main() == 1
    captured = capsys.readouterr()
    assert "failed 2" in captured.out
    assert "Failed (500)" in captured.err
