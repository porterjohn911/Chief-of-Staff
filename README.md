# Chief of Staff (`cos`)

A local AI Chief of Staff for your MacBook. Powered by Claude, integrated with
your Gmail and Google Calendar, with built-in journaling, health logging,
project tracking, and relationship reminders.

Talk to it in the terminal, give it its own email address so you can text
it from anywhere, and let it brief you every morning.

---

## What it does

- **Email**: read, summarize, draft, and send via Gmail
- **Calendar**: list upcoming events, schedule new ones, remind you before
- **Health**: log weight, sleep, workouts, water, meds, and review trends
- **Projects**: capture ideas, break them into tasks, track progress
- **Journal**: daily prompts, free-write entries, weekly retrospectives
- **Relationships**: who you should reach out to, when you last did, what matters to them
- **Daily briefing**: every morning at 7am, agent sends you a summary

---

## Quickstart

### 1. Install

```bash
git clone <this-repo> ~/cos
cd ~/cos
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

### 2. Configure

```bash
cp .env.example .env
```

Fill in:

- `USER_NAME`, `USER_EMAIL`, `USER_TIMEZONE`
- `GOOGLE_OAUTH_CLIENT_SECRETS` — path to your OAuth client JSON
  (see "Set up Google APIs" below)

No Anthropic API key required — the agent talks to Claude through the
Claude Code CLI on your Mac, which is included in your Claude Pro/Max
subscription. Install it and log in once:

```bash
npm install -g @anthropic-ai/claude-code   # requires Node.js
claude /login                              # pick "Claude.ai account"
```

### 3. Set up Google APIs (for Gmail + Calendar)

1. Go to https://console.cloud.google.com/, create a project.
2. Enable APIs: **Gmail API** and **Google Calendar API**.
3. Create an **OAuth 2.0 Client ID** (type: Desktop app), download the JSON.
4. Save it to `~/.config/cos/google_client_secrets.json` and point
   `GOOGLE_OAUTH_CLIENT_SECRETS` at it.

### 4. Give the agent its own email (optional but recommended)

1. Create a brand-new Gmail account, e.g. `cos.<yourname>@gmail.com`.
2. Run `cos auth-google --account agent` and complete the browser flow
   while signed into the agent's account. This authorizes the agent's inbox
   for sending and reading.
3. Run `cos auth-google --account user` and authorize *your* primary account.
   This is used for reading your own inbox and calendar.

You can now email the agent at its address and it will reply. Run
`cos email-loop` (or install it as a launchd job — see below) to keep the
loop running.

### 5. Chat with it

```bash
cos chat
```

### 6. Install background jobs

```bash
./scripts/install_launchd.sh
```

This installs three launchd jobs:

- `com.cos.briefing` — runs every weekday at 7:00 AM, sends you the briefing
- `com.cos.journal`  — runs nightly at 9:00 PM, sends a journal reminder
- `com.cos.emailloop` — polls the agent inbox every 2 minutes

Uninstall with `./scripts/uninstall_launchd.sh`.

---

## Commands

| Command                    | What it does                                        |
| -------------------------- | --------------------------------------------------- |
| `cos chat`                 | Interactive REPL with the agent                     |
| `cos ask "<question>"`     | One-shot question, prints answer and exits          |
| `cos briefing`             | Generate and send today's briefing now              |
| `cos email-loop`           | Start the inbox polling loop (foreground)           |
| `cos journal`              | Open today's journal entry in `$EDITOR`             |
| `cos journal prompt`       | Get a journal prompt from the agent                 |
| `cos health log <type> <value>` | Quick-log a health metric                      |
| `cos projects`             | List projects and open tasks                        |
| `cos relationships due`    | Show people you're overdue to contact               |
| `cos auth-google ...`      | Authorize a Google account                          |
| `cos setup`                | Initialize database and config directories          |

---

## How it works

- **Agent loop**: Claude (Opus 4.7) runs a tool-use loop. Every "area"
  (mail/calendar/health/projects/journal/relationships) is exposed as a set
  of tools. The agent decides which to call based on what you say.
- **Storage**: SQLite database at `~/.local/share/cos/cos.db`. Journal
  entries are also written as Markdown files in `~/.local/share/cos/journal/`
  so you own them in plain text.
- **Email loop**: polls the agent's Gmail every 2 min. New unread messages
  get fed to the agent as user input. The agent replies via Gmail.
- **Briefing**: runs the agent with a special prompt that pulls calendar
  events, overdue tasks, recent journal mood, and people you should ping,
  then emails the digest to you.

---

## Layout

```
cos/
├── cli.py              # entry point, subcommands
├── agent.py            # Claude tool-use loop
├── config.py           # env & paths
├── storage.py          # SQLite schema + helpers
├── google_auth.py      # OAuth flow
├── briefing.py         # morning briefing
├── email_loop.py       # inbox poller
├── prompts/
│   └── system.md       # the agent's persona
└── tools/
    ├── gmail.py
    ├── calendar.py
    ├── health.py
    ├── projects.py
    ├── journal.py
    └── relationships.py
```

---

## Roadmap / next things to add

- Voice input via `whisper.cpp`
- iMessage integration (read-only via `~/Library/Messages/chat.db`)
- Apple Health export ingest
- Web dashboard
- Finance tracking
- Sleep score correlation with calendar load
