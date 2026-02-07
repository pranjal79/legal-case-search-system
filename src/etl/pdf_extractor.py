import os
import json
import re
from datetime import datetime
from pathlib import Path

import PyPDF2
import pdfplumber
import fitz  # PyMuPDF
from tqdm import tqdm


class PDFExtractor:
    """
    Extract text and metadata from legal PDF documents.
    Designed for large-scale datasets (26,000+ PDFs).
    """

    def __init__(self, pdf_folder, output_folder):
        """
        Args:
            pdf_folder (str): Folder containing PDF files
            output_folder (str): Folder to store extracted JSON files
        """
        self.pdf_folder = Path(pdf_folder)
        self.output_folder = Path(output_folder)
        self.output_folder.mkdir(parents=True, exist_ok=True)

        self.stats = {
            "total": 0,
            "successful": 0,
            "failed": 0,
            "errors": []
        }

    def extract_all_pdfs(self, limit=None):
        """
        Extract text from all PDFs in the folder.

        Args:
            limit (int | None): Number of PDFs to process (None = all)
        """
        pdf_files = list(self.pdf_folder.rglob("*.pdf"))

        if limit:
            pdf_files = pdf_files[:limit]

        self.stats["total"] = len(pdf_files)

        print("\n" + "=" * 70)
        print("PDF EXTRACTION PIPELINE")
        print("=" * 70)
        print(f"📂 Source folder : {self.pdf_folder}")
        print(f"💾 Output folder : {self.output_folder}")
        print(f"📊 PDFs to process: {len(pdf_files)}")
        print("=" * 70 + "\n")

        for pdf_file in tqdm(pdf_files, desc="Extracting PDFs", unit="file"):
            try:
                self._extract_single_pdf(pdf_file)
                self.stats["successful"] += 1
            except Exception as e:
                self.stats["failed"] += 1
                self.stats["errors"].append({
                    "file": pdf_file.name,
                    "error": str(e)
                })
                print(f"\n❌ Failed: {pdf_file.name} → {e}")

        self._print_statistics()
        self._save_error_log()

    def _extract_single_pdf(self, pdf_path):
        """
        Extract text from a single PDF using multiple fallback methods.
        """
        case_data = {
            "pdf_filename": pdf_path.name,
            "case_id": pdf_path.stem,
            "extraction_date": datetime.now().isoformat()
        }

        text = None
        method_used = None

        # Method 1: PyMuPDF (fastest)
        try:
            text = self._extract_with_pymupdf(pdf_path)
            method_used = "pymupdf"
        except Exception:
            pass

        # Method 2: pdfplumber
        if not text or len(text.split()) < 200:
            try:
                text = self._extract_with_pdfplumber(pdf_path)
                method_used = "pdfplumber"
            except Exception:
                pass

        # Method 3: PyPDF2
        if not text or len(text.split()) < 200:
            try:
                text = self._extract_with_pypdf2(pdf_path)
                method_used = "pypdf2"
            except Exception:
                pass

        # ✅ Final success condition
        if not text or len(text.split()) < 200:
            raise Exception("Insufficient extracted text")

        case_data["raw_text"] = text
        case_data["cleaned_text"] = self._clean_text(text)
        case_data["extraction_method"] = method_used

        metadata = self._extract_metadata(text)
        case_data.update(metadata)

        case_data["word_count"] = len(case_data["cleaned_text"].split())
        case_data["char_count"] = len(case_data["cleaned_text"])
        case_data["page_count"] = self._get_page_count(pdf_path)

        output_file = self.output_folder / f"{case_data['case_id']}.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(case_data, f, ensure_ascii=False, indent=2)

    def _extract_with_pymupdf(self, pdf_path):
        text = ""
        with fitz.open(pdf_path) as doc:
            for page in doc:
                text += page.get_text()
        return text

    def _extract_with_pdfplumber(self, pdf_path):
        text = ""
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
        return text

    def _extract_with_pypdf2(self, pdf_path):
        text = ""
        with open(pdf_path, "rb") as file:
            reader = PyPDF2.PdfReader(file)
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
        return text

    def _get_page_count(self, pdf_path):
        try:
            with open(pdf_path, "rb") as file:
                reader = PyPDF2.PdfReader(file)
                return len(reader.pages)
        except Exception:
            return 0

    def _clean_text(self, text):
        text = re.sub(r"\s+", " ", text)
        text = re.sub(r"[^\w\s\.,;:\-\(\)\[\]/\'\"]", "", text)
        text = re.sub(r"Page \d+", "", text)
        return text.strip()

    def _extract_metadata(self, text):
        metadata = {
            "title": "Unknown",
            "court": "Supreme Court of India",
            "date": None,
            "bench": None,
            "petitioner": None,
            "respondent": None,
            "case_number": None,
            "citations": []
        }

        title_match = re.search(
            r"([A-Z][A-Za-z\s]+)\s+(?:vs?\.?|versus)\s+([A-Z][A-Za-z\s]+)",
            text[:1000]
        )
        if title_match:
            metadata["title"] = f"{title_match.group(1)} vs {title_match.group(2)}"
            metadata["petitioner"] = title_match.group(1).strip()
            metadata["respondent"] = title_match.group(2).strip()

        date_patterns = [
            r"(?:Decided on|Judgment dated)[\s:]+(\d{1,2}[-/]\d{1,2}[-/]\d{4})",
            r"(\d{1,2}\s+(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4})"
        ]

        for pattern in date_patterns:
            match = re.search(pattern, text[:2000], re.IGNORECASE)
            if match:
                metadata["date"] = match.group(1)
                break

        bench_match = re.search(
            r"(?:BENCH|CORAM)[\s:]+(.+?)(?:\n|JUDGMENT)",
            text[:2000],
            re.IGNORECASE
        )
        if bench_match:
            metadata["bench"] = bench_match.group(1).strip()

        citation_patterns = [
            r"\(\d{4}\)\s+\d+\s+SCC\s+\d+",
            r"AIR\s+\d{4}\s+SC\s+\d+"
        ]

        for pattern in citation_patterns:
            metadata["citations"].extend(re.findall(pattern, text))

        metadata["citations"] = list(set(metadata["citations"]))[:30]
        return metadata

    def _print_statistics(self):
        print("\n" + "=" * 70)
        print("EXTRACTION COMPLETE")
        print("=" * 70)
        print(f"📊 Total PDFs : {self.stats['total']}")
        print(f"✅ Success    : {self.stats['successful']}")
        print(f"❌ Failed     : {self.stats['failed']}")
        print("=" * 70 + "\n")

    def _save_error_log(self):
        if self.stats["errors"]:
            error_log = self.output_folder / "extraction_errors.json"
            with open(error_log, "w", encoding="utf-8") as f:
                json.dump(self.stats["errors"], f, indent=2)
            print(f"⚠️ Error log saved to: {error_log}")


if __name__ == "__main__":
    PDF_FOLDER = "data/raw/supreme_court_pdfs"
    OUTPUT_FOLDER = "data/processed/extracted_json"

    if not os.path.exists(PDF_FOLDER):
        print(f"❌ PDF folder not found: {PDF_FOLDER}")
        exit(1)

    extractor = PDFExtractor(PDF_FOLDER, OUTPUT_FOLDER)

    print("🧪 TEST MODE: Processing first 10 PDFs...\n")
    extractor.extract_all_pdfs(limit=None)

    print("\n✅ Extraction pipeline complete!")
