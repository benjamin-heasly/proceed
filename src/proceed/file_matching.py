from pathlib import Path
import hashlib


def match_all(dirs: list[str], glob_patterns: list[str])-> dict[str, dict[str, str]]:
    """Search each given dir using each given "glob" pattern, return matched files, with content digests, per dir."""
    matches = {}
    for dir in dirs:
        dir_matches = {}
        for glob_pattern in glob_patterns:
            dir_glob_matches = match_files(dir, glob_pattern)
            dir_matches.update(dir_glob_matches)
        if dir_matches:
            matches[dir] = dir_matches
    return matches


def match_files(dir: str, glob_pattern: str) -> dict[str, str]:
    """Search the given dir using the given "glob" pattern, return matched files with their content digests."""
    matches = Path(dir).glob(glob_pattern)
    return {path.relative_to(dir).as_posix(): hash_contents(path) for path in matches}


def hash_contents(path: Path, algorithm: str = "sha256") -> str:
    """Hash the file contents at the given path, return hex-encoded digest prefixed with the algorignm name."""
    with open(path, "rb") as f:
        digest = hashlib.file_digest(f, algorithm)
    return f"{digest.name}:{digest.hexdigest()}"
