import pytest
from pathlib import Path
from document import document_processor


def test_document_processor_initialization():
    """
    Tests that document processor initializes correctly.
    Validates Docling converter is ready.
    """
    assert document_processor.converter is not None


@pytest.mark.skipif(
    not Path("tests/sample_rfp.pdf").exists(),
    reason="Sample RFP file not found"
)
def test_pdf_extraction():
    """
    Tests PDF document extraction functionality.
    Validates text, tables, and metadata extraction.
    """
    result = document_processor.extract("tests/sample_rfp.pdf")
    
    assert 'text' in result
    assert 'tables' in result
    assert 'metadata' in result
    assert len(result['text']) > 0


def test_text_only_extraction():
    """
    Tests quick text extraction without full structure.
    Validates simplified extraction method.
    """
    if Path("tests/sample_rfp.pdf").exists():
        text = document_processor.extract_text_only("tests/sample_rfp.pdf")
        assert isinstance(text, str)
        assert len(text) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

