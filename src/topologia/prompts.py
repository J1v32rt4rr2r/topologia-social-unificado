from pathlib import Path


class PromptLoader:
    def __init__(self, prompts_dir: str | None = None):
        if prompts_dir:
            self.base = Path(prompts_dir)
        else:
            self.base = Path(__file__).resolve().parent.parent.parent / "prompts"

    def load(self, name: str, **kwargs) -> str:
        path = self.base / f"{name}.md"
        if not path.exists():
            raise FileNotFoundError(f"Prompt file not found: {path}")
        content = path.read_text(encoding="utf-8")
        for key, value in kwargs.items():
            content = content.replace(f"{{{key}}}", str(value))
        return content
