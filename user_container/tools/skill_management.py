"""
Skill Management Tool - Create, update, delete, and list custom skills.

Allows the agent to create new reusable skills for itself,
enabling self-learning of recurring workflows.
"""

import os
import re
import shutil
from typing import Any, Callable, Dict, TYPE_CHECKING

from user_container.tools.registry import ToolSchema, make_parameters

if TYPE_CHECKING:
    from user_container.db.db import DB
    from user_container.agent.skill_loader import SkillLoader


MANAGE_SKILL_SCHEMA = ToolSchema(
    name="manage_skill",
    description="""Create, update, delete, list custom skills, or write scripts for them.

Use ONLY when you have a confirmed plan and the user has explicitly agreed to create/update/delete a skill.
Do NOT call this tool to answer questions about skills — just respond in text.

Before calling action="create", you MUST have already:
1. Discussed the approach with the user (APIs, auth method, scope)
2. Presented a concrete plan
3. Received explicit user confirmation to proceed

Actions:
- "create": Register a new skill in DB.
- "write_script": Write a Python script for a skill (stores in DB + writes to disk). Use this instead of write_file for skill scripts.
- "update": Update an existing skill (requires skill_id + fields to change)
- "delete": Delete a custom skill (requires skill_id)
- "list": List all custom skills

Always use this tool to register skills and write their scripts — never create skill files manually.""",
    parameters=make_parameters(
        {
            "action": {
                "type": "string",
                "enum": ["create", "update", "delete", "list", "write_script"],
                "description": "Action to perform: create, update, delete, list, or write_script"
            },
            "skill_id": {
                "type": "string",
                "description": "Skill ID (required for update/delete/write_script, auto-generated for create)"
            },
            "name": {
                "type": "string",
                "description": "Human-readable skill name (required for create)"
            },
            "description": {
                "type": "string",
                "description": "When to use this skill - 'Use when...' format for router matching (required for create)"
            },
            "instructions": {
                "type": "string",
                "description": "Detailed markdown workflow instructions (required for create)"
            },
            "required_secrets": {
                "type": ["array", "null"],
                "items": {"type": "string"},
                "description": "List of environment variable names the skill needs (e.g., ['GMAIL_APP_PASSWORD']). User configures values in Settings."
            },
            "filename": {
                "type": "string",
                "description": "Script filename for write_script action (e.g., 'main.py'). Must be a .py file."
            },
            "content": {
                "type": "string",
                "description": "Script content for write_script action. Full Python source code."
            }
        },
        required=["action"]
    ),
    strict=False
)


def _slugify(name: str, max_len: int = 40) -> str:
    """Convert name to a URL-safe skill ID (lowercase, hyphens)."""
    slug = name.lower().strip()
    slug = re.sub(r'[^a-z0-9\s-]', '', slug)
    slug = re.sub(r'[\s_]+', '-', slug)
    slug = re.sub(r'-+', '-', slug)
    slug = slug.strip('-')
    return slug[:max_len]


def make_manage_skill_tool(
    db: "DB",
    skill_loader: "SkillLoader",
    skills_dir: str
) -> Callable[[Dict[str, Any]], Dict[str, Any]]:
    """
    Factory function to create the manage_skill tool handler.

    Args:
        db: Database instance
        skill_loader: SkillLoader instance (for cache clearing and conflict checks)
        skills_dir: Base skills directory path

    Returns:
        Tool handler function
    """
    def manage_skill(args: Dict[str, Any]) -> Dict[str, Any]:
        action = args.get("action")

        if action == "create":
            return _create_skill(args, db, skill_loader, skills_dir)
        elif action == "write_script":
            return _write_script(args, db, skill_loader, skills_dir)
        elif action == "update":
            return _update_skill(args, db, skill_loader, skills_dir)
        elif action == "delete":
            return _delete_skill(args, db, skill_loader, skills_dir)
        elif action == "list":
            return _list_skills(db)
        else:
            return {"status": "error", "error": f"Unknown action: {action}. Use create, write_script, update, delete, or list."}

    return manage_skill


