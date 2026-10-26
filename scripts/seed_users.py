"""Load synthetic users into the running API.

Users are created through ``POST /users`` so every row passes the same
validation and duplicate-email checks as a real request. The output is
deterministic for a given ``--seed``, so re-running skips existing users.

Usage:
    uv run python scripts/seed_users.py [--count 50] [--seed 42] [--url URL]
"""

import argparse
import json
import random
import sys
import urllib.error
import urllib.request

FIRST_NAMES = [
    "Aarav", "Amara", "Ana", "Chen", "Diego", "Elena", "Fatima", "Hiro",
    "Ines", "Jamal", "Kofi", "Lena", "Liam", "Maya", "Mateo", "Noah",
    "Olga", "Priya", "Ravi", "Sara", "Sofia", "Tariq", "Yara", "Zoe",
]
LAST_NAMES = [
    "Adeyemi", "Berg", "Costa", "Dubois", "Garcia", "Haddad", "Ivanova",
    "Kim", "Kowalski", "Lopez", "Mensah", "Nakamura", "Novak", "Okafor",
    "Patel", "Rossi", "Schmidt", "Silva", "Singh", "Tanaka", "Wang", "Yilmaz",
]
# Reserved example domains (RFC 2606) so no real mailbox is ever targeted.
DOMAINS = ["example.com", "example.org", "example.net"]


def make_users(count: int, seed: int) -> list[dict[str, str]]:
    """Return ``count`` synthetic users with unique email addresses."""
    rng = random.Random(seed)
    users = []
    for i in range(1, count + 1):
        first = rng.choice(FIRST_NAMES)
        last = rng.choice(LAST_NAMES)
        # The index suffix keeps emails unique even when names repeat.
        email = f"{first}.{last}{i}@{rng.choice(DOMAINS)}".lower()
        users.append({"name": f"{first} {last}", "email": email})
    return users


def post_user(base_url: str, user: dict[str, str]) -> int:
    """Create one user and return the HTTP status code."""
    request = urllib.request.Request(
        f"{base_url}/users",
        data=json.dumps(user).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            return response.status
    except urllib.error.HTTPError as exc:
        return exc.code


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--count", type=int, default=50)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--url", default="http://localhost:8000")
    args = parser.parse_args()

    created = skipped = failed = 0
    for user in make_users(args.count, args.seed):
        code = post_user(args.url.rstrip("/"), user)
        if code == 201:
            created += 1
        elif code == 409:
            skipped += 1  # Already loaded by an earlier run.
        else:
            failed += 1
            print(f"Failed ({code}): {user}", file=sys.stderr)

    print(f"Created {created}, skipped {skipped} existing, failed {failed}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
