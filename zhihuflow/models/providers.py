from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional, Protocol


class ModelProvider(Protocol):
    def generate(self, system: str, prompt: str, *, temperature: float = 0.4) -> str:
        ...

    @property
    def model_id(self) -> str:
        ...


def load_env_file(path: str) -> dict[str, str]:
    """Load KEY=VALUE pairs without printing or exporting secrets to logs."""
    env_path = Path(path).expanduser()
    loaded: dict[str, str] = {}
    if not env_path.exists():
        raise FileNotFoundError(str(env_path))
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if not key:
            continue
        os.environ.setdefault(key, value)
        loaded[key] = value
    return loaded


@dataclass
class DeterministicModel:
    """Offline model substitute for demos, tests, and interviews."""

    @property
    def model_id(self) -> str:
        return "deterministic-agent"

    def generate(self, system: str, prompt: str, *, temperature: float = 0.4) -> str:
        lines = [line.strip("- ").strip() for line in prompt.splitlines() if line.strip()]
        topic = next((line for line in lines if "话题" in line or "topic" in line.lower()), lines[0] if lines else "AI Agent")
        return (
            f"{topic}\n\n"
            "核心判断：这个方向的价值不在于把模型包装得更像人，而在于把搜索、证据、记忆、工具契约和人工确认做成稳定运行时。"
            "如果缺少证据链和可回放日志，所谓 Agent 很容易退化成一次性内容生成器。"
        )


@dataclass
class OpenAICompatibleModel:
    """Tiny OpenAI-compatible chat client using only the standard library."""

    api_key: str
    base_url: str
    model: str
    provider_name: str = "openai-compatible"

    @property
    def model_id(self) -> str:
        return f"{self.provider_name}:{self.model}"

    @classmethod
    def from_env(cls) -> Optional["OpenAICompatibleModel"]:
        api_key = os.getenv("ZHIHUFLOW_OPENAI_API_KEY")
        base_url = os.getenv("ZHIHUFLOW_OPENAI_BASE_URL", "https://api.openai.com/v1")
        model = os.getenv("ZHIHUFLOW_OPENAI_MODEL", "gpt-4o-mini")
        if not api_key:
            return None
        return cls(api_key=api_key, base_url=base_url.rstrip("/"), model=model, provider_name="openai-compatible")

    def generate(self, system: str, prompt: str, *, temperature: float = 0.4) -> str:
        payload: dict[str, Any] = {
            "model": self.model,
            "temperature": temperature,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
        }
        request = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=45) as response:
                data = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"{self.provider_name} request failed: {exc.code} {detail[:300]}") from exc
        return data["choices"][0]["message"]["content"]


@dataclass
class BailianModel(OpenAICompatibleModel):
    """Alibaba Cloud Bailian / DashScope OpenAI-compatible chat model."""

    provider_name: str = "aliyun-bailian"

    @classmethod
    def from_env(cls) -> Optional["BailianModel"]:
        api_key = os.getenv("ALIBABA_CLOUD_BAILIAN_API_KEY") or os.getenv("DASHSCOPE_API_KEY")
        model = os.getenv("ZHIHUFLOW_BAILIAN_MODEL") or os.getenv("SOLOOPS_MODEL_NAME") or "qwen-plus"
        base_url = os.getenv("ZHIHUFLOW_BAILIAN_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
        if not api_key:
            return None
        return cls(api_key=api_key, base_url=base_url.rstrip("/"), model=model)


def model_from_env(provider: Optional[str] = None) -> ModelProvider:
    requested = (provider or os.getenv("ZHIHUFLOW_MODEL_PROVIDER") or os.getenv("SOLOOPS_MODEL_PROVIDER") or "").lower()
    if requested in {"aliyun_bailian", "bailian", "dashscope", "aliyun-bailian"}:
        return BailianModel.from_env() or DeterministicModel()
    if requested in {"openai", "openai-compatible", "openai_compatible"}:
        return OpenAICompatibleModel.from_env() or DeterministicModel()
    return BailianModel.from_env() or OpenAICompatibleModel.from_env() or DeterministicModel()


def default_model() -> ModelProvider:
    return model_from_env()