def _create_skill(
    args: Dict[str, Any],
    db: "DB",
    skill_loader: "SkillLoader",
    skills_dir: str
) -> Dict[str, Any]:
    import json as json_mod

    name = args.get("name")
    description = args.get("description")
    instructions = args.get("instructions")
    required_secrets = args.get("required_secrets")

    if not name:
        return {"status": "error", "error": "Missing required field: name"}
    if not description:
        return {"status": "error", "error": "Missing required field: description"}
    if not instructions:
        return {"status": "error", "error": "Missing required field: instructions"}

    skill_id = _slugify(name)
    if not skill_id:
        return {"status": "error", "error": f"Could not generate valid skill ID from name: {name}"}

    # Check for conflict with built-in skills (filesystem)
    builtin_path = os.path.join(skills_dir, skill_id)
    if os.path.exists(os.path.join(builtin_path, "SKILL.md")):
        return {"status": "error", "error": f"Skill ID '{skill_id}' conflicts with a built-in skill. Choose a different name."}

    # Check for conflict with existing custom skills
    existing = db.get_custom_skill(skill_id)
    if existing:
        return {"status": "error", "error": f"Custom skill '{skill_id}' already exists. Use action='update' to modify it."}

    # Serialize required_secrets to JSON string
    secrets_json = json_mod.dumps(required_secrets) if required_secrets else None

    try:
        db.create_custom_skill(skill_id, name, description, instructions, secrets_json)

        # Create filesystem directory for scripts
        custom_dir = os.path.join(skills_dir, "_custom", skill_id, "scripts")
        os.makedirs(custom_dir, exist_ok=True)

        # Clear skill loader cache so new skill is discoverable
        skill_loader.clear_cache()

        return {
            "status": "success",
            "skill_id": skill_id,
            "name": name,
            "message": f"Skill '{name}' created (id: {skill_id}). Use manage_skill(action='write_script', skill_id='{skill_id}', filename='script.py', content='...') to add scripts."
        }
    except Exception as e:
        return {"status": "error", "error": f"Failed to create skill: {str(e)}"}


def _ensure_scripts_on_disk(skill_id: str, db: "DB", skills_dir: str) -> None:
    """Sync scripts from DB (source of truth) to disk. Always overwrites."""
    try:
        scripts = db.get_skill_scripts(skill_id)
        if not scripts:
            return
        scripts_path = os.path.join(skills_dir, "_custom", skill_id, "scripts")
        os.makedirs(scripts_path, exist_ok=True)
        for s in scripts:
            fp = os.path.join(scripts_path, s["filename"])
            with open(fp, "w", encoding="utf-8") as f:
                f.write(s["content"])
    except Exception:
        pass


def _write_script(
    args: Dict[str, Any],
    db: "DB",
    skill_loader: "SkillLoader",
    skills_dir: str
) -> Dict[str, Any]:
    skill_id = args.get("skill_id")
    filename = args.get("filename")
    content = args.get("content")

    if not skill_id:
        return {"status": "error", "error": "Missing required field: skill_id"}
    if not filename:
        return {"status": "error", "error": "Missing required field: filename"}
    if not content:
        return {"status": "error", "error": "Missing required field: content"}

    # Validate filename: only safe .py filenames, no paths or hidden files
    if not re.match(r'^[a-zA-Z0-9_-]+\.py$', filename):
        return {"status": "error", "error": f"Invalid filename: '{filename}'. Must match [a-zA-Z0-9_-]+.py (no paths, no hidden files)."}

    # Size limit
    if len(content) > 1_000_000:
        return {"status": "error", "error": "Script content exceeds 1MB limit."}

    # Verify skill exists
    existing = db.get_custom_skill(skill_id)
    if not existing:
        return {"status": "error", "error": f"Custom skill '{skill_id}' not found. Create it first with action='create'."}

    try:
        # Store in DB (source of truth)
        db.save_skill_script(skill_id, filename, content)

        # Write to disk
        scripts_path = os.path.join(skills_dir, "_custom", skill_id, "scripts")
        os.makedirs(scripts_path, exist_ok=True)
        file_path = os.path.join(scripts_path, filename)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)

        return {
            "status": "success",
            "skill_id": skill_id,
            "filename": filename,
            "path": file_path,
            "message": f"Script '{filename}' written for skill '{skill_id}'."
        }
    except Exception as e:
        return {"status": "error", "error": f"Failed to write script: {str(e)}"}


