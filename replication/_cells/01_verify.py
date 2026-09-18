from pathlib import Path
import hashlib
import json

cwd = Path.cwd()
if (cwd / "HASHES.md").exists():
    REPO = cwd.parent
elif (cwd / "replication" / "HASHES.md").exists():
    REPO = cwd
else:
    raise FileNotFoundError("Run from the repository root or replication/")

HASHES = REPO / "replication" / "HASHES.md"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


expected = {}
for line in HASHES.read_text().splitlines():
    if len(line) > 66 and line[64:66] == "  ":
        expected[line[66:].strip()] = line[:64]

missing, mismatch, ok = [], [], []
for rel, digest in sorted(expected.items()):
    path = REPO / rel
    if not path.exists():
        missing.append(rel)
        continue
    got = sha256(path)
    if got != digest:
        mismatch.append({"path": rel, "expected": digest[:12], "got": got[:12]})
    else:
        ok.append(rel)

print(json.dumps({"ok": len(ok), "missing": missing, "mismatch": mismatch}, indent=2))
if missing or mismatch:
    raise SystemExit("Tier A failed.")
print("Tier A passed.")
