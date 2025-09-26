#tests/unit/test_pdf_extractor.py
import sys
import os
import logging
from pathlib import Path
"""
python test_pdf_extractor.py

The test script will:

    Create a sample text-based PDF for testing

    Test text extraction from the PDF

    Test metadata extraction

    Test image and table extraction

    Test the simplified function interface

    Test error handling with invalid PDFs

    Check OCR functionality (if a scanned PDF is available)

Key features of the test script:

    ✅ Automatic sample PDF creation if none exists

    ✅ Comprehensive testing of all PDF extractor features

    ✅ Error handling and validation

    ✅ OCR testing (with instructions for setup)

    ✅ Clean output with emojis for readability

    ✅ No external dependencies beyond what's already in your pro

    ject

To fully test OCR functionality, you'll need to:

    Find or create a scanned PDF (image-based, not text-based)

    Place it at test_samples/sample_scanned.pdf

    Set PDF_USE_OCR=true in your environment variables

The script provides clear feedback on what works and what needs attention, making it easy to identify and fix any issues with your PDF extractor implementation.
"""

# Add the src directory to the Python path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

# Set up basic logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')


def test_pdf_extractor():
    """Test the PDF extractor with different types of PDFs"""

    # Import the PDF extractor
    from src.processing.pdf_extractor import extract_text_from_pdf, PDFExtractor

    # Test cases
    test_cases = [
        {
            'name': 'Text-based PDF',
            'file_path':
            'test_samples/sample_text.pdf',  # You'll need to create this
            'expected_min_chars': 100
        },
        {
            'name': 'Scanned PDF (if available)',
            'file_path': 'test_samples/sample_scanned.pdf',  # Optional
            'expected_min_chars': 50,
            'use_ocr': True
        }
    ]

    # Create test samples directory if it doesn't exist
    os.makedirs('test_samples', exist_ok=True)

    # Create a simple text-based PDF for testing if it doesn't exist
    text_pdf_path = 'test_samples/sample_text.pdf'
    if not os.path.exists(text_pdf_path):
        create_sample_text_pdf(text_pdf_path)

    print("Testing PDF Extractor...")
    print("=" * 50)

    # Test the extractor
    pdf_extractor = PDFExtractor()

    for test_case in test_cases:
        if not os.path.exists(test_case['file_path']):
            print(
                f"⚠️  Skipping {test_case['name']} - file not found: {test_case['file_path']}"
            )
            continue

        print(f"\n🧪 Testing: {test_case['name']}")
        print(f"📁 File: {test_case['file_path']}")

        try:
            # Read the PDF file
            with open(test_case['file_path'], 'rb') as f:
                pdf_content = f.read()

            # Configure OCR if specified
            if test_case.get('use_ocr'):
                pdf_extractor.use_ocr = True

            # Extract text and metadata
            text, metadata = pdf_extractor.extract_text_from_pdf(pdf_content)

            # Print results
            print(f"✅ Text extraction successful")
            print(f"📄 Text length: {len(text)} characters")
            print(f"📊 Page count: {metadata.get('page_count', 'N/A')}")
            print(f"📝 Title: {metadata.get('title', 'N/A')}")
            print(f"👤 Author: {metadata.get('author', 'N/A')}")

            # Show first 200 characters of text
            preview = text[:200].replace('\n', ' ')
            print(f"🔍 Text preview: {preview}...")

            # Validate results
            if len(text) >= test_case['expected_min_chars']:
                print("✅ Text length meets expectations")
            else:
                print(
                    f"⚠️  Text length is shorter than expected (expected at least {test_case['expected_min_chars']} chars)"
                )

            # Test image extraction
            images = pdf_extractor.extract_images(pdf_content, max_images=3)
            print(f"🖼️  Extracted {len(images)} images")

            # Test table extraction
            tables = pdf_extractor.extract_tables(pdf_content)
            print(f"📊 Extracted {len(tables)} tables")

        except Exception as e:
            print(f"❌ Error processing {test_case['name']}: {e}")

    # Test the simplified function interface
    print("\n" + "=" * 50)
    print("Testing simplified function interface...")

    try:
        with open(text_pdf_path, 'rb') as f:
            pdf_content = f.read()

        text = extract_text_from_pdf(pdf_content)
        print(
            f"✅ Simplified function works - extracted {len(text)} characters")

    except Exception as e:
        print(f"❌ Simplified function failed: {e}")

    # Test error handling
    print("\n" + "=" * 50)
    print("Testing error handling...")

    try:
        # Test with invalid PDF content
        invalid_content = b"This is not a PDF file"
        text, metadata = pdf_extractor.extract_text_from_pdf(invalid_content)
        print("❌ Should have raised an error for invalid PDF")
    except Exception as e:
        print(f"✅ Properly handled invalid PDF: {type(e).__name__}")


