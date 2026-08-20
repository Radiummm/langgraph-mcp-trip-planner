"""读取 Markdown skill，并按用户输入匹配。"""

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Iterable

from ..models.schemas import TripRequest


@dataclass(frozen=True)
class TravelSkill:
    name: str
    keywords: tuple[str, ...]
    body: str


SKILL_DIR = Path(__file__).with_name("skills")


def build_skill_context(request: TripRequest) -> str:
    text = " ".join([*request.preferences, request.free_text_input or ""])
    matched = [skill for skill in _load_skills() if _matches(text, skill.keywords)]
    if not matched:
        return "无"

    return "\n\n".join(f"### {skill.name}\n{skill.body}" for skill in matched)


def _matches(text: str, keywords: Iterable[str]) -> bool:
    return any(keyword in text for keyword in keywords)


@lru_cache(maxsize=1)
def _load_skills() -> tuple[TravelSkill, ...]:
    return tuple(_parse_skill(path) for path in sorted(SKILL_DIR.glob("*.md")))


def _parse_skill(path: Path) -> TravelSkill:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        raise ValueError(f"{path} 缺少YAML frontmatter")

    _, header, body = text.split("---", 2)
    meta = _parse_frontmatter(header)
    return TravelSkill(
        name=meta.get("name", path.stem),
        keywords=tuple(meta.get("keywords", [])),
        body=body.strip(),
    )


def _parse_frontmatter(header: str) -> dict[str, str | list[str]]:
    # ponytail: 只解析本项目skill用到的YAML子集；需要完整YAML时再引入PyYAML。
    meta: dict[str, str | list[str]] = {}
    current_key = ""
    for line in header.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("- ") and current_key:
            values = meta.setdefault(current_key, [])
            if isinstance(values, list):
                values.append(stripped[2:].strip())
            continue
        if ":" in stripped:
            key, value = stripped.split(":", 1)
            current_key = key.strip()
            meta[current_key] = value.strip() or []
    return meta


def _demo() -> None:
    request = TripRequest(
        city="北京",
        start_date="2026-07-01",
        end_date="2026-07-03",
        travel_days=3,
        transportation="公共交通",
        accommodation="经济型酒店",
        preferences=["历史文化", "美食"],
        free_text_input="带老人同行，不要太赶",
    )
    context = build_skill_context(request)
    assert "慢节奏同行" in context
    assert "美食优先" in context
    assert "文化深度" in context


if __name__ == "__main__":
    _demo()
