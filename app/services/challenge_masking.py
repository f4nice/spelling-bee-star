import re


ASCII_WORD_PATTERN = re.compile(r"^[A-Za-z]+$")
VOWELS = frozenset("aeiou")


def _ends_with_consonant_vowel_consonant(value: str) -> bool:
    if len(value) < 3:
        return False
    first, middle, last = value[-3:]
    return (
        first not in VOWELS
        and middle in VOWELS
        and last not in VOWELS
        and last not in "wxy"
    )


def _challenge_word_roots(word: str) -> set[str]:
    if len(word) < 3 or not ASCII_WORD_PATTERN.fullmatch(word):
        return {word}

    lower_word = word.lower()
    roots = {word}
    if lower_word.endswith("ies") and len(word) > 4:
        roots.add(f"{word[:-3]}y")
    if lower_word.endswith("es") and len(word) > 4:
        roots.update({word[:-2], word[:-1]})
    elif lower_word.endswith("s") and len(word) > 3 and not lower_word.endswith("ss"):
        roots.add(word[:-1])

    if lower_word.endswith("ied") and len(word) > 4:
        roots.add(f"{word[:-3]}y")
    if lower_word.endswith("ed") and len(word) > 4:
        stem = word[:-2]
        roots.update({stem, word[:-1]})
        if len(stem) > 2 and stem[-1].lower() == stem[-2].lower():
            roots.add(stem[:-1])

    if lower_word.endswith("ing") and len(word) > 5:
        stem = word[:-3]
        roots.update({stem, f"{stem}e"})
        if len(stem) > 2 and stem[-1].lower() == stem[-2].lower():
            roots.add(stem[:-1])

    return {root for root in roots if len(root) >= 3}


def challenge_word_forms(word_value: str | None) -> set[str]:
    word = (word_value or "").strip()
    if not word:
        return set()

    forms = {word, f"{word}'s", f"{word}’s"}
    if len(word) < 3 or not ASCII_WORD_PATTERN.fullmatch(word):
        return forms

    lower_word = word.lower()
    forms.update({f"{word}s", f"{word}es", f"{word}ed", f"{word}ing"})

    if lower_word.endswith("y") and len(word) > 1 and lower_word[-2] not in VOWELS:
        forms.update({f"{word[:-1]}ies", f"{word[:-1]}ied"})

    if lower_word.endswith("e") and lower_word not in {"see", "flee"}:
        forms.add(f"{word}d")
        if not lower_word.endswith(("ee", "oe", "ye")):
            forms.add(f"{word[:-1]}ing")

    if lower_word.endswith("ie"):
        forms.add(f"{word[:-2]}ying")

    if lower_word.endswith("c"):
        forms.update({f"{word}ked", f"{word}king"})

    if _ends_with_consonant_vowel_consonant(lower_word):
        forms.update({f"{word}{word[-1]}ed", f"{word}{word[-1]}ing"})

    return forms


def mask_word_in_text(
    text_value: str | None,
    word_value: str | None,
    alternate_spellings: str | None = None,
) -> str | None:
    text = (text_value or "").strip()
    word = (word_value or "").strip()
    if not text:
        return None
    if not word:
        return text

    spellings = {word}
    if alternate_spellings:
        spellings.update(
            item.strip()
            for item in re.split(r"[,;/；，、\r\n]+", alternate_spellings)
            if item.strip()
        )

    candidates: set[str] = set()
    for spelling in spellings:
        for root in _challenge_word_roots(spelling):
            candidates.update(challenge_word_forms(root))

    masked_text = text
    for candidate in sorted(candidates, key=len, reverse=True):
        pattern = re.compile(
            rf"(?<![A-Za-z]){re.escape(candidate)}(?![A-Za-z])",
            re.IGNORECASE,
        )
        masked_text = pattern.sub("***", masked_text)
    return masked_text
