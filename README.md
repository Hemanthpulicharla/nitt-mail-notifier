<div align="center">

```
███╗   ██╗██╗████████╗████████╗    ███╗   ███╗ █████╗ ██╗██╗     
████╗  ██║██║╚══██╔══╝╚══██╔══╝    ████╗ ████║██╔══██╗██║██║     
██╔██╗ ██║██║   ██║      ██║       ██╔████╔██║███████║██║██║     
██║╚██╗██║██║   ██║      ██║       ██║╚██╔╝██║██╔══██║██║██║     
██║ ╚████║██║   ██║      ██║       ██║ ╚═╝ ██║██║  ██║██║███████╗
╚═╝  ╚═══╝╚═╝   ╚═╝      ╚═╝       ╚═╝     ╚═╝╚═╝  ╚═╝╚═╝╚══════╝
```

### *because NITT's webmail doesn't deserve to live rent-free in your browser tab*

![Last Checked](https://img.shields.io/badge/last_checked-auto_every_5_min-blue?style=flat-square)
![Built With](https://img.shields.io/badge/built_with-Python_3.11-yellow?style=flat-square)
![Runs On](https://img.shields.io/badge/runs_on-GitHub_Actions_(free)-black?style=flat-square)
![Notifies Via](https://img.shields.io/badge/notifies_via-Pushbullet-green?style=flat-square)
![NITT](https://img.shields.io/badge/made_for-NITT_students-red?style=flat-square)

</div>

---

## What is this?

You know how NITT's webmail (`students.nitt.edu/`) is completely unusable on mobile, won't send notifications, and you have to manually check it like it's 2003? Yeah. This fixes that.

This tool runs silently in the cloud (GitHub's free servers), logs into your webmail every **5 minutes**, and the moment a new mail lands in your NITT inbox - **your Android phone gets a Pushbullet notification** with the sender's name, subject line, and a preview of the actual message body. Just like Gmail does it.

No PC running. No phone battery drain. No app to keep open. Just notifications, automatically, forever.

---

## How notification looks like

```
┌─────────────────────────────────────────┐
│  📬 Associate Dean (Students Welfare)  │
│ ─────────────────────────────────────── │
│  ✉  Registration for Passport Mela '26 │
│  👤 adsw@nitt.edu                       │
│  🕐 Mon 05:02 PM                        │
│  ────────────────────────────────────   │
│  Dear Students, You are invited to      │
│  register for the upcoming Passport     │
│  Mela being organized on campus. The    │
│  last date to register is…              │
└─────────────────────────────────────────┘
```

One notification per mail. No spam. No repeats.

---

## how it works (the 30 second version)

```
GitHub Actions wakes up every 5 min
         │
         ▼
   Logs into your NITT webmail
         │
         ▼
   Fetches inbox — grabs all message UIDs
         │
         ▼
   Compares with seen_uids.json (saved from last run)
         │
    ┌────┴────┐
    │         │
  same     NEW UIDs found!
    │         │
  sleep     Fetches subject + body for each
             │
             ▼
        Pushbullet → your Android phone 📱
             │
             ▼
        Saves updated UIDs back to repo
```

State (`seen_uids.json`) is committed back to the repo after every run — that's how it remembers what it already notified you about across runs.

---

## Setup - do this once, never touch it again

### step 1 - get pushbullet on your phone

1. Install **Pushbullet** from Play Store
2. Sign up / log in
3. On a browser go to **[pushbullet.com/account](https://www.pushbullet.com/#settings/account)**
4. Scroll to **Access Tokens** - click **Create Access Token**
5. Copy the token - looks like `o.AbCdEfGhIjKl123456`

---

### step 2 - set up this repo

1. Hit the **Fork** button on this repo (top right) - or create a new **private** repo and upload both files

**Make it private.** Your secrets are stored separately but still - don't broadcast that you're monitoring your inbox.

2. Make sure your repo has these two files at the right paths:

```
your-repo/
├── nitt_checker.py                       
└── .github/
    └── workflows/
        └── check_mail.yml                 
```

To create the workflow file on GitHub: click **Add file - Create new file**, type `.github/workflows/check_mail.yml` as the filename (GitHub auto-creates the folders when you type the `/`), paste the YAML, and save.

---

### step 3 - add your secrets

Go to your repo → **Settings** → **Secrets and variables** - **Actions** → **New repository secret**

Add these three, one by one:

| Secret Name | What to put |
|---|---|
| `NITT_USERNAME` | Your full NITT email - e.g. `210125023@nitt.edu` |
| `NITT_PASSWORD` | Your webmail login password |
| `PUSHBULLET_TOKEN` | The `o.Abc...` token from step 1 |

Secrets are encrypted by GitHub and never visible to anyone - not even you after saving. The script accesses them as environment variables at runtime.

---

### step 4 — run it manually to confirm

1. Go to the **Actions** tab in your repo
2. Click **NITT Mail Checker** in the left list
3. Click the **Run workflow** dropdown → **Run workflow**
4. Click into the running job to watch live logs

**First run** - you'll see:
```
[OK] Logged in.
[STATE] Saved 50 UIDs to seen_uids.json
[INIT] First run complete. Baseline: 50 UIDs.
[INIT] Total inbox: 408. Watching for new mail from now on.
```
This is correct. It's saving your current inbox as a baseline.

**After this** - run it again manually. You'll see:
```
[OK] Logged in.
[INFO] Seen: 50 UIDs | Page-1 now: 50 | New: 0
[OK] No new mail. (Total inbox: 408)
```

You'll also see `seen_uids.json` appear as a committed file in your repo. **That's the confirmation it's working.** From this point, every new mail = notification on your phone, automatically.

---

## Local testing commands

For testing on your own PC before/after uploading to GitHub.

First fill in your credentials temporarily in lines 12–14 of the script (blank them before committing):

```bash
# Verify Pushbullet sends to your phone
python nitt_checker.py --test

# Push your latest 3 unread mails to phone immediately
python nitt_checker.py --preview 3

# Show detailed debug info about UIDs and state
python nitt_checker.py --debug

# Clear saved state (next run will set a fresh baseline)
python nitt_checker.py --reset

# Normal run (same as what GitHub runs)
python nitt_checker.py
```

---

## ❓ common questions

**Q: It shows `[NO CHANGE]` every time — is it broken?**  
A: No. `[NO CHANGE]` means it ran, checked, found nothing new, and went back to sleep. That's exactly what it should do. You'll see `[NEW]` the moment an actual mail arrives.

**Q: Will it notify me about mails I already had before setup?**  
A: No. The first run saves your existing inbox as the baseline. Only mails that arrive *after* setup trigger notifications. Use `--preview N` to manually push older mails to your phone whenever you want.

**Q: How long until I get a notification after a mail arrives?**  
A: Maximum 5 minutes (GitHub's scheduler minimum). Usually 3–4 minutes in practice. During high-load periods on GitHub's servers it can occasionally slip to 7–8 minutes.

**Q: Does it work when I'm on bad network / 2G?**  
A: Yes. The script runs on GitHub's servers in the cloud — your network has nothing to do with it running. Your phone just needs a brief moment of connectivity to receive the Pushbullet notification, which is tiny (a few hundred bytes, way under 2G).

**Q: Is my password safe?**  
A: Your password lives only in GitHub Secrets, which are encrypted at rest and never logged anywhere. The script running in GitHub Actions accesses it as an environment variable that's masked in all logs. Don't hardcode it in the script file itself.

**Q: Can I change the check frequency?**  
A: Yes. Edit `check_mail.yml` and change the cron line. `*/5` = every 5 min (minimum). `*/10` = every 10 min. `*/30` = every 30 min. GitHub's hard minimum is 5 minutes.

**Q: Does it check only the first page of inbox (50 mails)?**  
A: Yes, by design. New mail always arrives on page 1 (sorted newest first), so checking only page 1 is sufficient to catch new arrivals. It doesn't need to scan your entire 400-mail history.

---

## file reference

```
nitt_checker.py       Main script — login, fetch, compare, notify
check_mail.yml        GitHub Actions workflow — scheduling and execution
seen_uids.json        Auto-generated — the memory of what's been notified
                      (committed back to repo after every run)
```

---

## 🛠️ built with

- **Python 3.11** + `requests` — login, scraping, API calls
- **Roundcube Web API** — JSON endpoints for inbox listing and mail fetch
- **Pushbullet API** — phone notifications
- **GitHub Actions** — free cloud scheduler (2000 min/month on free tier, this uses ~10 min/day)

---

<div align="center">

*Made out of frustration at 11pm when a deadline mail arrived and nobody saw it.*  
*For NIT Trichy students, by a NIT Trichy student.*

</div>
