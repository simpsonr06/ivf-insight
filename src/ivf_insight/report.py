"""IVF Insight Research Monograph Compilation Module

Generates the comprehensive 21-section research report in Markdown, HTML, and PDF.
"""

from pathlib import Path
import subprocess
import shutil
import markdown

ACADEMIC_CSS = """
@page {
    size: A4;
    margin: 20mm 15mm 20mm 15mm;
    @top-center {
        content: "IVF Insight: Clinical Data Analysis & Prospective Chronological Validation";
        font-family: "Georgia", serif;
        font-size: 8pt;
        color: #7f8c8d;
        border-bottom: 0.5pt solid #bdc3c7;
        padding-bottom: 4px;
        margin-bottom: 10px;
    }
    @bottom-center {
        content: "Page " counter(page) " of " counter(pages);
        font-family: "Georgia", serif;
        font-size: 8pt;
        color: #7f8c8d;
    }
}

body {
    font-family: "Georgia", "Times New Roman", serif;
    font-size: 10pt;
    line-height: 1.55;
    color: #2c3e50;
    margin: 0 auto;
    padding: 0;
}

h1 {
    font-family: "Arial", "Helvetica", sans-serif;
    font-size: 18pt;
    font-weight: bold;
    color: #1a365d;
    line-height: 1.25;
    margin-top: 0;
    margin-bottom: 12pt;
    text-align: center;
}

h2 {
    font-family: "Arial", "Helvetica", sans-serif;
    font-size: 13pt;
    font-weight: bold;
    color: #2b6cb0;
    border-bottom: 1.5pt solid #cbd5e0;
    padding-bottom: 3pt;
    margin-top: 18pt;
    margin-bottom: 8pt;
    page-break-after: avoid;
}

h3 {
    font-family: "Arial", "Helvetica", sans-serif;
    font-size: 11pt;
    font-weight: bold;
    color: #2d3748;
    margin-top: 14pt;
    margin-bottom: 6pt;
    page-break-after: avoid;
}

h4 {
    font-family: "Arial", "Helvetica", sans-serif;
    font-size: 10pt;
    font-weight: bold;
    color: #4a5568;
    margin-top: 10pt;
    margin-bottom: 4pt;
}

p {
    margin-top: 0;
    margin-bottom: 8pt;
    text-align: justify;
    text-justify: inter-word;
}

ul, ol {
    margin-top: 0;
    margin-bottom: 8pt;
    padding-left: 20pt;
}

li {
    margin-bottom: 4pt;
}

blockquote {
    border-left: 3pt solid #3182ce;
    padding-left: 10pt;
    margin-left: 0;
    margin-right: 0;
    color: #4a5568;
    font-style: italic;
    background: #ebf8ff;
    padding-top: 6pt;
    padding-bottom: 6pt;
}

code {
    font-family: "Courier New", Courier, monospace;
    font-size: 9pt;
    background-color: #edf2f7;
    padding: 1pt 3pt;
    border-radius: 2pt;
    color: #c53030;
}

pre {
    background-color: #f7fafc;
    border: 1pt solid #e2e8f0;
    border-radius: 4pt;
    padding: 8pt;
    overflow-x: auto;
    font-family: "Courier New", Courier, monospace;
    font-size: 8pt;
    line-height: 1.35;
    margin-bottom: 10pt;
}

table {
    width: 100%;
    border-collapse: collapse;
    margin-top: 8pt;
    margin-bottom: 12pt;
    font-size: 8.5pt;
    page-break-inside: avoid;
}

th, td {
    border: 0.75pt solid #cbd5e0;
    padding: 4pt 6pt;
    text-align: left;
}

th {
    background-color: #edf2f7;
    font-weight: bold;
    color: #2d3748;
}

tr:nth-child(even) {
    background-color: #f7fafc;
}

.title-page {
    page-break-after: always;
    text-align: center;
    padding-top: 40pt;
}

.author-block {
    margin-top: 20pt;
    margin-bottom: 30pt;
    font-size: 11pt;
    line-height: 1.5;
}

.metadata-box {
    border: 1pt solid #cbd5e0;
    background: #f8fafc;
    padding: 12pt;
    text-align: left;
    font-size: 9pt;
    margin-top: 30pt;
    border-radius: 4pt;
}

hr {
    border: 0;
    border-bottom: 1pt solid #e2e8f0;
    margin: 16pt 0;
}

.alert-warning {
    border-left: 3pt solid #dd6b20;
    background: #fffaf0;
    padding: 8pt 10pt;
    margin-bottom: 10pt;
    font-size: 9pt;
}

.alert-info {
    border-left: 3pt solid #3182ce;
    background: #ebf8ff;
    padding: 8pt 10pt;
    margin-bottom: 10pt;
    font-size: 9pt;
}

.figure-caption {
    font-size: 8.5pt;
    color: #718096;
    font-style: italic;
    text-align: center;
    margin-top: 4pt;
    margin-bottom: 12pt;
}
"""


def compile_research_report(output_dir: str = "reports") -> dict:
    """Compiles markdown, HTML, and PDF research report deliverables."""
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    md_path = out_dir / "IVF_Insight_Research_Report.md"
    html_path = out_dir / "IVF_Insight_Research_Report.html"
    pdf_path = out_dir / "IVF_Insight_Research_Report.pdf"

    if not md_path.exists():
        raise FileNotFoundError(f"Markdown report template not found at {md_path}")

    content = md_path.read_text(encoding="utf-8")
    html_body = markdown.markdown(content, extensions=["tables", "fenced_code", "toc"])

    html_full = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>IVF Insight: Exploratory Clinical Data Analysis, Predictive Modelling and Temporal Validation of IVF Treatment-Cycle Outcomes</title>
<style>
{ACADEMIC_CSS}
</style>
</head>
<body>
{html_body}
</body>
</html>
"""
    html_path.write_text(html_full, encoding="utf-8")

    # Locate Chrome or Edge for headless PDF compilation
    browsers = [
        Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"),
        Path(r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"),
        Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
        Path(r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"),
    ]
    browser_exe = None
    for b in browsers:
        if b.exists():
            browser_exe = b
            break
    if browser_exe is None:
        browser_exe = shutil.which("msedge") or shutil.which("chrome") or shutil.which("google-chrome")

    pdf_generated = False
    if browser_exe:
        html_uri = html_path.resolve().as_uri()
        cmd = [
            str(browser_exe),
            "--headless",
            "--disable-gpu",
            "--run-all-compositor-stages-before-draw",
            f"--print-to-pdf={pdf_path.resolve()}",
            html_uri,
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        pdf_generated = pdf_path.exists() and pdf_path.stat().st_size > 0

    return {
        "markdown_report": str(md_path),
        "html_report": str(html_path),
        "pdf_report": str(pdf_path) if pdf_generated else None,
        "pdf_size_bytes": pdf_path.stat().st_size if pdf_generated else 0,
        "browser_used": str(browser_exe) if browser_exe else None,
    }
