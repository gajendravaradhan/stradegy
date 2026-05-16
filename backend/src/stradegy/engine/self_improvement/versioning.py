from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import json
from loguru import logger

from stradegy.config import settings


@dataclass
class StrategyVersion:
    version_id: str
    timestamp: str
    strategy_name: str
    params: dict[str, Any]
    metrics: dict[str, float]
    parent_version: str | None = None


class VersionManager:
    def __init__(self, path: Path | None = None):
        self.path = path or (settings.eval_dir / "versions.jsonl")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._versions: list[StrategyVersion] = []
        self._load()

    def _load(self) -> None:
        if not self.path.exists():
            return
        try:
            with self.path.open("r") as f:
                for line in f:
                    if line.strip():
                        obj = json.loads(line)
                        self._versions.append(StrategyVersion(**obj))
        except Exception as e:
            logger.error(f"Failed to load versions: {e}")

    def _save(self) -> None:
        try:
            with self.path.open("w") as f:
                for v in self._versions:
                    f.write(json.dumps(asdict(v)) + "\n")
        except Exception as e:
            logger.error(f"Failed to save versions: {e}")

    def save(self, version: StrategyVersion) -> None:
        self._versions.append(version)
        self._save()

    def list_versions(self, strategy_name: str) -> list[StrategyVersion]:
        return [v for v in self._versions if v.strategy_name == strategy_name]

    def get_latest(self, strategy_name: str) -> StrategyVersion | None:
        versions = self.list_versions(strategy_name)
        return versions[-1] if versions else None

    def rollback_params(self, strategy_name: str, version_id: str | None = None) -> dict[str, Any] | None:
        versions = self.list_versions(strategy_name)
        if not versions:
            return None
        if version_id:
            for v in versions:
                if v.version_id == version_id:
                    return v.params
            return None
        return versions[-1].params
