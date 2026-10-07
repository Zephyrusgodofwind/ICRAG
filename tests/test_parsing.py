from irishclinicalrag.parsing.documents import normalize_extracted_text


def test_private_use_pdf_bullets_are_normalized() -> None:
    assert normalize_extracted_text("\uf0b7 Recommendation\n\uf0a7 Evidence") == (
        "• Recommendation\n• Evidence"
    )
