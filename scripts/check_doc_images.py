#!/usr/bin/env python3
"""Check the images referenced by the markdown documentation of a repository.

Shared by ha-reef-card and ha-reefbeat-component: the same file lives in the
`scripts/` folder of both, and works on any repository of the ecosystem.

Every image reference is resolved to a file when it can be:

  relative path   against the markdown file holding it, as GitHub does
  GitHub URL      raw.githubusercontent.com/<owner>/<repo>/<ref>/<path>,
                  github.com/<owner>/<repo>/raw|blob/<ref>/<path>
                  - the repository being checked: <root>/<path>
                  - another repository: <root>/../<repo>/<path>, when that
                    checkout sits next to this one (as regen.sh expects)
  other URL       not resolved, only probed with --check-remote

Problems reported, each with the file and the line of the reference:

  MISSING   the file does not exist in this repository
  SIBLING   the file does not exist in the sibling checkout it points to
  ABSOLUTE  the path starts with "/", which GitHub resolves against the site
            root (https://github.com/img/...) instead of the repository, so the
            image is broken online even though the file exists locally
  HTTP nnn  a remote image answered with an error (--check-remote only)

A GitHub URL whose ref is not the default branch (`main`) is checked the same
way, against the working tree: what matters here is the path.

Usage, from the repository root or naming it:
    python3 scripts/check_doc_images.py [options] [root-or-files...]

    python3 scripts/check_doc_images.py                        # this repository
    python3 scripts/check_doc_images.py ../ha-reefbeat-component
    python3 scripts/check_doc_images.py README.md doc/fr/README.fr.md
    python3 scripts/check_doc_images.py --check-remote --verbose

Exit code is 1 when at least one problem is found, so the script can be wired
into a pre-commit hook or a CI job.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import unquote, urlsplit

# Markdown ![alt](path "title") and HTML <img src="path">
MD_IMAGE = re.compile(r"!\[[^\]]*\]\(\s*<?([^)\s>]+)")
HTML_IMAGE = re.compile(r"<img[^>]+?src\s*=\s*[\"']([^\"']+)[\"']", re.IGNORECASE)

# Folders never scanned for markdown: dependencies and build output
SKIP_DIRS = {".git", "node_modules", "dist", "build", ".venv", "venv", "__pycache__"}

RESET, RED, YELLOW, GREEN, DIM = (
    "\033[0m",
    "\033[31m",
    "\033[33m",
    "\033[32m",
    "\033[2m",
)


@dataclass(frozen=True)
class Repo:
    """The repository being checked, as GitHub names it."""

    root: Path
    owner: str
    name: str

    def is_self(self, owner: str, name: str) -> bool:
        """Whether a GitHub owner/name designates this repository."""
        return owner.lower() == self.owner.lower() and name.lower() == self.name.lower()


def detect_repo(root: Path, owner: str | None) -> Repo:
    """Name the repository from its `origin` remote, else from its folder."""
    remote_owner = remote_name = None
    try:
        url = subprocess.run(
            ["git", "-C", str(root), "remote", "get-url", "origin"],
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
        # git@github.com:Owner/repo.git or https://github.com/Owner/repo(.git)
        match = re.search(r"github\.com[:/]([^/]+)/([^/]+?)(?:\.git)?/?$", url)
        if match:
            remote_owner, remote_name = match.group(1), match.group(2)
    except (OSError, subprocess.CalledProcessError):
        pass
    return Repo(
        root=root,
        owner=owner or remote_owner or "Elwinmage",
        name=remote_name or root.resolve().name,
    )


def parse_github_url(url: str) -> tuple[str, str, str] | None:
    """Split a GitHub file URL into (owner, repo, path in the repository).

    The ref is dropped: `main`, `refs/heads/main`, a tag or a commit all name
    a version of the same path.
    @return None when the URL is not a GitHub file URL
    """
    parts = urlsplit(url)
    segments = [unquote(s) for s in parts.path.split("/") if s]
    host = parts.netloc.lower()

    if host == "raw.githubusercontent.com" and len(segments) >= 4:
        owner, repo, rest = segments[0], segments[1], segments[2:]
    elif host in ("github.com", "www.github.com") and len(segments) >= 5:
        if segments[2] not in ("raw", "blob"):
            return None
        owner, repo, rest = segments[0], segments[1], segments[3:]
    else:
        return None

    # refs/heads/<branch>/... and refs/tags/<tag>/... carry a two-part prefix
    if len(rest) >= 3 and rest[0] == "refs" and rest[1] in ("heads", "tags"):
        rest = rest[3:]
    else:
        rest = rest[1:]
    if not rest:
        return None
    return owner, repo, "/".join(rest)


def iter_references(path: Path):
    """Yield (line_number, reference) for every image of a markdown file."""
    with path.open(encoding="utf-8") as handle:
        for number, line in enumerate(handle, start=1):
            for match in MD_IMAGE.finditer(line):
                yield number, match.group(1)
            for match in HTML_IMAGE.finditer(line):
                yield number, match.group(1)


def default_targets(root: Path) -> list[Path]:
    """The markdown files of a repository: its root, then `doc/`.

    English first, so the reference README is reported before its
    translations.
    """
    targets = sorted(root.glob("*.md"), key=lambda p: (p.name != "README.md", p.name))
    doc = root / "doc"
    if doc.is_dir():
        targets.extend(
            sorted(
                p
                for p in doc.rglob("*.md")
                if not SKIP_DIRS.intersection(p.relative_to(root).parts)
            )
        )
    return targets


def check(
    path: Path, repo: Repo, check_remote: bool, stats: dict[str, int]
) -> list[tuple[int, str, str]]:
    """Return the problems of one file as (line, kind, reference)."""
    problems: list[tuple[int, str, str]] = []
    for line, ref in iter_references(path):
        target = ref.split("#", 1)[0].split("?", 1)[0]
        if not target or target.startswith("data:"):
            continue

        if target.startswith(("http://", "https://")):
            github = parse_github_url(target)
            if github is None:
                stats["remote"] += 1
                if check_remote:
                    problems.extend(_check_remote(line, target))
                continue
            owner, name, rel = github
            if repo.is_self(owner, name):
                stats["self"] += 1
                if not (repo.root / rel).exists():
                    problems.append((line, "MISSING", ref))
                continue
            sibling = repo.root.resolve().parent / name
            if sibling.is_dir():
                stats["sibling"] += 1
                if not (sibling / rel).exists():
                    problems.append((line, "SIBLING", ref))
                continue
            # No checkout to look into: only the network can tell
            stats["remote"] += 1
            if check_remote:
                problems.extend(_check_remote(line, target))
            continue

        if target.startswith("/"):
            # GitHub resolves this against the site root, never the repository
            problems.append((line, "ABSOLUTE", ref))
            continue
        stats["relative"] += 1
        if not (path.parent / unquote(target)).exists():
            problems.append((line, "MISSING", ref))
    return problems


def _check_remote(line: int, url: str) -> list[tuple[int, str, str]]:
    """Probe a remote image. Network failures are reported, not raised."""
    import urllib.error
    import urllib.request

    request = urllib.request.Request(url, method="HEAD")
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            if response.status >= 400:
                return [(line, f"HTTP {response.status}", url)]
    except urllib.error.HTTPError as err:
        return [(line, f"HTTP {err.code}", url)]
    except Exception as err:
        return [(line, f"UNREACHABLE ({type(err).__name__})", url)]
    return []


def resolve_targets(args: list[str]) -> tuple[Path, list[Path]]:
    """Turn the command line into (repository root, files to check).

    No argument: the current directory is the repository. A directory: it is
    the repository, all its markdown is checked. Files: checked as given,
    against the current directory as repository.
    """
    if not args:
        root = Path.cwd()
        return root, default_targets(root)
    if len(args) == 1 and Path(args[0]).is_dir():
        root = Path(args[0])
        return root, default_targets(root)
    return Path.cwd(), [Path(a) for a in args]


def display(path: Path) -> str:
    """Path as the user can open it from where the script was launched."""
    try:
        return str(path.resolve().relative_to(Path.cwd().resolve()))
    except ValueError:
        return str(path)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "paths",
        nargs="*",
        help="the repository root, or markdown files (default: current directory)",
    )
    parser.add_argument(
        "--check-remote",
        action="store_true",
        help="probe the URLs that cannot be resolved to a local file",
    )
    parser.add_argument(
        "--owner",
        help="GitHub owner of the repository (default: from the origin remote)",
    )
    parser.add_argument(
        "--verbose", action="store_true", help="list clean files and a breakdown"
    )
    args = parser.parse_args()

    root, targets = resolve_targets(args.paths)
    repo = detect_repo(root, args.owner)
    print(f"{DIM}repository {repo.owner}/{repo.name} at {display(root)}{RESET}")

    stats = {"relative": 0, "self": 0, "sibling": 0, "remote": 0}
    total = 0
    for path in targets:
        if not path.exists():
            print(f"{RED}no such file: {path}{RESET}")
            total += 1
            continue
        problems = check(path, repo, args.check_remote, stats)
        if not problems:
            if args.verbose:
                print(f"{GREEN}✓{RESET} {display(path)}")
            continue
        total += len(problems)
        print(f"{RED}✗{RESET} {display(path)} {DIM}({len(problems)}){RESET}")
        width = max(len(kind) for _, kind, _ in problems)
        for line, kind, ref in problems:
            color = RED if kind in ("MISSING", "SIBLING") else YELLOW
            # "path:line:" is the format editors and CI logs can jump to
            print(f"   {display(path)}:{line}: {color}{kind:<{width}}{RESET}  {ref}")

    print()
    if args.verbose or stats["remote"]:
        remote = "probed" if args.check_remote else "skipped, use --check-remote"
        print(
            f"{DIM}{len(targets)} file(s): {stats['relative']} relative, "
            f"{stats['self']} URL(s) to this repository, "
            f"{stats['sibling']} to a sibling checkout, "
            f"{stats['remote']} other URL(s) ({remote}){RESET}"
        )
    if total:
        print(f"{RED}{total} problem(s) found{RESET}")
        return 1
    print(f"{GREEN}all images resolve{RESET}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
