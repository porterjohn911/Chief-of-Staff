from __future__ import annotations

from ..storage import connect, now
from .registry import tool


@tool(
    name="create_project",
    description="Create a new project to track.",
    input_schema={
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "description": {"type": "string"},
            "target_date": {"type": "string", "description": "YYYY-MM-DD"},
        },
        "required": ["name"],
    },
)
def create_project(name: str, description: str = "", target_date: str | None = None):
    with connect() as c:
        c.execute(
            "INSERT INTO projects (name, description, status, target_date, created_at, updated_at) "
            "VALUES (?,?,?,?,?,?)",
            (name, description, "active", target_date, now(), now()),
        )
    return {"created": True, "name": name}


@tool(
    name="list_projects",
    description="List projects, optionally filtered by status.",
    input_schema={
        "type": "object",
        "properties": {
            "status": {"type": "string", "enum": ["active", "paused", "done", "all"], "default": "active"},
        },
    },
)
def list_projects(status: str = "active"):
    with connect() as c:
        if status == "all":
            rows = c.execute("SELECT * FROM projects ORDER BY updated_at DESC").fetchall()
        else:
            rows = c.execute(
                "SELECT * FROM projects WHERE status = ? ORDER BY updated_at DESC", (status,)
            ).fetchall()
    return {"projects": [dict(r) for r in rows]}


@tool(
    name="update_project",
    description="Update project status, description, or target date.",
    input_schema={
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "status": {"type": "string", "enum": ["active", "paused", "done"]},
            "description": {"type": "string"},
            "target_date": {"type": "string"},
        },
        "required": ["name"],
    },
)
def update_project(name: str, status: str | None = None, description: str | None = None,
                   target_date: str | None = None):
    fields, vals = [], []
    if status:
        fields.append("status = ?"); vals.append(status)
    if description is not None:
        fields.append("description = ?"); vals.append(description)
    if target_date is not None:
        fields.append("target_date = ?"); vals.append(target_date)
    if not fields:
        return {"updated": False, "reason": "nothing to update"}
    fields.append("updated_at = ?"); vals.append(now())
    vals.append(name)
    with connect() as c:
        c.execute(f"UPDATE projects SET {', '.join(fields)} WHERE name = ?", vals)
    return {"updated": True, "name": name}


@tool(
    name="add_task",
    description="Add a task, optionally under a project.",
    input_schema={
        "type": "object",
        "properties": {
            "title": {"type": "string"},
            "project_name": {"type": "string"},
            "notes": {"type": "string"},
            "due_date": {"type": "string", "description": "YYYY-MM-DD"},
        },
        "required": ["title"],
    },
)
def add_task(title: str, project_name: str | None = None, notes: str = "",
             due_date: str | None = None):
    project_id = None
    with connect() as c:
        if project_name:
            row = c.execute("SELECT id FROM projects WHERE name = ?", (project_name,)).fetchone()
            if row:
                project_id = row["id"]
            else:
                c.execute(
                    "INSERT INTO projects (name, status, created_at, updated_at) VALUES (?,?,?,?)",
                    (project_name, "active", now(), now()),
                )
                project_id = c.execute(
                    "SELECT id FROM projects WHERE name = ?", (project_name,)
                ).fetchone()["id"]
        c.execute(
            "INSERT INTO tasks (project_id, title, notes, status, due_date, created_at) "
            "VALUES (?,?,?,?,?,?)",
            (project_id, title, notes, "open", due_date, now()),
        )
    return {"added": True, "title": title, "project": project_name}


@tool(
    name="list_tasks",
    description="List tasks, optionally filtered by status, project, or due-before date.",
    input_schema={
        "type": "object",
        "properties": {
            "status": {"type": "string", "enum": ["open", "done", "all"], "default": "open"},
            "project_name": {"type": "string"},
            "due_before": {"type": "string", "description": "YYYY-MM-DD"},
        },
    },
)
def list_tasks(status: str = "open", project_name: str | None = None,
               due_before: str | None = None):
    sql = "SELECT t.*, p.name AS project FROM tasks t LEFT JOIN projects p ON t.project_id = p.id WHERE 1=1"
    args: list = []
    if status != "all":
        sql += " AND t.status = ?"; args.append(status)
    if project_name:
        sql += " AND p.name = ?"; args.append(project_name)
    if due_before:
        sql += " AND t.due_date IS NOT NULL AND t.due_date <= ?"; args.append(due_before)
    sql += " ORDER BY t.due_date IS NULL, t.due_date, t.created_at"
    with connect() as c:
        rows = c.execute(sql, args).fetchall()
    return {"tasks": [dict(r) for r in rows]}


@tool(
    name="complete_task",
    description="Mark a task as done by id.",
    input_schema={
        "type": "object",
        "properties": {"task_id": {"type": "integer"}},
        "required": ["task_id"],
    },
)
def complete_task(task_id: int):
    with connect() as c:
        c.execute(
            "UPDATE tasks SET status = 'done', completed_at = ? WHERE id = ?",
            (now(), task_id),
        )
    return {"completed": True, "task_id": task_id}
