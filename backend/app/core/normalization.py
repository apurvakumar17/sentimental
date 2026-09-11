import re
import html
import unicodedata

def safe_normalize_text(text: str) -> str:
    """
    Performs safe string normalization without applying NLP preprocessing.
    
    Permitted operations:
    - Unicode NFKC normalization (standardizes smart quotes, non-breaking spaces, compatibility characters)
    - Unescaping HTML entities (&amp; -> &, &quot; -> ", etc.)
    - Stripping residual HTML tags if any (<br>, <p>, </div>)
    - Trimming and collapsing repeated whitespace and newlines into single spaces
    
    STRICTLY FORBIDDEN (Reserved for Module 2):
    - Stopword removal
    - Stemming / lemmatization
    - Lowercasing (preserves casing for Named Entity Recognition / Aspect Extraction)
    - Tokenization
    - Punctuation stripping
    """
    if not text:
        return ""

    # 1. Unicode normalization (NFKC)
    normalized = unicodedata.normalize("NFKC", text)

    # 2. HTML unescape
    normalized = html.unescape(normalized)

    # 3. Strip residual HTML tags safely
    normalized = re.sub(r"<[^>]+>", " ", normalized)

    # 4. Collapse repeated whitespace and carriage returns
    normalized = " ".join(normalized.split())

    return normalized.strip()
