from typing import List

__version__ = "v1.2.2-beta.2"
GITHUB_REPO_URL = "https://github.com/incconutwo/mouse-battery-tray"
GITHUB_RELEASES_API = "https://api.github.com/repos/incconutwo/mouse-battery-tray/releases/latest"
GITHUB_RELEASES_URL = "https://github.com/incconutwo/mouse-battery-tray/releases/latest"


def is_newer_version(latest: str, current: str) -> bool:
    """Compare semver string tags reliably (e.g. 'v1.1.0' > 'v1.0.0', 'v1.1.0-beta1' vs 'v1.0.0')."""
    def parse(v: str) -> List[int]:
        v = v.lstrip('vV').split('-')[0].split('+')[0]
        parts = []
        for p in v.split('.'):
            try:
                parts.append(int(p))
            except ValueError:
                parts.append(0)
        return parts
    return parse(latest) > parse(current)
