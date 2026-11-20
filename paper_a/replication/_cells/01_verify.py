from pathlib import Path
import hashlib
import json


def find_repo(start: Path) -> Path:
    for cand in [start, *start.parents]:
        if (cand / "paper_a" / "replication" / "HASHES.md").is_file():
            return cand
    raise FileNotFoundError(
        "paper_a/replication/HASHES.md not found. Run from the repository root."
    )


REPO = find_repo(Path.cwd())
HASHES = REPO / "paper_a" / "replication" / "HASHES.md"


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

# A public checkout carries declared redactions (PUBLIC_REDACTIONS.md: private sha -> public sha). A redacted file
# passes when its private sha is the one HASHES.md expects and its bytes match the recorded public sha.
redacted = {}
REDACTIONS = REPO / "PUBLIC_REDACTIONS.md"
if REDACTIONS.is_file():
    for line in REDACTIONS.read_text().splitlines():
        cells = [c.strip().strip("`") for c in line.strip().strip("|").split("|")]
        if len(cells) >= 3 and len(cells[1]) == 64 and len(cells[2]) == 64:
            redacted[cells[0]] = (cells[1], cells[2])

missing, mismatch, ok, via_redaction = [], [], [], []
for rel, digest in sorted(expected.items()):
    path = REPO / rel
    if not path.exists():
        missing.append(rel)
        continue
    got = sha256(path)
    if got == digest:
        ok.append(rel)
    elif rel in redacted and redacted[rel] == (digest, got):
        via_redaction.append(rel)
    else:
        mismatch.append({"path": rel, "expected": digest[:12], "got": got[:12]})

print(json.dumps({"ok": len(ok), "ok_via_declared_redaction": via_redaction, "missing": missing,
                  "mismatch": mismatch}, indent=2))
if missing or mismatch:
    raise SystemExit("Tier A failed.")
print("Tier A passed.")
