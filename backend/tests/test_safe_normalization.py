from backend.app.core.normalization import safe_normalize_text

def test_unicode_nfkc_normalization():
    # Smart quotes and typographic marks normalized to standard equivalents
    raw = "The phone’s camera has “stellar” performance and 5G connectivity."
    normalized = safe_normalize_text(raw)
    assert "stellar" in normalized
    # Non-breaking space \xa0 converted to standard space
    assert "\xa0" not in normalized

def test_html_entity_and_tag_stripping():
    raw = "Crisp OLED display &amp; loud speakers!<br><p>Charges in 30 mins.</p>"
    normalized = safe_normalize_text(raw)
    assert "&amp;" not in normalized
    assert "&" in normalized
    assert "<br>" not in normalized
    assert "<p>" not in normalized
    assert "</p>" not in normalized
    assert normalized == "Crisp OLED display & loud speakers! Charges in 30 mins."

def test_whitespace_and_newline_collapsing():
    raw = "   Excellent    battery \n\n   life \t and \r\n fast charging.   "
    normalized = safe_normalize_text(raw)
    assert normalized == "Excellent battery life and fast charging."

def test_strictly_preserves_case_and_nlp_tokens():
    # Must NOT remove stopwords, must NOT lowercase, must NOT stem
    raw = "I am very happy with the Snapdragon 8 Gen 3 processor."
    normalized = safe_normalize_text(raw)
    # Casing preserved
    assert "Snapdragon 8 Gen 3" in normalized
    # Stopwords preserved
    assert "I am very happy with the" in normalized
    # Punctuation preserved
    assert normalized.endswith(".")
