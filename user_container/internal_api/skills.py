"""Internal API - skill execution for apps."""
import subprocess
import json
import re
from pathlib import Path
from typing import Dict, Any, List, Set

from user_container.db.db import DB
from user_container.usage.skill_tracker import track_skill_usage

SKILL_BLACKLIST: Set[str] = {"app-deploy", "frontend-design", "web-app-builder"}
SKILLS_DIR = Path("/app/user_container/skills")


def get_allowed_skills() -> Set[str]:
    """Dynamiczny whitelist - skanuje katalog skills/"""
    return {
        d.name for d in SKILLS_DIR.iterdir()
        if d.is_dir() and (d / "SKILL.md").exists()
    } - SKILL_BLACKLIST


def list_skills() -> List[Dict[str, Any]]:
    """Zwraca listę dostępnych skilli z opisami i skryptami."""
    result = []
    for skill_name in get_allowed_skills():
        skill_dir = SKILLS_DIR / skill_name
        skill_md = skill_dir / "SKILL.md"
        scripts_dir = skill_dir / "scripts"

        # Parse YAML frontmatter from SKILL.md
        description = ""
        try:
            content = skill_md.read_text()
            # Extract description from frontmatter
            match = re.search(
                r'^---\s*\n.*?description:\s*["\']?(.+?)["\']?\s*\n.*?---',
                content,
                re.DOTALL
            )
            if match:
                description = match.group(1).strip().strip('"\'')
        except Exception:
            pass

        # List available scripts
        scripts = []
        if scripts_dir.exists():
            scripts = [f.stem for f in scripts_dir.glob("*.py") if f.is_file()]

        result.append({
            "name": skill_name,
            "description": description,
            "scripts": scripts,
            "docs_path": str(skill_md)  # Path to SKILL.md for detailed docs
        })

    return sorted(result, key=lambda x: x["name"])


def execute_skill(
    skill: str,
    script: str,
    args: Dict[str, Any],
    app_id: str,
    db: DB
) -> Dict[str, Any]:
    """Wykonaj skill i trackuj usage."""
    # 1. Walidacja
    if skill not in get_allowed_skills():
        return {"status": "error", "error": f"Skill '{skill}' not allowed"}

    script_path = Path(f"/app/user_container/skills/{skill}/scripts/{script}.py")
    if not script_path.exists():
        return {"status": "error", "error": f"Script '{script}' not found"}

    # 2. Zbuduj komendę
    cmd = ["uv", "run", str(script_path)]
    for k, v in args.items():
        cmd.extend([f"--{k.replace('_', '-')}", str(v)])

    # 4. Wykonaj
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120,
            cwd="/app"
        )
    except subprocess.TimeoutExpired:
        return {"status": "error", "error": "Skill execution timeout"}

    if result.returncode != 0:
        return {"status": "error", "error": result.stderr or "Skill execution failed"}

    try:
        output = json.loads(result.stdout)
    except json.JSONDecodeError:
        return {"status": "error", "error": "Invalid skill output"}

    # 5. Trackuj usage (automatycznie dedukcja z balance)
    track_skill_usage(
        tool_name="shell",
        args={"cmd": " ".join(cmd)},
        output=output,
        job_id=None,
        conversation_id=None,
        component=f"app:{app_id}"
    )

    return {"status": "success", "result": output}