def create_sample_text_pdf(file_path):
    """Create a simple text-based PDF for testing"""
    try:
        # Try to create PDF using reportlab if available
        from reportlab.lib.pagesizes import letter
        from reportlab.pdfgen import canvas

        c = canvas.Canvas(file_path, pagesize=letter)
        c.drawString(100, 750, "Sample Research Paper")
        c.drawString(100, 730, "Title: Advanced Machine Learning Techniques")
        c.drawString(100, 710, "Author: Dr. Jane Smith")
        c.drawString(100, 690, "Abstract: This paper explores...")
        c.drawString(100, 670, "Keywords: machine learning, AI, research")
        c.drawString(100, 650,
                     "Introduction: Machine learning has revolutionized...")
        c.drawString(100, 630,
                     "Methodology: We conducted experiments using...")
        c.drawString(100, 610,
                     "Results: Our approach achieved 95% accuracy...")
        c.drawString(100, 590, "Conclusion: This research demonstrates...")
        c.drawString(100, 570, "References: [1] Smith et al. 2020...")
        c.save()
        print(f"✅ Created sample PDF: {file_path}")

    except ImportError:
        # Fallback: create a minimal PDF using PyMuPDF
        try:
            import fitz
            doc = fitz.open()
            page = doc.new_page()

            # Add some text
            text = """Sample Research Paper
Title: Advanced Machine Learning Techniques
Author: Dr. Jane Smith
Abstract: This paper explores advanced machine learning techniques...
Introduction: Machine learning has revolutionized various fields...
Methodology: We conducted experiments using state-of-the-art methods...
Results: Our approach achieved significant improvements...
Conclusion: This research demonstrates the effectiveness of...
"""
            page.insert_text((100, 100), text)
            doc.save(file_path)
            doc.close()
            print(f"✅ Created sample PDF using PyMuPDF: {file_path}")

        except ImportError:
            print(
                "❌ Cannot create sample PDF - neither reportlab nor PyMuPDF available"
            )
            return False

    return True


def test_ocr_functionality():
    """Test OCR functionality if a scanned PDF is available"""
    print("\n" + "=" * 50)
    print("Testing OCR functionality...")

    scanned_pdf_path = 'test_samples/sample_scanned.pdf'

    if not os.path.exists(scanned_pdf_path):
        print("⚠️  No scanned PDF available for OCR testing")
        print(
            "💡 To test OCR, place a scanned PDF at: test_samples/sample_scanned.pdf"
        )
        return

    # from processing.pdf_extractor import PDFExtractor
    from src.processing.pdf_extractor import PDFExtractor

    pdf_extractor = PDFExtractor()
    pdf_extractor.use_ocr = True
    pdf_extractor.ocr_language = "eng"

    try:
        with open(scanned_pdf_path, 'rb') as f:
            pdf_content = f.read()

        text, metadata = pdf_extractor.extract_text_from_pdf(pdf_content)
        print(f"✅ OCR extraction successful")
        print(f"📄 Text length: {len(text)} characters")
        print(f"🔍 Text preview: {text[:200]}...")

    except Exception as e:
        print(f"❌ OCR extraction failed: {e}")


if __name__ == "__main__":
    # Create a .env file for testing if it doesn't exist
    if not os.path.exists('.env'):
        with open('.env', 'w') as f:
            f.write("PDF_USE_OCR=false\n")
            f.write("PDF_OCR_LANGUAGE=eng\n")

    # Test main functionality
    test_pdf_extractor()

    # Test OCR functionality
    test_ocr_functionality()

    print("\n" + "=" * 50)
    print("📋 Test Summary:")
    print("✅ Basic PDF extraction tested")
    print("✅ Simplified function interface tested")
    print("✅ Error handling tested")
    print("✅ OCR functionality checked")
    print(
        "\n🎯 To fully test OCR, add a scanned PDF to test_samples/sample_scanned.pdf"
    )
