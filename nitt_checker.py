import requests
import re
import os
import json
import html
import sys

# ── FILL THESE FOR LOCAL TESTING (clear before uploading to GitHub) ───────────
USERNAME         = "210125023@nitt.edu"   # ← your NITT email
PASSWORD         = "Hemanth@10"           # ← your webmail password
PUSHBULLET_TOKEN = "o.Eyl1jAabAIBYoN1CE6yjQcYN7EMOe0nm"
# ─────────────────────────────────────────────────────────────────────────────

WEBMAIL_URL = "https://students.nitt.edu/rcmail/"
STATE_FILE  = os.path.join(os.path.dirname(os.path.abspath(__file__)), "seen_uids.json")


# ── State helpers ─────────────────────────────────────────────────────────────

def load_seen_uids():
    try:
        with open(STATE_FILE) as f:
            return set(json.load(f))
    except Exception:
        return None  # None = first ever run

def save_seen_uids(uids: set):
    with open(STATE_FILE, "w") as f:
        json.dump(sorted(list(uids)), f)


# ── Login ─────────────────────────────────────────────────────────────────────

def get_session() -> requests.Session:
    s = requests.Session()
    s.headers["User-Agent"] = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"

    # Load login page to grab CSRF token
    r = s.get(WEBMAIL_URL, timeout=20)
    r.raise_for_status()

    token = ""
    for pat in [r'name="_token"\s+value="([^"]+)"',
                r'"request_token"\s*:\s*"([^"]+)"']:
        m = re.search(pat, r.text)
        if m:
            token = m.group(1)
            break

    # Submit login
    r = s.post(WEBMAIL_URL, data={
        "_task":   "login",
        "_action": "login",
        "_token":  token,
        "_user":   USERNAME,
        "_pass":   PASSWORD,
    }, timeout=20)
    r.raise_for_status()

    if "logout" not in r.text.lower():
        raise RuntimeError("Login failed — check your USERNAME and PASSWORD.")

    print("[OK] Logged in successfully.")
    return s


# ── Fetch inbox list ──────────────────────────────────────────────────────────

def fetch_inbox(s: requests.Session, page: int = 1):
    """Returns (list_of_messages, total_count)."""
    r = s.get(
        WEBMAIL_URL + f"?_task=mail&_action=list&_mbox=INBOX&_remote=1&_page={page}",
        timeout=20
    )
    r.raise_for_status()
    data  = r.json()
    total = data.get("env", {}).get("messagecount", 0)
    msgs  = []

    for match in re.finditer(
        r'this\.add_message_row\((\d+),(\{.*?\}),(\{.*?\}),',
        data.get("exec", ""), re.DOTALL
    ):
        uid = int(match.group(1))
        try:
            meta  = json.loads(match.group(2))
            flags = json.loads(match.group(3))
        except Exception:
            continue

        fromto = meta.get("fromto", "")
        em = re.search(r'title="([^"]+)"', fromto)
        nm = re.search(r'class="rcmContactAddress">([^<]+)<', fromto)
        sender_email = em.group(1) if em else ""
        sender_name  = html.unescape(nm.group(1)).strip() if nm else sender_email

        msgs.append({
            "uid":          uid,
            "subject":      html.unescape(meta.get("subject", "(no subject)")),
            "sender_name":  sender_name,
            "sender_email": sender_email,
            "date":         meta.get("date", ""),
            "seen":         bool(flags.get("seen", False)),
        })

    return msgs, total


# ── Fetch body ────────────────────────────────────────────────────────────────

