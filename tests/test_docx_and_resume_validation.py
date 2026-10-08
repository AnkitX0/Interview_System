import io
import zipfile
import pytest
from fastapi.testclient import TestClient
import docx

from backend.services.resume_service import (
    validate_resume_file_bytes,
    extract_text_from_docx_bytes,
    normalize_extracted_text,
    validate_resume_document,
)


def create_sample_docx_bytes(include_table: bool = True, include_links: bool = True) -> bytes:
    """Creates a real in-memory Microsoft Word DOCX resume."""
    doc = docx.Document()
    doc.add_heading("Sarah Connor", level=1)
    doc.add_paragraph("Email: sarah.connor@example.com | Phone: +1-555-0199 | Location: Los Angeles, CA")
    
    doc.add_heading("Professional Summary", level=2)
    doc.add_paragraph(
        "Senior Distributed Systems Engineer with 6+ years of experience architecting resilient backend services, "
        "low-latency streaming pipelines, and cloud-native microservices."
    )

    doc.add_heading("Technical Skills", level=2)
    if include_table:
        table = doc.add_table(rows=3, cols=2)
        table.cell(0, 0).text = "Languages"
        table.cell(0, 1).text = "Python, Go, C++, SQL, Bash"
        table.cell(1, 0).text = "Frameworks & Tools"
        table.cell(1, 1).text = "FastAPI, Docker, Kubernetes, Kafka, Redis"
        table.cell(2, 0).text = "Cloud Platforms"
        table.cell(2, 1).text = "AWS, PostgreSQL, Prometheus, Grafana"
    else:
        doc.add_paragraph("Languages: Python, Go, C++, SQL, Bash")
        doc.add_paragraph("Frameworks & Tools: FastAPI, Docker, Kubernetes, Kafka, Redis")

    doc.add_heading("Professional Experience", level=2)
    p_exp1 = doc.add_paragraph()
    p_exp1.add_run("Staff Backend Engineer - Cyberdyne Systems (2022 - Present)\n").bold = True
    p_exp1.add_run("- Architected high-throughput telemetry ingestion service processing 50,000 events/sec with 99.99% uptime.\n")
    p_exp1.add_run("- Optimized PostgreSQL database connection pooling and indexing, cutting p99 query latency by 45%.\n")
    p_exp1.add_run("- Implemented Redis distributed locking for consensus across 12 worker nodes.\n")

    p_exp2 = doc.add_paragraph()
    p_exp2.add_run("Software Engineer - Tech Core (2019 - 2022)\n").bold = True
    p_exp2.add_run("- Developed microservices in Python and FastAPI deployed to AWS EKS clusters.\n")
    p_exp2.add_run("- Engineered automated CI/CD deployment pipelines using GitHub Actions.\n")

    doc.add_heading("Key Projects", level=2)
    p_proj = doc.add_paragraph()
    p_proj.add_run("Real-Time Anomaly Detector: ").bold = True
    p_proj.add_run("Built stream processing pipeline in Go and Kafka handling 20,000 messages/sec with sub-50ms latency. ")
    if include_links:
        p_proj.add_run("Source code on GitHub (https://github.com/sarahconnor/stream-detector).")

    doc.add_heading("Education", level=2)
    doc.add_paragraph("B.S. in Computer Science - University of California, Berkeley (2015 - 2019)")

    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


def test_valid_docx_extraction_and_table_content():
    """Verifies that a real DOCX file extracts paragraphs, tables, and sections without XML metadata."""
    docx_bytes = create_sample_docx_bytes(include_table=True, include_links=True)
    text = extract_text_from_docx_bytes(docx_bytes)

    # 1. Ensure human-readable content is present
    assert "Sarah Connor" in text
    assert "sarah.connor@example.com" in text
    assert "Languages: Python, Go, C++, SQL, Bash" in text
    assert "Cyberdyne Systems" in text
    assert "50,000 events/sec" in text

    # 2. Critical Safety: NO XML/ZIP artifact leakage
    assert "word/document.xml" not in text
    assert "[Content_Types].xml" not in text
    assert "PK\x03\x04" not in text
    assert "xmlns:" not in text
    assert "<w:" not in text


