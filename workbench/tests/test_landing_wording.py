"""Paper B is the journal version of the preprint, not an extension of it (CP26-E1)."""
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "viewer/src"
FOOTER = ("Paper B, the journal version in preparation, evaluates the method as a scoring "
          "instrument on a 42-country cohort; this workbench is its companion.")
BANNED = ("extends the method", "sequel", "follow-up study", "Paper B builds on")


def test_footer_states_journal_version():
    assert FOOTER in (SRC / "landing.ts").read_text()


def test_no_extension_phrasing_about_paper_b():
    for path in SRC.glob("*.ts"):
        text = path.read_text()
        for phrase in BANNED:
            assert phrase not in text, f"{path.name}: {phrase!r}"


def test_preprint_citations_kept():
    assert "arXiv:2610.06562" in (SRC / "landing.ts").read_text()
    assert "arXiv:2610.06562" in (SRC / "common.ts").read_text()
