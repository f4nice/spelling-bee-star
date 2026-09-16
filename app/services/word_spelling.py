import unicodedata


SPELLING_PUNCTUATION = frozenset("'\u2018\u2019\u02bc`.\u00b7-\u2010\u2011\u2013\u2014/&+(),")


def clean_word_spelling(value: str | None) -> str:
    return unicodedata.normalize("NFC", " ".join(str(value or "").split()))


def is_latin_spelling(value: str) -> bool:
    text = clean_word_spelling(value)
    if not text or len(text) > 128:
        return False
    has_letter = False
    can_combine = False
    for char in text:
        category = unicodedata.category(char)
        if category.startswith("L") and "LATIN" in unicodedata.name(char, ""):
            has_letter = True
            can_combine = True
        elif category.startswith("M") and can_combine:
            continue
        elif char in SPELLING_PUNCTUATION or char == " " or char in "0123456789":
            can_combine = False
        else:
            return False
    return has_letter
