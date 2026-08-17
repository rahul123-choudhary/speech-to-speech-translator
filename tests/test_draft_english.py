from pathlib import Path

from s2st.draft_english import MODEL_NAME, write_drafts


def test_machine_drafts_are_not_marked_as_approved(tmp_path: Path) -> None:
    output = tmp_path / "drafts.tsv"
    write_drafts([{"id": "item", "english_reference": "Hello"}], output, MODEL_NAME)
    fields = output.read_text(encoding="utf-8").splitlines()[1].split("\t")
    assert fields[3] == ""
    assert fields[4] == "machine_draft"
