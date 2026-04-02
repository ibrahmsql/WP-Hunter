from pathlib import Path


def build_tool_policy(workspace_root: Path) -> dict[str, object]:
    return {
        "workspace_root": str(workspace_root.resolve()),
        "enforcement": "handled_by_open_multi_agent",
    }