def fetch_body(s: requests.Session, uid: int, max_chars: int = 400) -> str:
    """
    Roundcube's ?_action=get&_part=1 returns the raw plain-text body directly.
    We try part 1, 1.1, and 2 in order — whichever gives readable text first.
    """
    for part in ["1", "1.1", "2"]:
        try:
            r = s.get(
                WEBMAIL_URL
                + f"?_task=mail&_action=get&_uid={uid}&_mbox=INBOX&_part={part}",
                timeout=15
            )
            if r.status_code != 200:
                continue
            text = r.text.strip()
            if not text or len(text) < 20:
                continue
            # Skip if what came back is JSON or JavaScript
            if text.startswith("{") or text.startswith("this."):
                continue
            # Strip HTML tags if present
            if "<" in text:
                text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL)
                text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.DOTALL)
                text = re.sub(r'<[^>]+>', ' ', text)
            text = html.unescape(text)
            text = re.sub(r'[ \t]+', ' ', text)          # collapse spaces
            text = re.sub(r'\n{3,}', '\n\n', text).strip()  # max 2 blank lines
            if len(text) > 30:
                return text[:max_chars] + ("…" if len(text) > max_chars else "")
        except Exception:
            continue

    return "(body preview not available)"


# ── Pushbullet ────────────────────────────────────────────────────────────────

def push(title: str, body: str):
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
    print("  [OK] Notification sent to phone.")


def notify(s: requests.Session, msg: dict):
    print(f"  → Fetching body for UID {msg['uid']}: {msg['subject'][:55]}")
    preview = fetch_body(s, msg["uid"])
    sender  = msg["sender_name"] or msg["sender_email"]

    title = f"📬 {sender}"
    body  = (
        f"✉  {msg['subject']}\n"
        f"👤 {msg['sender_email']}\n"
        f"🕐 {msg['date']}\n"
        f"{'─' * 32}\n"
        f"{preview}"
    )
    push(title, body)


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    args = sys.argv[1:]

    # --test: verify Pushbullet connection
    if "--test" in args:
        print("[TEST] Sending test ping to your phone...")
        push(
            "📬 NITT Mail — Test",
            "✅ Connection working!\nYou will get notified here when new mail arrives."
        )
        print("[TEST] Done. Check your phone now.")
        return

    # --reset: wipe saved state
    if "--reset" in args:
        if os.path.exists(STATE_FILE):
            os.remove(STATE_FILE)
            print("[RESET] seen_uids.json deleted. Next run sets a fresh baseline.")
        else:
            print("[RESET] No state file found — nothing to clear.")
        return

    # --preview N: immediately push latest N unread mails to phone
    if "--preview" in args:
        try:
            n = int(args[args.index("--preview") + 1])
        except (IndexError, ValueError):
            n = 3
        print(f"[PREVIEW] Fetching {n} latest unread mail(s)...")
        session     = get_session()
        msgs, total = fetch_inbox(session)
        unread      = [m for m in msgs if not m["seen"]][:n]
        if not unread:
            print("[PREVIEW] No unread mails found on page 1.")
        else:
            for msg in unread:
                notify(session, msg)
            print(f"[PREVIEW] {len(unread)} notification(s) sent. Check your phone!")
        return

    # ── Normal scheduled run ──────────────────────────────────────────────────
    seen      = load_seen_uids()
    session   = get_session()
    msgs, total = fetch_inbox(session)
    now_uids  = {m["uid"] for m in msgs}

    # First ever run — save baseline, no notifications
    if seen is None:
        save_seen_uids(now_uids)
        print(f"[INIT] Baseline saved ({len(now_uids)} UIDs, {total} total in inbox).")
        print(f"[INIT] Watching for new mail from now on.")
        return

    new_uids = sorted(now_uids - seen, reverse=True)  # newest first

    if not new_uids:
        print(f"[OK] No new mail. (Inbox: {total} messages)")
        save_seen_uids(seen | now_uids)
        return

    print(f"[NEW] {len(new_uids)} new message(s) detected!")
    lookup = {m["uid"]: m for m in msgs}
    for uid in new_uids:
        if uid in lookup:
            notify(session, lookup[uid])

    save_seen_uids(seen | now_uids)
    print(f"[DONE] {len(new_uids)} notification(s) pushed.")


if __name__ == "__main__":
    main()
