import pytest

from app.knowledge.processing import chunk_text, extract_text, validate_upload


def test_chunk_text_splits_long_body():
    text = "word " * 900
    chunks = chunk_text(text)
    assert len(chunks) >= 2
    assert all(c.content for c in chunks)


def test_chunk_text_respects_heading():
    text = "# Policy\n\nFirst paragraph.\n\n# Another\n\nSecond paragraph."
    chunks = chunk_text(text)
    assert any(c.heading == "Policy" for c in chunks)


def test_extract_markdown():
    content = extract_text("guide.md", b"# Title\n\nBody text.")
    assert "Title" in content


def test_extract_faq_csv():
    csv_data = b"question,answer\nWhat is PO?,Purchase order.\n"
    content = extract_text("faq.csv", csv_data)
    assert "Q: What is PO?" in content
    assert "Purchase order" in content


def test_validate_rejects_bad_extension():
    with pytest.raises(ValueError, match="Unsupported"):
        validate_upload("file.exe", 100)
