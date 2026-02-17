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
    description="""Create, update, delete, or list custom skills (reusable workflows).

Use when user asks to create a skill, learn something, or remember a workflow.

Actions:
- "create": Register a new skill in DB. Returns scripts_path — write Python scripts there using write_file.
- "update": Update an existing skill (requires skill_id + fields to change)
- "delete": Delete a custom skill (requires skill_id)
- "list": List all custom skills

Always use this tool to register skills — never create skill files manually.""",
    parameters=make_parameters(
        {
            "action": {
                "type": "string",
                "enum": ["create", "update", "delete", "list"],
                "description": "Action to perform: create, update, delete, or list"
            },
            "skill_id": {
                "type": "string",
                "description": "Skill ID (required for update/delete, auto-generated for create)"
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
        elif action == "update":
            return _update_skill(args, db, skill_loader, skills_dir)
        elif action == "delete":
            return _delete_skill(args, db, skill_loader, skills_dir)
        elif action == "list":
            return _list_skills(db)
        else:
            return {"status": "error", "error": f"Unknown action: {action}. Use create, update, delete, or list."}

    return manage_skill


def _create_skill(
    args: Dict[str, Any],
    db: "DB",
    skill_loader: "SkillLoader",
    skills_dir: str
) -> Dict[str, Any]:
    name = args.get("name")
    description = args.get("description")
    instructions = args.get("instructions")

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

    try:
        db.create_custom_skill(skill_id, name, description, instructions)

        # Create filesystem directory for scripts
        custom_dir = os.path.join(skills_dir, "_custom", skill_id, "scripts")
        os.makedirs(custom_dir, exist_ok=True)

        # Clear skill loader cache so new skill is discoverable
        skill_loader.clear_cache()

        scripts_path = os.path.join(skills_dir, "_custom", skill_id, "scripts")

        return {
            "status": "success",
            "skill_id": skill_id,
            "name": name,
            "scripts_path": scripts_path,
            "message": f"Skill '{name}' created (id: {skill_id}). Scripts directory: {scripts_path}. You can now write Python scripts there using write_file."
        }
    except Exception as e:
        return {"status": "error", "error": f"Failed to create skill: {str(e)}"}


def _update_skill(
    args: Dict[str, Any],
    db: "DB",
    skill_loader: "SkillLoader",
    skills_dir: str
) -> Dict[str, Any]:
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

    try:
        db.update_custom_skill(skill_id, name, description, instructions)
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
    try:
        skills = db.get_custom_skills()
        if not skills:
            return {
                "status": "success",
                "skills": [],
                "message": "No custom skills found."
            }

        formatted = [
            {"id": s["id"], "name": s["name"], "description": s.get("description", "")}
            for s in skills
        ]

        return {
            "status": "success",
            "skills": formatted,
            "count": len(formatted),
            "message": f"Found {len(formatted)} custom skill(s)."
        }
    except Exception as e:
        return {"status": "error", "error": f"Failed to list skills: {str(e)}"}
