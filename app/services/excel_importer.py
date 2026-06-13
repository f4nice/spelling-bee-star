from io import BytesIO
import re
from typing import Any

import pandas as pd


WORD_COLUMNS = ("word", "words", "单词", "英文单词", "english", "vocabulary", "vocab", "单字")
PHONETIC_COLUMNS = ("phonetic", "音标")
CHINESE_COLUMNS = ("chinese_definition", "中文定义", "中文释义", "释义")
NOTE_COLUMNS = ("note", "备注")
IGNORED_WORD_COLUMNS = ("序号", "编号", "id", "index", "no", "number")
WORD_PATTERN = re.compile(r"^[a-zA-Z][a-zA-Z' -]*$")


def _find_column(columns: list[str], candidates: tuple[str, ...]) -> str | None:
    normalized = {str(col).strip().lower(): col for col in columns}
    for name in candidates:
        if name.lower() in normalized:
            return normalized[name.lower()]
    return None


def parse_words_from_excel(content: bytes) -> list[dict[str, Any]]:
    frame = pd.read_excel(BytesIO(content), engine="openpyxl")
    if frame.empty:
        return []

    return parse_words_from_frame(frame)


def parse_preview_from_excel(content: bytes) -> dict[str, Any]:
    frame = pd.read_excel(BytesIO(content), engine="openpyxl")
    frame = frame.fillna("")
    columns = [str(column).strip() for column in frame.columns]
    records = frame.astype(str).to_dict(orient="records")
    rows = [
        {
            "index": index,
            "excel_row": index + 2,
            "values": {str(key).strip(): value for key, value in record.items()},
        }
        for index, record in enumerate(records)
    ]
    inferred_word_column = _find_column(columns, WORD_COLUMNS) or _infer_word_column(frame)
    return {
        "columns": columns,
        "rows": rows,
        "inferred_word_column": str(inferred_word_column).strip() if inferred_word_column is not None else None,
    }


def parse_words_from_preview(
    preview: dict[str, Any],
    selected_row_indexes: set[int],
    selected_columns: set[str],
    word_column: str,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    selected_preview_rows = [
        row for row in preview["rows"] if int(row["index"]) in selected_row_indexes
    ]
    frame = pd.DataFrame([row["values"] for row in selected_preview_rows])
    if frame.empty or word_column not in frame.columns:
        return rows

    columns = [column for column in frame.columns if column in selected_columns]
    if word_column not in columns:
        columns.append(word_column)
    frame = frame[columns]
    return parse_words_from_frame(frame, word_column=word_column)


def parse_words_from_frame(frame: pd.DataFrame, word_column: str | None = None) -> list[dict[str, Any]]:
    if frame.empty:
        return []

    columns = list(frame.columns)
    word_col = word_column or _find_column(columns, WORD_COLUMNS) or _infer_word_column(frame)
    phonetic_col = _find_column(columns, PHONETIC_COLUMNS)
    chinese_col = _find_column(columns, CHINESE_COLUMNS)
    note_col = _find_column(columns, NOTE_COLUMNS)

    if word_col is None:
        return []

    rows: list[dict[str, Any]] = []
    for index, row in frame.iterrows():
        raw_word = row.get(word_col)
        if pd.isna(raw_word):
            continue

        word = str(raw_word).strip()
        if not _looks_like_english_word(word):
            continue

        rows.append(
            {
                "word": word.lower(),
                "phonetic": _optional_text(row.get(phonetic_col)) if phonetic_col else None,
                "chinese_definition": _optional_text(row.get(chinese_col)) if chinese_col else None,
                "note": _optional_text(row.get(note_col)) if note_col else None,
                "row_number": int(index) + 2,
            }
        )
    return rows


def _infer_word_column(frame: pd.DataFrame) -> str | None:
    best_column: str | None = None
    best_score = 0

    for column in frame.columns:
        column_name = str(column).strip().lower()
        if column_name in IGNORED_WORD_COLUMNS:
            continue

        values = frame[column].dropna().head(50)
        score = sum(1 for value in values if _looks_like_english_word(str(value).strip()))
        if score > best_score:
            best_column = column
            best_score = score

    return best_column if best_score > 0 else None


def _looks_like_english_word(value: str) -> bool:
    value = value.strip()
    if not value or value.isdigit():
        return False
    return bool(WORD_PATTERN.fullmatch(value))


def _optional_text(value: Any) -> str | None:
    if value is None or pd.isna(value):
        return None
    text = str(value).strip()
    return text or None
