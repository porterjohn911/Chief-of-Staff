import sys

import click
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel

from . import config, storage
from .agent import run_turn

console = Console()


@click.group(invoke_without_command=True)
@click.pass_context
def main(ctx):
    """Chief of Staff — your personal AI assistant."""
    if ctx.invoked_subcommand is None:
        ctx.invoke(chat)


@main.command()
def setup():
    """Initialize database and config directories."""
    config.ensure_dirs()
    storage.init_db()
    console.print(f"[green]OK[/green] data dir: {config.DATA_DIR}")
    console.print(f"[green]OK[/green] db:       {config.DB_PATH}")
    console.print(f"[green]OK[/green] journal:  {config.JOURNAL_DIR}")
    if not config.GOOGLE_OAUTH_CLIENT_SECRETS.exists():
        console.print(
            f"[yellow]![/yellow] OAuth secrets missing at {config.GOOGLE_OAUTH_CLIENT_SECRETS}\n"
            "    Create one at https://console.cloud.google.com/apis/credentials"
        )


@main.command(name="auth-google")
@click.option("--account", type=click.Choice(["user", "agent"]), default="user")
def auth_google(account):
    """Authorize a Google account (user or agent)."""
    from .google_auth import get_credentials
    creds = get_credentials(account)
    console.print(f"[green]OK[/green] authorized {account} (token cached, scopes: {creds.scopes})")


@main.command()
def chat():
    """Start an interactive chat with the agent."""
    storage.init_db()
    history: list = []
    console.print(Panel.fit(
        f"Chief of Staff for [bold]{config.USER_NAME}[/bold]. Type 'exit' to quit.",
        border_style="cyan",
    ))
    while True:
        try:
            user_in = console.input("[bold cyan]you[/bold cyan] > ").strip()
        except (EOFError, KeyboardInterrupt):
            console.print()
            return
        if not user_in:
            continue
        if user_in.lower() in {"exit", "quit", "q"}:
            return

        def on_tool(name, inputs):
            console.print(f"[dim]· {name}({_short(inputs)})[/dim]")

        try:
            text, history = run_turn(user_in, history, on_tool=on_tool)
        except Exception as e:
            console.print(f"[red]error:[/red] {e}")
            continue
        console.print("[bold magenta]cos[/bold magenta] >")
        console.print(Markdown(text))
        console.print()


def _short(d: dict) -> str:
    parts = []
    for k, v in d.items():
        s = str(v)
        if len(s) > 40:
            s = s[:40] + "..."
        parts.append(f"{k}={s}")
    return ", ".join(parts)


@main.command()
@click.argument("question", nargs=-1, required=True)
def ask(question):
    """One-shot question; prints the answer and exits."""
    storage.init_db()
    text, _ = run_turn(" ".join(question))
    console.print(Markdown(text))


@main.command()
@click.option("--send/--no-send", default=True, help="Email the briefing (default: send).")
def briefing(send):
    """Generate the morning briefing and optionally email it."""
    storage.init_db()
    from .briefing import generate_briefing, send_briefing
    if send:
        result = send_briefing()
        console.print(result)
    else:
        text = generate_briefing()
        console.print(Markdown(text))


@main.command(name="email-loop")
@click.option("--once", is_flag=True, help="Process one batch and exit (for testing).")
def email_loop_cmd(once):
    """Run the agent email inbox loop (foreground)."""
    storage.init_db()
    from .email_loop import run_loop
    run_loop(once=once)


@main.group()
def journal():
    """Journaling commands."""


@journal.command("prompt")
def journal_prompt():
    """Get a thoughtful journal prompt from the agent."""
    storage.init_db()
    from .tools.journal import get_journal_prompt
    p = get_journal_prompt()["prompt"]
    console.print(Panel(p, border_style="magenta", title="tonight's prompt"))


@journal.command("write")
def journal_write():
    """Open today's journal entry in $EDITOR and save it."""
    import os
    import subprocess
    import tempfile
    from datetime import date
    from .tools.journal import save_journal_entry, get_journal_prompt
    prompt = get_journal_prompt()["prompt"]
    editor = os.environ.get("EDITOR", "vi")
    with tempfile.NamedTemporaryFile(mode="w+", suffix=".md", delete=False) as f:
        f.write(f"# {date.today().isoformat()}\n\n> {prompt}\n\n")
        tmp_path = f.name
    subprocess.call([editor, tmp_path])
    content = open(tmp_path).read()
    body = content.split("\n", 3)[-1].strip()
    save_journal_entry(content=body, prompt=prompt)
    console.print("[green]saved.[/green]")


@journal.command("remind")
def journal_remind():
    """Send a journal reminder to the user (used by launchd at night)."""
    from .tools.gmail import send_email
    from .tools.journal import get_journal_prompt
    prompt = get_journal_prompt()["prompt"]
    if not config.USER_EMAIL:
        console.print(prompt); return
    send_email(
        to=config.USER_EMAIL,
        subject="Journal time",
        body=f"Tonight's prompt:\n\n  {prompt}\n\nReply to this email with your entry and I'll save it.",
        account="agent" if config.AGENT_EMAIL != config.USER_EMAIL else "user",
    )
    console.print("[green]reminder sent.[/green]")


@main.command()
def projects():
    """List active projects and their open tasks."""
    storage.init_db()
    from .tools.projects import list_projects, list_tasks
    p = list_projects(status="active")["projects"]
    t = list_tasks(status="open")["tasks"]
    if not p:
        console.print("[dim]No active projects.[/dim]")
    for pr in p:
        console.print(f"[bold]· {pr['name']}[/bold]  [dim]({pr['status']})[/dim]")
        for tk in [x for x in t if x["project"] == pr["name"]]:
            due = f"  [yellow]due {tk['due_date']}[/yellow]" if tk["due_date"] else ""
            console.print(f"    - {tk['title']}{due}")
    orphans = [x for x in t if not x["project"]]
    if orphans:
        console.print("[bold]· (no project)[/bold]")
        for tk in orphans:
            due = f"  [yellow]due {tk['due_date']}[/yellow]" if tk["due_date"] else ""
            console.print(f"    - {tk['title']}{due}")


@main.group()
def health():
    """Health logging."""


@health.command("log")
@click.argument("metric")
@click.argument("value", type=float)
@click.option("--unit", default=None)
@click.option("--notes", default="")
def health_log_cmd(metric, value, unit, notes):
    """Quick-log a health metric: e.g. `cos health log weight 178`."""
    storage.init_db()
    from .tools.health import log_health
    out = log_health(metric=metric, value=value, unit=unit, notes=notes)
    console.print(out)


@health.command("summary")
@click.option("--days", default=7)
def health_summary_cmd(days):
    storage.init_db()
    from .tools.health import health_summary
    out = health_summary(days=days)
    console.print(out)


@main.group()
def relationships():
    """Relationship reminders."""


@relationships.command("due")
def rel_due():
    storage.init_db()
    from .tools.relationships import who_to_reach_out_to
    out = who_to_reach_out_to()
    if not out["overdue"]:
        console.print("[green]nobody overdue — well done.[/green]"); return
    for c in out["overdue"]:
        od = c["days_overdue"]
        tag = f"[red]{od}d overdue[/red]" if od else "[yellow]never contacted[/yellow]"
        console.print(f"· {c['name']}  {tag}")


if __name__ == "__main__":
    main()
