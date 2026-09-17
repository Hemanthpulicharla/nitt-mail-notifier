<div align="center">

```
███╗   ██╗██╗████████╗████████╗    ███╗   ███╗ █████╗ ██╗██╗     
████╗  ██║██║╚══██╔══╝╚══██╔══╝    ████╗ ████║██╔══██╗██║██║     
██╔██╗ ██║██║   ██║      ██║       ██╔████╔██║███████║██║██║     
██║╚██╗██║██║   ██║      ██║       ██║╚██╔╝██║██╔══██║██║██║     
██║ ╚████║██║   ██║      ██║       ██║ ╚═╝ ██║██║  ██║██║███████╗
╚═╝  ╚═══╝╚═╝   ╚═╝      ╚═╝       ╚═╝     ╚═╝╚═╝  ╚═╝╚═╝╚══════╝
```

### *A small utility to bring NITT webmail notifications to your phone.*

![Last Checked](https://img.shields.io/badge/last_checked-auto_every_5_min-blue?style=flat-square)
![Built With](https://img.shields.io/badge/built_with-Python_3.11-yellow?style=flat-square)
![Runs On](https://img.shields.io/badge/runs_on-GitHub_Actions-black?style=flat-square)
![Notifies Via](https://img.shields.io/badge/notifies_via-Pushbullet-green?style=flat-square)

</div>

---

## Why this exists

If you study at NITT, you already know how webmail (`students.nitt.edu/`) works out in practice. The interface is clunky on mobile, there are no native push alerts, and important department circulars usually arrive quietly when you are nowhere near your laptop. Most of the time, you only find out about a deadline because someone forwarded a screenshot to a batch WhatsApp group.

This setup automates that check. It uses a small Python script scheduled on GitHub Actions to check your inbox every 5 minutes. Whenever a new mail arrives, it forwards the sender, subject, and a short preview directly to your phone using Pushbullet. 

You do not need to keep a browser tab open, run anything locally on your PC, or keep a background app draining battery on your phone.

---

## What the notification looks like

```
┌─────────────────────────────────────────┐
│  📬 Associate Dean (Students Welfare)   │
│ ─────────────────────────────────────── │
│  ✉  Registration for Passport Mela '26  │
│  👤 adsw@nitt.edu                        │
│  🕐 Mon 05:02 PM                         │
│  ────────────────────────────────────    │
│  Dear Students, You are invited to       │
│  register for the upcoming Passport      │
│  Mela being organized on campus. The     │
│  last date to register is...             │
└─────────────────────────────────────────┘
```

The script tracks already delivered messages in a file called `seen_uids.json`. After each run, it commits this file back to your repository so it remembers what has already been pushed and avoids duplicate alerts.

---

## Setup guide

### Step 1: Set up Pushbullet

1. Install the Pushbullet app on your phone from the Play Store.
2. Log in and open [pushbullet.com/#settings/account](https://www.pushbullet.com/#settings/account) in a browser.
3. Scroll down to **Access Tokens** and click **Create Access Token**.
4. Copy the generated token (it usually starts with `o.`).

---

### Step 2: Create your repository

1. Fork this repository, or create a new **private** repository on your GitHub account and upload the code.
2. Keep the repository private so your commit activity and mail check logs remain your own.
3. Make sure the files match this structure:

```
your-repo/
├── nitt_checker.py                       
└── .github/
    └── workflows/
        └── check_mail.yml                 
```

If you are creating the workflow manually on GitHub, click **Add file -> Create new file**, paste `.github/workflows/check_mail.yml` in the name field, paste the workflow contents, and commit.

---

### Step 3: Add your credentials as GitHub Secrets

Go to your repository: **Settings -> Secrets and variables -> Actions -> New repository secret**.

Add the following three secrets:

| Secret Name | Value |
|---|---|
| `NITT_USERNAME` | Your full roll-number email (e.g. `210125023@nitt.edu`) |
| `NITT_PASSWORD` | Your webmail login password |
| `PUSHBULLET_TOKEN` | The access token copied from Step 1 |

GitHub encrypts these values, so they remain hidden and are only exposed as environment variables during the workflow run.

---

### Step 4: Run a first check to set the baseline

1. Go to the **Actions** tab in your repository.
2. Select **NITT Mail Checker** from the list on the left.
3. Click **Run workflow -> Run workflow**.
4. Open the run log to see the output.

On the **first run**, the script establishes a baseline so it does not blast your phone with your entire existing inbox:

```
[OK] Logged in.
[STATE] Saved 50 UIDs to seen_uids.json
[INIT] First run complete. Baseline: 50 UIDs.
[INIT] Total inbox: 408. Watching for new mail from now on.
```

If you trigger it a second time manually, you will see it verify the baseline:

```
[OK] Logged in.
[INFO] Seen: 50 UIDs | Page-1 now: 50 | New: 0
[OK] No new mail. (Total inbox: 408)
```

You will also notice `seen_uids.json` in your repository files. Once this file is committed, the workflow runs on schedule and notifies you whenever a new mail lands.

---

## Local testing

If you want to run or test the script directly on your computer:

```bash
# Verify Pushbullet notifications reach your device
python nitt_checker.py --test

# Push the 3 most recent unread emails to your phone
python nitt_checker.py --preview 3

# Inspect UID states and inbox debug info
python nitt_checker.py --debug

# Reset seen records (the next run resets the baseline)
python nitt_checker.py --reset

# Standard run
python nitt_checker.py
```

*Note: If you paste credentials into lines 12-14 for local testing, remember to clear them before committing code to git.*

---

## Repository layout

* `nitt_checker.py`: Handles logging into webmail, checking UIDs, and triggering Pushbullet.
* `.github/workflows/check_mail.yml`: GitHub Actions configuration running on a 5-minute cron schedule.
* `seen_uids.json`: Stores message IDs that have already been handled so alerts are not repeated.

---

## Technical stack

* **Python 3.11** with `requests` for session handling and HTTP requests.
* **Roundcube Web API** JSON endpoints for fetching inbox listings and message bodies.
* **Pushbullet API** for mobile push alerts.
* **GitHub Actions** for scheduled execution.

---

<div align="center">

*Written out of the common frustration of missing important campus circulars at odd hours.*  
*Simple, transparent, and intended for NIT Trichy students.*

</div>
