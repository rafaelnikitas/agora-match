"""Build the click-to-open static web app from the deterministic demo catalog."""

import shutil
from pathlib import Path

from .build_static import main as build_static_data


def main() -> None:
    project_root = Path(__file__).resolve().parent.parent
    output = project_root / "dist"
    if output.is_symlink() or output.resolve().parent != project_root:
        raise RuntimeError("dist must be a regular directory inside the project")
    build_static_data()
    if output.exists():
        shutil.rmtree(output)
    shutil.copytree(project_root / "static", output)
    print(f"Built click-to-open site at {output}")


if __name__ == "__main__":
    main()
