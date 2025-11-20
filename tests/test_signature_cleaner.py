"""Unit tests for signature and footer cleaning"""

import pytest

from src.workflow.utils import clean_signature, strip_html_tags


class TestSignatureCleaner:
    """Test suite for email signature cleaning"""

    @pytest.mark.unit
    def test_clean_signature_basic_text(self):
        """Test cleaning simple text signatures"""
        text = """Hi there,

Can you send me a quote for 100 bolts?

Thanks,
John Doe
Sales Manager
Company Inc.
Phone: 555-1234"""

        cleaned = clean_signature(text)

        # Should remove signature but keep main content
        assert "quote for 100 bolts" in cleaned
        assert cleaned.strip() != ""

    @pytest.mark.unit
    def test_clean_signature_html(self):
        """Test cleaning HTML email bodies"""
        html = """<html><body>
<p>Please provide pricing for Grade 8 fasteners.</p>
<p>Best regards,<br/>
John Smith</p>
</body></html>"""

        cleaned = clean_signature(html)

        # Should contain main content
        assert "pricing" in cleaned or "fasteners" in cleaned

    @pytest.mark.unit
    def test_strip_html_tags(self):
        """Test HTML tag removal"""
        html = "<html><body><p>Hello <b>World</b></p><br/></body></html>"

        text = strip_html_tags(html)

        # Should be plain text
        assert "<" not in text
        assert ">" not in text
        assert "Hello" in text
        assert "World" in text

    @pytest.mark.unit
    def test_clean_signature_empty_body(self):
        """Test handling of empty email body"""
        cleaned = clean_signature("")
        assert cleaned == ""

        cleaned = clean_signature(None)
        assert cleaned == ""

    @pytest.mark.unit
    def test_clean_signature_common_separators(self):
        """Test removal of common signature separators"""
        text = """Please send quote for threaded rod.

--
John Doe
Company Inc."""

        cleaned = clean_signature(text)

        # Should keep main content
        assert "quote" in cleaned
        assert "threaded rod" in cleaned

    @pytest.mark.unit
    def test_clean_signature_email_footer(self):
        """Test removal of common email footers"""
        text = """We need 50 pcs of Grade 5 bolts.

Best regards,
Jane

________________________________
This email and any attachments are confidential."""

        cleaned = clean_signature(text)

        # Should keep main request
        assert "50 pcs" in cleaned or "Grade 5" in cleaned

    @pytest.mark.unit
    def test_clean_signature_forwarded_prefix(self):
        """Test handling of forwarded email prefixes"""
        text = """---------- Forwarded message ---------
From: John <john@example.com>
Date: Mon, Jan 15, 2025
Subject: RFQ

Please quote 100 Grade 8 bolts."""

        cleaned = clean_signature(text)

        # Should keep the actual content
        assert "Grade 8 bolts" in cleaned

    @pytest.mark.unit
    def test_clean_signature_reply_quotes(self):
        """Test removal of reply quotes (> symbols)"""
        text = """We can provide that.

> On Jan 15, 2025, customer wrote:
> Can you quote 50 fasteners?"""

        cleaned = clean_signature(text)

        # Should keep new content
        assert "can provide" in cleaned

    @pytest.mark.unit
    def test_clean_signature_preserves_main_content(self):
        """Test that main email content is preserved"""
        text = """Request for Quote:

Product: Hex Bolts
Grade: 8
Size: 1/2-13 x 2"
Quantity: 500 pcs
Required by: January 30, 2025

Please provide your best pricing.

Thank you,
Procurement Team"""

        cleaned = clean_signature(text)

        # Should preserve all key information
        assert "Hex Bolts" in cleaned
        assert "Grade: 8" in cleaned or "Grade 8" in cleaned
        assert "500" in cleaned
        assert "pricing" in cleaned

    @pytest.mark.unit
    def test_clean_signature_multiple_paragraphs(self):
        """Test handling of multiple paragraph emails"""
        text = """Hello,

We are looking for the following items:

1. Grade 8 bolts - 100 pcs
2. Threaded rod - 50 ft

Please quote by end of week.

Thanks,
John"""

        cleaned = clean_signature(text)

        # Should preserve structured content
        assert "Grade 8 bolts" in cleaned
        assert "Threaded rod" in cleaned
        assert "100" in cleaned


class TestHtmlCleaning:
    """Test suite for HTML cleaning"""

    @pytest.mark.unit
    def test_strip_html_complex(self):
        """Test stripping complex HTML"""
        html = """<html>
<head><style>p { color: blue; }</style></head>
<body>
<div class="content">
<p>Product: <strong>Bolts</strong></p>
<ul>
<li>Grade 8</li>
<li>Quantity: 100</li>
</ul>
</div>
</body>
</html>"""

        text = strip_html_tags(html)

        # Should extract text content
        assert "Product" in text
        assert "Bolts" in text
        assert "Grade 8" in text
        assert "100" in text

        # Should not have HTML tags
        assert "<" not in text

    @pytest.mark.unit
    def test_strip_html_with_entities(self):
        """Test HTML entity handling"""
        html = "<p>Cost: $100 &amp; up</p>"

        text = strip_html_tags(html)

        # Should decode entities
        assert "$100" in text
        # Should handle ampersand
        assert "&" in text or "amp" in text

    @pytest.mark.unit
    def test_strip_html_preserve_line_breaks(self):
        """Test that line breaks are preserved"""
        html = """<p>Line 1</p>
<p>Line 2</p>
<p>Line 3</p>"""

        text = strip_html_tags(html)

        # Should have multiple lines
        assert "Line 1" in text
        assert "Line 2" in text
        assert "Line 3" in text
