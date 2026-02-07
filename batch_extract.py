from src.etl.pdf_extractor import PDFExtractor
import time
from datetime import datetime


def main():
    """
    Batch process ALL Supreme Court PDFs (≈26,000 files)

    ⚠️ This script is meant for LONG runs (10–20 hours).
    Run ONLY after testing pdf_extractor.py with 10 PDFs.
    """

    print("""
╔══════════════════════════════════════════════════════════════╗
║     SUPREME COURT PDF EXTRACTION - BATCH PROCESSOR           ║
║                    ~26,000 PDFs                              ║
╚══════════════════════════════════════════════════════════════╝
    """)

    # Paths (relative to project root)
    PDF_FOLDER = "data/raw/supreme_court_pdfs"
    OUTPUT_FOLDER = "data/processed/extracted_json"

    print(f"📂 Source folder : {PDF_FOLDER}")
    print(f"💾 Output folder : {OUTPUT_FOLDER}")
    print(f"⏰ Start time    : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("\n⚠️ This process may take 10–20 HOURS.")
    print("⚠️ Keep your system ON and plugged in.\n")

    # Safety confirmation
    response = input("Are you sure you want to continue? (yes/no): ").strip().lower()
    if response != "yes":
        print("❌ Batch extraction cancelled.")
        return

    # Start timer
    start_time = time.time()

    # Initialize extractor
    extractor = PDFExtractor(PDF_FOLDER, OUTPUT_FOLDER)

    # Run extraction for ALL PDFs
    extractor.extract_all_pdfs(limit=None)

    # End timer
    end_time = time.time()
    duration = end_time - start_time

    hours = int(duration // 3600)
    minutes = int((duration % 3600) // 60)

    print("\n════════════════════════════════════════════════════")
    print("✅ BATCH EXTRACTION COMPLETED")
    print(f"⏱️ Total time   : {hours} hours {minutes} minutes")
    print(f"⏰ End time     : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"📁 Output path  : {OUTPUT_FOLDER}")
    print("════════════════════════════════════════════════════\n")


if __name__ == "__main__":
    main()
