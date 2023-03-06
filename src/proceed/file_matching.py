from pathlib import Path
import hashlib

def match_files(dir: str, glob_pattern: str) -> dict[str, str]:
    """Search the given dir using the given "glob" pattern, return matched files with their content digests."""
    matches = Path(dir).glob(glob_pattern)
    return {path.relative_to(dir).as_posix(): hash_contents(path) for path in matches}


def hash_contents(path: Path, algorithm: str = "sha256") -> str:
    """Hash the file contents at the given path, return hex-encoded digest prefixed with the algorignm name."""
    with open(path, "rb") as f:
        digest = hashlib.file_digest(f, algorithm)
    return f"{digest.name}:{digest.hexdigest()}"