def _update_skill(
    args: Dict[str, Any],
    db: "DB",
    skill_loader: "SkillLoader",
    skills_dir: str
) -> Dict[str, Any]:
    import json as json_mod

    skill_id = args.get("skill_id")
    if not skill_id:
        return {"status": "error", "error": "Missing required field: skill_id"}

    existing = db.get_custom_skill(skill_id)
    if not existing:
        return {"status": "error", "error": f"Custom skill '{skill_id}' not found. Use action='list' to see available skills."}

    # Merge: use provided values or keep existing
    name = args.get("name") or existing["name"]
    description = args.get("description") or existing.get("description", "")
    instructions = args.get("instructions") or existing["instructions"]

    # Handle required_secrets: if provided use it, otherwise keep existing
    required_secrets = args.get("required_secrets")
    if required_secrets is not None:
        secrets_json = json_mod.dumps(required_secrets) if required_secrets else None
    else:
        secrets_json = existing.get("required_secrets")

    try:
        db.update_custom_skill(skill_id, name, description, instructions, secrets_json)
        skill_loader.clear_cache(skill_id)

        return {
            "status": "success",
            "skill_id": skill_id,
            "message": f"Skill '{name}' updated successfully."
        }
    except Exception as e:
        return {"status": "error", "error": f"Failed to update skill: {str(e)}"}


def _delete_skill(
    args: Dict[str, Any],
    db: "DB",
    skill_loader: "SkillLoader",
    skills_dir: str
) -> Dict[str, Any]:
    skill_id = args.get("skill_id")
    if not skill_id:
        return {"status": "error", "error": "Missing required field: skill_id"}

    # delete_custom_skill already calls delete_skill_secrets internally
    deleted = db.delete_custom_skill(skill_id)
    if not deleted:
        return {"status": "error", "error": f"Custom skill '{skill_id}' not found."}

    # Remove filesystem directory
    custom_dir = os.path.join(skills_dir, "_custom", skill_id)
    shutil.rmtree(custom_dir, ignore_errors=True)

    skill_loader.clear_cache(skill_id)

    return {
        "status": "success",
        "skill_id": skill_id,
        "message": f"Skill '{skill_id}' deleted."
    }


def _list_skills(db: "DB") -> Dict[str, Any]:
    import json as json_mod

    try:
        skills = db.get_custom_skills()
        if not skills:
            return {
                "status": "success",
                "skills": [],
                "message": "No custom skills found."
            }

        formatted = []
        for s in skills:
            entry = {"id": s["id"], "name": s["name"], "description": s.get("description", "")}
            # Parse required_secrets and check configured status
            req_secrets_raw = s.get("required_secrets")
            if req_secrets_raw:
                try:
                    req_secrets = json_mod.loads(req_secrets_raw)
                except (json_mod.JSONDecodeError, TypeError):
                    req_secrets = []
                if req_secrets:
                    configured = db.get_skill_secrets_status(s["id"])
                    entry["required_secrets"] = req_secrets
                    entry["secrets_configured"] = all(name in configured for name in req_secrets)
            formatted.append(entry)

        return {
            "status": "success",
            "skills": formatted,
            "count": len(formatted),
            "message": f"Found {len(formatted)} custom skill(s)."
        }
    except Exception as e:
        return {"status": "error", "error": f"Failed to list skills: {str(e)}"}
