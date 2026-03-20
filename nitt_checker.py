import requests
import re
import os
import json
import html
import sys

USERNAME         = os.environ.get("NITT_USERNAME",   "")
PASSWORD         = os.environ.get("NITT_PASSWORD",   "")
PUSHBULLET_TOKEN = os.environ.get("PUSHBULLET_TOKEN","")
# ─────────────────────────────────────────────────────────────────────────────

WEBMAIL_URL = "https://students.nitt.edu/rcmail/"

STATE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "seen_uids.json")


# ── State ─────────────────────────────────────────────────────────────────────

def load_seen_uids():
    try:
        with open(STATE_FILE) as f:
            data = json.load(f)
            return set(data)
    except FileNotFoundError:
        return None   # None = genuinely first run
    except Exception as e:
        print(f"[WARN] Could not load state file: {e}")
        return None

def save_seen_uids(uids: set):
    with open(STATE_FILE, "w") as f:
        json.dump(sorted(list(uids)), f)
    print(f"[STATE] Saved {len(uids)} UIDs to {STATE_FILE}")


# ── Login ─────────────────────────────────────────────────────────────────────

def get_session() -> requests.Session:
    s = requests.Session()
    s.headers["User-Agent"] = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"

    r = s.get(WEBMAIL_URL, timeout=20)
    r.raise_for_status()

    token = ""
    for pat in [r'name="_token"\s+value="([^"]+)"',
                r'"request_token"\s*:\s*"([^"]+)"']:
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
        raise RuntimeError("Login failed — check USERNAME and PASSWORD.")

    print("[OK] Logged in.")
    return s


# ── Fetch inbox ───────────────────────────────────────────────────────────────

def fetch_inbox(s: requests.Session, page: int = 1):
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

        fromto       = meta.get("fromto", "")
        em           = re.search(r'title="([^"]+)"', fromto)
        nm           = re.search(r'class="rcmContactAddress">([^<]+)<', fromto)
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
    for part in ["1", "1.1", "2"]:
        try:
            r = s.get(
                WEBMAIL_URL + f"?_task=mail&_action=get&_uid={uid}&_mbox=INBOX&_part={part}",
                timeout=15
            )
            if r.status_code != 200:
                continue
            text = r.text.strip()
            if not text or len(text) < 20:
                continue
            if text.startswith("{") or text.startswith("this."):
                continue
            if "<" in text:
                text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL)
                text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.DOTALL)
                text = re.sub(r'<[^>]+>', ' ', text)
            text = html.unescape(text)
            text = re.sub(r'[ \t]+', ' ', text)
            text = re.sub(r'\n{3,}', '\n\n', text).strip()
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
    if r.status_code != 200:
        print(f"  [PUSH ERROR] Status {r.status_code}: {r.text[:200]}")
    r.raise_for_status()
    print("  [OK] Notification sent to phone.")


def notify(s: requests.Session, msg: dict):
    print(f"  → Fetching body for UID {msg['uid']}: {msg['subject'][:55]}")
    preview = fetch_body(s, msg["uid"])
    sender  = msg["sender_name"] or msg["sender_email"]
    push(
        f"📬 {sender}",
        f"✉  {msg['subject']}\n"
        f"👤 {msg['sender_email']}\n"
        f"🕐 {msg['date']}\n"
        f"{'─' * 32}\n"
        f"{preview}"
    )


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    args = sys.argv[1:]

    if not USERNAME or not PASSWORD or not PUSHBULLET_TOKEN:
        print("[ERROR] Credentials are empty!")
        print("        For local use: fill USERNAME/PASSWORD/PUSHBULLET_TOKEN in the script.")
        print("        For GitHub: set them as repository Secrets.")
        sys.exit(1)

    # --test
    if "--test" in args:
        print("[TEST] Sending ping to phone...")
        push("📬 NITT Mail — Test", "✅ Working! You'll be notified here when new mail arrives.")
        print("[TEST] Done. Check your phone.")
        return

    # --reset
    if "--reset" in args:
        if os.path.exists(STATE_FILE):
            os.remove(STATE_FILE)
            print(f"[RESET] Deleted {STATE_FILE}")
        else:
            print("[RESET] No state file found.")
        return

    # --preview N
    if "--preview" in args:
        try:
            n = int(args[args.index("--preview") + 1])
        except (IndexError, ValueError):
            n = 3
        print(f"[PREVIEW] Sending {n} latest unread mail(s) to phone...")
        session     = get_session()
        msgs, total = fetch_inbox(session)
        unread      = [m for m in msgs if not m["seen"]][:n]
        if not unread:
            print("[PREVIEW] No unread mails on page 1.")
        else:
            for msg in unread:
                notify(session, msg)
            print(f"[PREVIEW] Done! Check your phone.")
        return

    # --debug: show exactly what's happening with UIDs
    if "--debug" in args:
        print(f"[DEBUG] State file: {STATE_FILE}")
        seen = load_seen_uids()
        print(f"[DEBUG] Seen UIDs loaded: {len(seen) if seen else 'None (first run)'}")
        session     = get_session()
        msgs, total = fetch_inbox(session)
        now_uids    = {m["uid"] for m in msgs}
        print(f"[DEBUG] Current page-1 UIDs ({len(now_uids)}): min={min(now_uids)} max={max(now_uids)}")
        if seen:
            new_uids = now_uids - seen
            print(f"[DEBUG] New UIDs not in seen: {sorted(new_uids, reverse=True)}")
            gone     = seen - now_uids
            print(f"[DEBUG] Old UIDs no longer on page 1: {len(gone)} (scrolled to page 2+)")
        return

    # ── Normal run ────────────────────────────────────────────────────────────
    print(f"[INFO] State file path: {STATE_FILE}")
    seen        = load_seen_uids()
    session     = get_session()
    msgs, total = fetch_inbox(session)
    now_uids    = {m["uid"] for m in msgs}

    # First run — save baseline
    if seen is None:
        save_seen_uids(now_uids)
        print(f"[INIT] First run complete. Baseline: {len(now_uids)} UIDs.")
        print(f"[INIT] Total inbox: {total}. Watching for new mail from now on.")
        return

    new_uids = sorted(now_uids - seen, reverse=True)
    print(f"[INFO] Seen: {len(seen)} UIDs | Page-1 now: {len(now_uids)} | New: {len(new_uids)}")

    if not new_uids:
        print(f"[OK] No new mail. (Total inbox: {total})")
        save_seen_uids(seen | now_uids)
        return

    print(f"[NEW] {len(new_uids)} new message(s) found!")
    lookup = {m["uid"]: m for m in msgs}
    for uid in new_uids:
        if uid in lookup:
            notify(session, lookup[uid])

    save_seen_uids(seen | now_uids)
    print(f"[DONE] {len(new_uids)} notification(s) sent.")


if __name__ == "__main__":
    main()
