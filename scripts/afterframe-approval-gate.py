
#!/usr/bin/env python3
import json
import sys
from pathlib import Path

def fail(message):
    print(f"APPROVAL GATE: BLOCKED — {message}", file=sys.stderr)
    raise SystemExit(2)

try:
    plan = json.loads(Path("scene-plan.json").read_text(encoding="utf-8"))
    approval = json.loads(Path("visual-approval.json").read_text(encoding="utf-8"))
except Exception as exc:
    fail(f"invalid or missing JSON: {exc}")

title = plan.get("episode_title")
if not isinstance(title, str) or not title.strip():
    fail("scene plan has no episode_title")

if approval.get("episode_title") != title:
    fail("approval episode_title does not match the current scene plan")

items = approval.get("shots")
if not isinstance(items, list) or len(items) != 10:
    fail("approval manifest must contain exactly 10 shot records")

approved_numbers = set()

for item in items:
    if not isinstance(item, dict):
        fail("each shot approval must be an object")

    number = item.get("shot_number")

    if not isinstance(number, int) or number < 1 or number > 10:
        fail("shot_number must be an integer from 1 to 10")

    if number in approved_numbers:
        fail(f"duplicate approval for shot {number}")

    approved_numbers.add(number)

    if item.get("approved") is not True:
        fail(f"shot {number} has not been approved")

if approved_numbers != set(range(1, 11)):
    fail("approvals must cover shots 1 through 10")

print(
    f"APPROVAL GATE: PASSED — all 10 keyframes marked approved for: {title}"
)
