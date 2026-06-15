from io import BytesIO
import re
from typing import Any

import pandas as pd


WORD_COLUMNS = ("word", "words", "单词", "英文单词", "english", "vocabulary", "vocab", "单字")
ALT_WORD_COLUMNS = ("其他拼法", "其它拼法", "其他写法", "其它写法", "alternate", "alternates", "alternate spelling", "other spellings")
PHONETIC_COLUMNS = ("phonetic", "音标")
PART_OF_SPEECH_COLUMNS = ("part_of_speech", "part of speech", "pos", "词性")
ENGLISH_DEFINITION_COLUMNS = ("english_definition", "english definition", "definition", "definition----asia 亚洲", "英文定义", "英义")
CHINESE_COLUMNS = ("chinese_definition", "中文定义", "中文释义", "释义")
EXAMPLE_COLUMNS = ("english_example", "example", "sentence", "例句", "英文例句")
NOTE_COLUMNS = ("note", "备注")
IGNORED_WORD_COLUMNS = ("序号", "编号", "id", "index", "no", "number")
WORD_PATTERN = re.compile(r"^[a-zA-Z][a-zA-Z' -]*$")


def _find_column(columns: list[str], candidates: tuple[str, ...]) -> str | None:
    normalized = {str(col).strip().lower(): col for col in columns}
    for name in candidates:
        if name.lower() in normalized:
            return normalized[name.lower()]
    candidate_values = tuple(name.lower() for name in candidates)
    for column in columns:
        column_name = str(column).strip().lower()
        if any(candidate in column_name for candidate in candidate_values if len(candidate) >= 3):
            return column
    return None


def parse_words_from_excel(content: bytes) -> list[dict[str, Any]]:
    frame = pd.read_excel(BytesIO(content), engine="openpyxl")
    if frame.empty:
        return []

    return parse_words_from_frame(frame)


def parse_preview_from_excel(content: bytes, sheet_name: str | None = None) -> dict[str, Any]:
    workbook = pd.ExcelFile(BytesIO(content), engine="openpyxl")
    sheet_names = [str(name) for name in workbook.sheet_names]
    active_sheet = sheet_name if sheet_name in sheet_names else (sheet_names[0] if sheet_names else None)
    if active_sheet is None:
        return {
            "columns": [],
            "rows": [],
            "inferred_word_column": None,
            "inferred_word_columns": [],
            "sheet_names": [],
            "sheet_name": None,
        }

    frame = pd.read_excel(workbook, sheet_name=active_sheet)
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
    inferred_word_columns = [str(inferred_word_column).strip()] if inferred_word_column is not None else []
    for column in columns:
        normalized = column.strip().lower()
        if normalized in {item.lower() for item in ALT_WORD_COLUMNS} and column not in inferred_word_columns:
            inferred_word_columns.append(column)
    return {
        "columns": columns,
        "rows": rows,
        "inferred_word_column": str(inferred_word_column).strip() if inferred_word_column is not None else None,
        "inferred_word_columns": inferred_word_columns,
        "sheet_names": sheet_names,
        "sheet_name": active_sheet,
    }


def parse_words_from_preview(
    preview: dict[str, Any],
    selected_row_indexes: set[int],
    selected_columns: set[str],
    word_columns: list[str],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    selected_preview_rows = [
        row for row in preview["rows"] if int(row["index"]) in selected_row_indexes
    ]
    frame = pd.DataFrame([row["values"] for row in selected_preview_rows])
    word_columns = [column for column in word_columns if column in frame.columns]
    if frame.empty or not word_columns:
        return rows

    columns = [column for column in frame.columns if column in selected_columns]
    for word_column in word_columns:
        if word_column not in columns:
            columns.append(word_column)
    frame = frame[columns]
    return parse_words_from_frame(frame, word_columns=word_columns)


def parse_words_from_frame(
    frame: pd.DataFrame,
    word_column: str | None = None,
    word_columns: list[str] | None = None,
) -> list[dict[str, Any]]:
    if frame.empty:
        return []

    columns = list(frame.columns)
    word_cols = word_columns or ([word_column] if word_column else [])
    if not word_cols:
        inferred = _find_column(columns, WORD_COLUMNS) or _infer_word_column(frame)
        word_cols = [inferred] if inferred else []
    word_cols = [column for column in word_cols if column in columns]
    word_col = word_cols[0] if word_cols else None
    phonetic_col = _find_column(columns, PHONETIC_COLUMNS)
    part_of_speech_col = _find_column(columns, PART_OF_SPEECH_COLUMNS)
    english_col = _find_column(columns, ENGLISH_DEFINITION_COLUMNS)
    chinese_col = _find_column(columns, CHINESE_COLUMNS)
    example_col = _find_column(columns, EXAMPLE_COLUMNS)
    note_col = _find_column(columns, NOTE_COLUMNS)

    if word_col is None:
        return []

    rows: list[dict[str, Any]] = []
    for index, row in frame.iterrows():
        spellings = _spellings_from_row(row, word_cols)
        if not spellings:
            continue

        word = spellings[0]
        alternate_spellings = spellings[1:]

        rows.append(
            {
                "word": word.lower(),
                "alternate_spellings": "\n".join(alternate_spellings) if alternate_spellings else None,
                "phonetic": _optional_text(row.get(phonetic_col)) if phonetic_col else None,
                "part_of_speech": _optional_text(row.get(part_of_speech_col)) if part_of_speech_col else None,
                "english_definition": _optional_text(row.get(english_col)) if english_col else None,
                "chinese_definition": _optional_text(row.get(chinese_col)) if chinese_col else None,
                "english_example": _optional_text(row.get(example_col)) if example_col else None,
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


def _split_spellings(value: Any) -> list[str]:
    if value is None or pd.isna(value):
        return []
    text = str(value).strip()
    if not text:
        return []
    parts = re.split(r"[,;/；，、\n\r]+", text)
    return [part.strip().lower() for part in parts if _looks_like_english_word(part.strip())]


def _spellings_from_row(row: Any, word_cols: list[str]) -> list[str]:
    spellings: list[str] = []
    seen: set[str] = set()
    for column in word_cols:
        for spelling in _split_spellings(row.get(column)):
            normalized = spelling.lower()
            if normalized not in seen:
                seen.add(normalized)
                spellings.append(normalized)
    return spellings


def _optional_text(value: Any) -> str | None:
    if value is None or pd.isna(value):
        return None
    text = str(value).strip()
    return text or None
