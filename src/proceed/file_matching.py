import logging
import hashlib
from pathlib import Path


def match_patterns_in_dirs(dirs: list[str], glob_patterns: list[str])-> dict[str, dict[str, str]]:
    """Search each given dir using each given "glob" pattern, return matched files, with content digests, per dir."""
    matches = {}
    for dir in dirs:
        dir_matches = {}
        for glob_pattern in glob_patterns:
            dir_glob_matches = match_pattern_in_dir(dir, glob_pattern)
            dir_matches.update(dir_glob_matches)
        if dir_matches:
            matches[dir] = dir_matches
    return matches


def match_pattern_in_dir(dir: str, glob_pattern: str) -> dict[str, str]:
    """Search the given dir using the given "glob" pattern, return matched files with their content digests."""
    matches = Path(dir).glob(glob_pattern)
    file_matches = [match for match in matches if match.is_file()]
    return {path.relative_to(dir).as_posix(): hash_contents(path) for path in file_matches}


def hash_contents(path: Path, algorithm: str = "sha256") -> str:
    """Hash the file contents at the given path, return hex-encoded digest prefixed with the algorignm name."""
    logging.info(f"Computing content hash ({algorithm}) for file: {path.as_posix()}")
    with open(path, "rb") as f:
        digest = hashlib.file_digest(f, algorithm)
    return f"{digest.name}:{digest.hexdigest()}"


def count_matches(matches: dict[str, dict[str, str]]) -> int:
    return sum(len(dir_matches) for dir_matches in matches.values())


def flatten_matches(matches: dict[str, dict[str, str]]) -> list[tuple[str, str]]:
    flattened = []
    for volume, file_info in matches.items():
        for path, digest in file_info.items():
            # TODO keep volume and path separate, so that host-specific volume is easy to ignore
            volume_path = Path(volume, path)
            flat = (volume_path.as_posix(), digest)
            flattened.append(flat)
    return flattened
