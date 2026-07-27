from __future__ import annotations

import os
from pathlib import Path

from zhihuflow.core.schemas import SandboxArtifact, new_id


class SandboxViolation(ValueError):
    pass


class LocalSandbox:
    """A conservative local artifact sandbox.

    This is not a process sandbox. It is a safe workspace boundary for skills and
    tools that need to write files. Process isolation can be added later behind
    the same interface.
    """

    def __init__(self, root: str = ".zhihuflow/sandbox") -> None:
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def resolve(self, relative_path: str) -> Path:
        if os.path.isabs(relative_path):
            raise SandboxViolation("absolute paths are not allowed in sandbox")
        candidate = (self.root / relative_path).resolve()
        if self.root not in candidate.parents and candidate != self.root:
            raise SandboxViolation("path escapes sandbox root")
        return candidate

    def write_text(self, relative_path: str, content: str) -> SandboxArtifact:
        path = self.resolve(relative_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return SandboxArtifact(
            artifact_id=new_id("sandbox"),
            relative_path=str(path.relative_to(self.root)),
            bytes_written=len(content.encode("utf-8")),
        )

    def read_text(self, relative_path: str) -> str:
        return self.resolve(relative_path).read_text(encoding="utf-8")
