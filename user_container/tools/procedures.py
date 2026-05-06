"""
Procedures Tool - Create, list, and manage AI-guided procedure workflows.

Allows the agent to create shareable procedure workflows that guide users
through multi-step processes via conversational AI.
"""

import re
import uuid
from typing import Any, Callable, Dict, TYPE_CHECKING

from user_container.tools.registry import ToolSchema, make_parameters

if TYPE_CHECKING:
    from user_container.db.db import DB


def _slugify(name: str) -> str:
    slug = name.lower().strip()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s_]+", "-", slug)
    slug = re.sub(r"-+", "-", slug).strip("-")
    return slug or "procedure"


def _unique_slug(base_slug: str, db: "DB") -> str:
    slug = base_slug
    counter = 2
    while db.get_procedure_by_slug(slug):
        slug = f"{base_slug}-{counter}"
        counter += 1
    return slug


CREATE_PROCEDURE_SCHEMA = ToolSchema(
    name="create_procedure",
    description="""Create a new AI-guided procedure workflow for END USERS.

A procedure is a PUBLIC, SHAREABLE, INTERACTIVE workflow — NOT an internal AI skill.
Use this (NOT manage_skill) when the user wants to build something that:
- Other people will run via a /p/slug link
- Guides a human through a step-by-step process in a conversation
- Collects information from the end user and produces an output
Examples: document fill-in wizard, client onboarding, intake form, daily check-in, contract review.

Contrast with skills: a skill is an internal AI tool/script. A procedure is a user-facing guided session.

IMPORTANT: Collect all necessary details from the user through conversation
BEFORE calling this tool. Ask about:
- What task should the procedure guide the end user through?
- What information does the AI need to gather from the end user?
- Are there any reference documents or files?
- When is the procedure considered complete?

The skill_prompt is the core instruction set for the AI that runs the procedure.
Write it in detail — it becomes the system prompt for that guided session.""",
    parameters=make_parameters(
        {
            "name": {
                "type": "string",
                "description": "Human-readable name for the procedure (e.g., 'Client Onboarding', 'Contract Review')"
            },
            "slug": {
                "type": "string",
                "description": "URL slug for the procedure (e.g., 'client-onboarding'). Leave empty to auto-generate from name."
            },
            "skill_prompt": {
                "type": "string",
                "description": "Detailed AI instruction set — what the AI should do when a user starts this procedure. Include: goal, steps, what to ask the user, how to handle edge cases, what output to produce."
            },
            "completion_condition": {
                "type": "string",
                "description": "Optional marker the AI should include when the procedure is complete. Defaults to [PROCEDURE_COMPLETE]."
            }
        },
        required=["name", "skill_prompt"]
    ),
    strict=False
)


def make_create_procedure_tool(db: "DB") -> Callable[[Dict[str, Any]], Dict[str, Any]]:
    def create_procedure(args: Dict[str, Any]) -> Dict[str, Any]:
        name = args.get("name", "").strip()
        skill_prompt = args.get("skill_prompt", "").strip()
        completion_condition = args.get("completion_condition") or "[PROCEDURE_COMPLETE]"
        custom_slug = args.get("slug", "").strip()

        if not name:
            return {"status": "error", "error": "Procedure name is required."}
        if not skill_prompt:
            return {"status": "error", "error": "skill_prompt is required."}

        base_slug = _slugify(custom_slug) if custom_slug else _slugify(name)
        slug = _unique_slug(base_slug, db)

        procedure_id = str(uuid.uuid4())
        try:
            db.create_procedure(procedure_id, name, slug, skill_prompt, completion_condition)
            return {
                "status": "success",
                "procedure_id": procedure_id,
                "name": name,
                "slug": slug,
                "url": f"/p/{slug}",
                "message": f"Procedure '{name}' created successfully. Users can run it at /p/{slug}."
            }
        except Exception as e:
            return {"status": "error", "error": f"Failed to create procedure: {str(e)}"}

    return create_procedure


LIST_PROCEDURES_SCHEMA = ToolSchema(
    name="list_procedures",
    description="""List all existing procedure workflows.

Use BEFORE creating or modifying a procedure to see what already exists.
Returns id, name, slug, and a summary of each procedure.""",
    parameters=make_parameters({}, required=[]),
    strict=False
)