def test_validate_resume_file_bytes_matrix():
    """Tests file signature and extension validation matrix."""
    valid_docx = create_sample_docx_bytes()
    valid_pdf = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF"

    # 1. Valid files
    is_valid, msg, ftype = validate_resume_file_bytes(valid_docx, "resume.docx")
    assert is_valid is True and ftype == "docx"

    is_valid, msg, ftype = validate_resume_file_bytes(valid_pdf, "resume.pdf")
    assert is_valid is True and ftype == "pdf"

    # 2. Legacy .doc rejection
    ole2_bytes = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1" + b"\x00" * 50
    is_valid, msg, ftype = validate_resume_file_bytes(ole2_bytes, "resume.doc")
    assert is_valid is False
    assert "Microsoft Word .doc files are not supported. Please upload a .docx file." in msg

    # Disguised .doc renamed to .docx
    is_valid, msg, ftype = validate_resume_file_bytes(ole2_bytes, "disguised.docx")
    assert is_valid is False
    assert "Microsoft Word .doc files are not supported. Please upload a .docx file." in msg

    # 3. Renamed text file -> .docx
    plain_text_bytes = b"Jane Doe\nSkills: Python, Go\nExperience: Software Engineer"
    is_valid, msg, ftype = validate_resume_file_bytes(plain_text_bytes, "plain.docx")
    assert is_valid is False
    assert "We couldn't read this document. Please upload a valid PDF or DOCX file." in msg

    # 4. Renamed zip without word/document.xml -> .docx
    zip_buf = io.BytesIO()
    with zipfile.ZipFile(zip_buf, "w") as zf:
        zf.writestr("test.txt", "not a docx")
    bogus_zip_bytes = zip_buf.getvalue()
    is_valid, msg, ftype = validate_resume_file_bytes(bogus_zip_bytes, "bogus.docx")
    assert is_valid is False
    assert "We couldn't read this document. Please upload a valid PDF or DOCX file." in msg

    # 5. Renamed zip -> .pdf
    is_valid, msg, ftype = validate_resume_file_bytes(bogus_zip_bytes, "bogus.pdf")
    assert is_valid is False
    assert "We couldn't read this document. Please upload a valid PDF or DOCX file." in msg

    # 6. Unsupported extensions
    for ext in [".txt", ".rtf", ".odt", ".pages", ".jpg", ".png", ".zip", ".csv", ".xlsx", ".exe", ".json"]:
        is_valid, msg, ftype = validate_resume_file_bytes(b"content", f"file{ext}")
        assert is_valid is False
        assert "Unsupported file type. Please upload a PDF or DOCX resume." in msg

    # 7. Empty files
    is_valid, msg, ftype = validate_resume_file_bytes(b"", "empty.docx")
    assert is_valid is False
    assert "We couldn't extract enough text to analyze this resume." in msg


def test_resume_upload_endpoint_valid_docx(client: TestClient):
    """End-to-end test: uploading a real DOCX resume extracts candidate info and generates structured score."""
    docx_bytes = create_sample_docx_bytes()

    res = client.post(
        "/resume/upload",
        files={"file": ("sarah_connor_resume.docx", docx_bytes, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")}
    )
    assert res.status_code == 200
    data = res.json()

    assert data["candidate_name"] == "Sarah Connor"
    assert "python" in [s.lower() for s in data["skills"]]
    assert "go" in [s.lower() for s in data["skills"]]
    assert data["resume_score"] > 50
    assert len(data["claims"]) > 0
    # No XML artifacts in persisted raw text or summary
    assert "word/document.xml" not in data["raw_text"]
    assert "[Content_Types].xml" not in data["raw_text"]
    assert "PK\x03\x04" not in data["raw_text"]


def test_resume_upload_endpoint_rejects_legacy_doc(client: TestClient):
    """End-to-end test: uploading .doc file is rejected with clear message."""
    ole2_bytes = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1" + b"\x00" * 100
    res = client.post(
        "/resume/upload",
        files={"file": ("resume.doc", ole2_bytes, "application/msword")}
    )
    assert res.status_code == 400
    assert "Microsoft Word .doc files are not supported. Please upload a .docx file." in res.json()["error"]["message"]


def test_resume_upload_endpoint_rejects_unsupported_formats(client: TestClient):
    """End-to-end test: uploading .txt, .rtf, or .zip is rejected with unsupported error."""
    res = client.post(
        "/resume/upload",
        files={"file": ("resume.txt", b"Jane Doe Python Developer", "text/plain")}
    )
    assert res.status_code == 400
    assert "Unsupported file type. Please upload a PDF or DOCX resume." in res.json()["error"]["message"]


def test_resume_upload_endpoint_rejects_corrupted_docx(client: TestClient):
    """End-to-end test: uploading invalid/renamed docx returns corrupted document message."""
    fake_docx = b"PK\x03\x04corrupted zip stream content without openxml"
    res = client.post(
        "/resume/upload",
        files={"file": ("corrupted.docx", fake_docx, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")}
    )
    assert res.status_code == 400
    assert "We couldn't read this document. Please upload a valid PDF or DOCX file." in res.json()["error"]["message"]


def test_resume_critical_safety_xml_garbage_rejection():
    """Critical safety check: text containing word/document.xml or PK headers is immediately aborted with no score."""
    corrupted_extracted_text = (
        "word/document.xml PK\x03\x04 [Content_Types].xml\n"
        "<w:document xmlns:w='http://schemas.openxmlformats.org/wordprocessingml/2006/main'>\n"
        "<w:p><w:r><w:t>John Doe Python AWS</w:t></w:r></w:p>\n"
        "Experience: Software Engineer at TechCorp\n"
        "Skills: Python, AWS, Docker\n"
    )
    is_valid, msg, details = validate_resume_document(corrupted_extracted_text)
    assert is_valid is False
    assert "Unable to read this document correctly. Please upload a valid PDF or DOCX resume." in msg
    assert details["reason"] == "xml_zip_garbage_detected"
