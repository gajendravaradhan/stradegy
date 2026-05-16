from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import json
from loguru import logger

from stradegy.config import settings


@dataclass
class Skill:
    name: str
    strategy_params: dict[str, Any]
    quality_gates: dict[str, float]
    score: float = 0.0
    version: str = "1.0"
    is_active: bool = True


class Skillbook:
    def __init__(self, path: Path | None = None):
        self.path = path or (settings.eval_dir / "skillbook.jsonl")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._skills: dict[str, Skill] = {}
        self._load()

    def _load(self) -> None:
        if not self.path.exists():
            return
        try:
            with self.path.open("r") as f:
                for line in f:
                    if line.strip():
                        obj = json.loads(line)
                        skill = Skill(**obj)
                        self._skills[skill.name] = skill
        except Exception as e:
            logger.error(f"Failed to load skillbook: {e}")

    def _save(self) -> None:
        try:
            with self.path.open("w") as f:
                for skill in self._skills.values():
                    f.write(json.dumps(asdict(skill)) + "\n")
        except Exception as e:
            logger.error(f"Failed to save skillbook: {e}")

    def add(self, skill: Skill) -> None:
        self._skills[skill.name] = skill
        self._save()

    def get(self, name: str) -> Skill | None:
        return self._skills.get(name)

    def list_active(self) -> list[Skill]:
        return [s for s in self._skills.values() if s.is_active]

    def evaluate(self, name: str, metrics: dict[str, float]) -> bool:
        skill = self._skills.get(name)
        if not skill:
            return False
        for gate, threshold in skill.quality_gates.items():
            if gate in metrics and metrics[gate] < threshold:
                return False
        return True

    def promote(self, name: str, score: float) -> None:
        skill = self._skills.get(name)
        if skill:
            skill.score = max(skill.score, score)
            skill.is_active = True
            self._save()

    def demote(self, name: str) -> None:
        skill = self._skills.get(name)
        if skill:
            skill.is_active = False
            self._save()

    def best_skill(self) -> Skill | None:
        active = self.list_active()
        if not active:
            return None
        return max(active, key=lambda s: s.score)