def make_list_procedures_tool(db: "DB") -> Callable[[Dict[str, Any]], Dict[str, Any]]:
    def list_procedures(args: Dict[str, Any]) -> Dict[str, Any]:
        try:
            procedures = db.get_procedures()
            if not procedures:
                return {"status": "success", "procedures": [], "message": "No procedures found."}

            formatted = []
            for p in procedures:
                formatted.append({
                    "id": p["id"],
                    "name": p["name"],
                    "slug": p["slug"],
                    "url": f"/p/{p['slug']}",
                    "skill_prompt_preview": (p.get("skill_prompt") or "")[:120] + "..." if len(p.get("skill_prompt") or "") > 120 else p.get("skill_prompt"),
                    "completion_condition": p.get("completion_condition"),
                    "created_at": p.get("created_at"),
                })

            return {
                "status": "success",
                "procedures": formatted,
                "count": len(formatted),
                "message": f"Found {len(formatted)} procedure(s)."
            }
        except Exception as e:
            return {"status": "error", "error": f"Failed to list procedures: {str(e)}"}

    return list_procedures


UPDATE_PROCEDURE_SCHEMA = ToolSchema(
    name="update_procedure",
    description="""Update or delete an existing procedure workflow.

Use when the user wants to:
- Change the name or description of a procedure
- Rewrite the AI instruction set (skill_prompt)
- Change the slug / URL
- Delete a procedure permanently

IMPORTANT: Use list_procedures first to get the procedure ID.
To delete permanently: set delete=true.""",
    parameters=make_parameters(
        {
            "procedure_id": {
                "type": "string",
                "description": "The ID of the procedure to update (get from list_procedures)"
            },
            "name": {
                "type": "string",
                "description": "New name for the procedure (optional)"
            },
            "slug": {
                "type": "string",
                "description": "New URL slug for the procedure (optional)"
            },
            "skill_prompt": {
                "type": "string",
                "description": "New AI instruction set for the procedure (optional)"
            },
            "completion_condition": {
                "type": "string",
                "description": "New completion condition marker (optional)"
            },
            "delete": {
                "type": "boolean",
                "description": "Set to true to permanently delete the procedure (cannot be undone)"
            }
        },
        required=["procedure_id"]
    ),
    strict=False
)


def make_update_procedure_tool(db: "DB") -> Callable[[Dict[str, Any]], Dict[str, Any]]:
    def update_procedure(args: Dict[str, Any]) -> Dict[str, Any]:
        procedure_id = args.get("procedure_id")

        procedure = db.get_procedure(procedure_id)
        if not procedure:
            return {
                "status": "error",
                "error": f"Procedure with ID '{procedure_id}' not found. Use list_procedures to see available procedures."
            }

        proc_name = procedure.get("name", procedure_id)

        if args.get("delete"):
            try:
                db.delete_procedure(procedure_id)
                return {
                    "status": "success",
                    "procedure_id": procedure_id,
                    "deleted": True,
                    "message": f"Procedure '{proc_name}' has been deleted permanently."
                }
            except Exception as e:
                return {"status": "error", "error": f"Failed to delete procedure: {str(e)}"}

        name = args.get("name") or procedure["name"]
        skill_prompt = args.get("skill_prompt") or procedure["skill_prompt"]
        completion_condition = args.get("completion_condition") or procedure.get("completion_condition") or "[PROCEDURE_COMPLETE]"

        if args.get("slug"):
            base_slug = _slugify(args["slug"])
            # Only check uniqueness if slug is actually changing
            if base_slug != procedure["slug"]:
                slug = _unique_slug(base_slug, db)
            else:
                slug = procedure["slug"]
        else:
            slug = procedure["slug"]

        try:
            db.update_procedure(procedure_id, name, slug, skill_prompt, completion_condition)
            updated_fields = [k for k in ["name", "slug", "skill_prompt", "completion_condition"] if args.get(k)]
            return {
                "status": "success",
                "procedure_id": procedure_id,
                "name": name,
                "slug": slug,
                "url": f"/p/{slug}",
                "updated_fields": updated_fields,
                "message": f"Procedure '{name}' updated successfully."
            }
        except Exception as e:
            return {"status": "error", "error": f"Failed to update procedure: {str(e)}"}

    return update_procedure
