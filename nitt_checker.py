import requests
import re
import os
import json

USERNAME         = "210125023@nitt.edu"   # ← your NITT email
PASSWORD         = "Hemanth@10"           # ← your webmail password
PUSHBULLET_TOKEN = "o.Eyl1jAabAIBYoN1CE6yjQcYN7EMOe0nm" 

WEBMAIL_URL = "https://students.nitt.edu/rcmail/"
STATE_FILE  = os.path.join(os.path.dirname(os.path.abspath(__file__)), "last_count.txt")


def load_last_count() -> int:
    try:
        with open(STATE_FILE) as f:
            return int(f.read().strip())
    except Exception:
        return -1


def save_count(count: int):
    with open(STATE_FILE, "w") as f:
        f.write(str(count))


def get_session() -> requests.Session:
    s = requests.Session()
    s.headers["User-Agent"] = "Mozilla/5.0 (NITT-Notifier)"

    r = s.get(WEBMAIL_URL, timeout=20)
    r.raise_for_status()

    token = ""
    for pat in [r'name="_token"\s+value="([^"]+)"', r'"request_token"\s*:\s*"([^"]+)"']:
        m = re.search(pat, r.text)
        if m:
            token = m.group(1)
            break

    r = s.post(WEBMAIL_URL, data={
        "_task":   "login",
        "_action": "login",
        "_token":  token,
        "_user":   USERNAME,
        "_pass":   PASSWORD,
    }, timeout=20)
    r.raise_for_status()

    if "logout" not in r.text.lower():
        raise RuntimeError("Login failed — check NITT_USERNAME and NITT_PASSWORD secrets.")

    print("[OK] Logged in.")
    return s


def fetch_unread_count(s: requests.Session) -> int:
    """
    Calls Roundcube's getunread API.
    Response looks like:
      {"action":"getunread","exec":"this.set_unread_count(\"INBOX\",174,true);..."}
    The count is inside the exec string — we extract it with a regex.
    """
    r = s.get(
        WEBMAIL_URL + "?_task=mail&_action=getunread&_remote=1&_mbox=INBOX",
        timeout=15
    )
    r.raise_for_status()
    data = r.json()
    exec_str = data.get("exec", "")

    # e.g.  this.set_unread_count("INBOX",174,true);
    m = re.search(r'set_unread_count\("INBOX"\s*,\s*(\d+)', exec_str)
    if m:
        count = int(m.group(1))
        print(f"[OK] Unread count: {count}")
        return count

    print(f"[!] Could not parse unread count from exec string: {exec_str[:200]}")
    return 0


def pushbullet_push(title: str, body: str):
    r = requests.post(
        "https://api.pushbullet.com/v2/pushes",
        headers={
            "Access-Token": PUSHBULLET_TOKEN,
            "Content-Type": "application/json",
        },
        data=json.dumps({"type": "note", "title": title, "body": body}),
        timeout=12,
    )
    r.raise_for_status()
    print("[OK] Pushbullet notification sent.")


def main():
    if not USERNAME or not PASSWORD or not PUSHBULLET_TOKEN:
        raise RuntimeError(
            "Missing env vars — set NITT_USERNAME, NITT_PASSWORD, PUSHBULLET_TOKEN "
            "as GitHub Secrets (see setup guide)."
        )

    last    = load_last_count()
    session = get_session()
    current = fetch_unread_count(session)

    print(f"[i] Last known: {last}  |  Current: {current}")

    if last == -1:
        print(f"[INIT] First run — baseline set to {current} unread.")
        save_count(current)
        return

    if current > last:
        new = current - last
        msg = (f"{new} new message{'s' if new > 1 else ''}! "
               f"You now have {current} unread in your NITT inbox.")
        print(f"[NOTIFY] {msg}")
        pushbullet_push("📬 NITT Mail", msg)
    else:
        print(f"[NO CHANGE] Still {current} unread.")

    save_count(current)


if __name__ == "__main__":
    main()