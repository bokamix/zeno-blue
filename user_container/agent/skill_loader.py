import os
import re
from typing import List, Optional, Dict
from dataclasses import dataclass

@dataclass
class Skill:
    name: str
    description: str
    instructions: str
    path: str

class SkillLoader:
    """
    Loads skills from the filesystem (Anthropic-style).
    Expects structure:
    /skills_dir
      /skill_name
        SKILL.md
        scripts/...
    """
    
    def __init__(self, skills_dir: str = "user_container/skills"):
        # Resolve to absolute path to avoid ambiguity
        self.skills_dir = os.path.abspath(skills_dir)
        self._skills_cache: Dict[str, Skill] = {}

    def load_skill(self, skill_name: str) -> Skill:
        """Loads a skill by name, parsing SKILL.md."""
        if skill_name in self._skills_cache:
            return self._skills_cache[skill_name]

        skill_path = os.path.join(self.skills_dir, skill_name)
        manifest_path = os.path.join(skill_path, "SKILL.md")

        if not os.path.exists(manifest_path):
            raise ValueError(f"Skill '{skill_name}' not found at {skill_path}")

        with open(manifest_path, "r", encoding="utf-8") as f:
            raw_content = f.read()

        name, description, instructions = self._parse_markdown(raw_content)
        
        # If name is missing in frontmatter, use folder name
        final_name = name or skill_name
        
        skill = Skill(
            name=final_name,
            description=description or f"Skill loaded from {skill_name}",
            instructions=instructions,
            path=skill_path
        )
        
        self._skills_cache[skill_name] = skill
        return skill

    def list_available_skills(self) -> List[Dict[str, str]]:
        """
        Scans the skills directory and returns a list of available skills
        with their names and descriptions (from SKILL.md).
        """
        skills = []
        if not os.path.exists(self.skills_dir):
            return []

        for item in os.listdir(self.skills_dir):
            skill_path = os.path.join(self.skills_dir, item)
            if os.path.isdir(skill_path) and os.path.exists(os.path.join(skill_path, "SKILL.md")):
                try:
                    # Load light version (just parse frontmatter) to get description
                    # We could reuse load_skill but that reads full file
                    # Optimally we cache this
                    skill = self.load_skill(item)
                    skills.append({
                        "name": skill.name,
                        "description": skill.description
                    })
                except Exception:
                    # Skip malformed skills
                    continue
        return skills

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
                blocks.append(skill.instructions)
                blocks.append("\n" + "-"*30 + "\n")
            except Exception as e:
                blocks.append(f"!! Error loading skill '{name}': {e}")
                
        return "\n".join(blocks)

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

