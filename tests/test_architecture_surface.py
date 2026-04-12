from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_architecture_decision_doc_exists_and_is_linked_from_readme():
    doc = ROOT / "docs" / "ARCHITECTURE_DECISION.md"
    assert doc.exists()

    content = doc.read_text(encoding="utf-8")
    assert "shared-contract product family" in content
    assert "`pyspider` is the reference runtime" in content
    assert "contract symmetry" in content
    assert "implementation symmetry" in content

    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "docs/ARCHITECTURE_DECISION.md" in readme
