import shutil
from pathlib import Path


def cleanup_run_workspace(workspace_root: Path) -> None:
    shutil.rmtree(workspace_root, ignore_errors=True)


def ensure_within_workspace(workspace_root: Path, candidate_path: Path) -> Path:
    resolved_workspace = workspace_root.resolve()
    candidate = candidate_path if candidate_path.is_absolute() else resolved_workspace / candidate_path
    resolved_candidate = candidate.resolve(strict=False)

    try:
        resolved_candidate.relative_to(resolved_workspace)
    except ValueError as exc:
        raise ValueError("candidate path is outside workspace") from exc

    return resolved_candidate
