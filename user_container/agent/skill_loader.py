import json
import os
import re
from typing import List, Optional, Dict
from dataclasses import dataclass, field

@dataclass
class Skill:
    name: str
    description: str
    instructions: str
    path: str
    required_secrets: List[str] = field(default_factory=list)
    secrets_status: Dict[str, bool] = field(default_factory=dict)

class SkillLoader:
    """
    Loads skills from the filesystem (built-in) and SQLite DB (custom).
    """

    def __init__(self, skills_dir: str = "user_container/skills", db=None):
        # Resolve to absolute path to avoid ambiguity
        self.skills_dir = os.path.abspath(skills_dir)
        self.db = db
        self._skills_cache: Dict[str, Skill] = {}

    def load_skill(self, skill_name: str) -> Skill:
        """Loads a skill by name, checking filesystem first then DB."""
        if skill_name in self._skills_cache:
            return self._skills_cache[skill_name]

        # Check filesystem (built-in skills)
        skill_path = os.path.join(self.skills_dir, skill_name)
        manifest_path = os.path.join(skill_path, "SKILL.md")
        if os.path.exists(manifest_path):
            with open(manifest_path, "r", encoding="utf-8") as f:
                raw_content = f.read()

            name, description, instructions = self._parse_markdown(raw_content)
            final_name = name or skill_name

            skill = Skill(
                name=final_name,
                description=description or f"Skill loaded from {skill_name}",
                instructions=instructions,
                path=skill_path
            )

            self._skills_cache[skill_name] = skill
            return skill

        # Check DB (custom skills)
        if self.db:
            row = self.db.get_custom_skill(skill_name)
            if row:
                required_secrets = []
                secrets_status = {}
                req_raw = row.get("required_secrets")
                if req_raw:
                    try:
                        required_secrets = json.loads(req_raw)
                    except (json.JSONDecodeError, TypeError):
                        pass
                if required_secrets:
                    secrets_status = self.db.get_skill_secrets_status(skill_name)

                skill = Skill(
                    name=row["name"],
                    description=row.get("description") or "",
                    instructions=row["instructions"],
                    path=os.path.join(self.skills_dir, "_custom", skill_name),
                    required_secrets=required_secrets,
                    secrets_status=secrets_status,
                )
                self._skills_cache[skill_name] = skill
                return skill

        raise ValueError(f"Skill '{skill_name}' not found in any skills directory")

    def list_available_skills(self) -> List[Dict[str, str]]:
        """
        Scans filesystem skills directory and DB custom skills.
        Returns a list of available skills with names and descriptions.
        """
        skills = []
        seen = set()

        # Filesystem built-in skills
        if os.path.exists(self.skills_dir):
            for item in os.listdir(self.skills_dir):
                skill_path = os.path.join(self.skills_dir, item)
                if os.path.isdir(skill_path) and os.path.exists(os.path.join(skill_path, "SKILL.md")):
                    try:
                        skill = self.load_skill(item)
                        skills.append({
                            "name": skill.name,
                            "description": skill.description
                        })
                        seen.add(item)
                    except Exception:
                        continue

        # DB custom skills
        if self.db:
            for row in self.db.get_custom_skills():
                skill_id = row["id"]
                if skill_id not in seen:
                    skills.append({
                        "name": skill_id,
                        "description": row.get("description") or ""
                    })
                    seen.add(skill_id)

        return skills

    def clear_cache(self, skill_name: str = None):
        """Clear cached skills. If skill_name is given, only clear that one."""
        if skill_name:
            self._skills_cache.pop(skill_name, None)
        else:
            self._skills_cache.clear()

    def get_skill_prompts(self, skill_names: List[str]) -> str:
        """
        Returns combined instructions for the system prompt.
        """
        if not skill_names:
            return ""

        blocks = ["\n# AVAILABLE SKILLS\n"]

        for name in skill_names:
            try:
                skill = self.load_skill(name)
                # We inject the absolute path so the model knows where scripts are
                blocks.append(f"## SKILL: {skill.name.upper()}")
                blocks.append(f"Location: {skill.path}")
                secrets_block = self._build_secrets_block(skill)
                if secrets_block:
                    blocks.append(secrets_block)
                blocks.append(skill.instructions)
                blocks.append("\n" + "-"*30 + "\n")
            except Exception as e:
                blocks.append(f"!! Error loading skill '{name}': {e}")

        return "\n".join(blocks)

    def _build_secrets_block(self, skill: Skill) -> str:
        """Build a prompt block describing secret/env var status for a skill."""
        if not skill.required_secrets:
            return ""

        all_configured = all(name in skill.secrets_status for name in skill.required_secrets)

        lines = ["\n### Environment Variables"]
        if all_configured:
            lines.append("These are automatically available when running this skill's scripts. Do NOT ask the user for these values.")
        else:
            lines.append("This skill requires the following environment variables. Variables marked NOT CONFIGURED must be set by the user in Settings > Skills before the skill can work.")

        for name in skill.required_secrets:
            status = "configured" if name in skill.secrets_status else "NOT CONFIGURED"
            lines.append(f"- {name}: {status}")

        return "\n".join(lines)

    def _parse_markdown(self, content: str) -> tuple[Optional[str], Optional[str], str]:
        """
        Parses YAML frontmatter from markdown.
        Returns (name, description, markdown_content).
        """
        # Regex to find frontmatter between --- and ---
        frontmatter_pattern = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)
        match = frontmatter_pattern.match(content)

        name = None
        description = None
        instructions = content

        if match:
            frontmatter_raw = match.group(1)
            instructions = content[match.end():] # Everything after the second ---

            # Simple line-by-line parser for "key: value"
            for line in frontmatter_raw.split('\n'):
                if ':' in line:
                    key, val = line.split(':', 1)
                    key = key.strip()
                    val = val.strip().strip('"\'')

                    if key == 'name':
                        name = val
                    elif key == 'description':
                        description = val

        return name, description, instructions.strip()
