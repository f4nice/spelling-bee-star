from __future__ import annotations

import importlib
import json
import random
from datetime import date, datetime
from typing import Any

from booklearner.config import MySQLConfig, get_mysql_config


def get_storage_status() -> dict[str, Any]:
    config = get_mysql_config()
    if not config.enabled:
        return {
            "enabled": False,
            "connected": False,
            "message": "MySQL is disabled; analysis results are shown only on this page.",
        }

    connector = _mysql_connector()
    if connector is None:
        return {
            "enabled": True,
            "connected": False,
            "message": "mysql-connector-python is missing. Install requirements.txt first.",
        }

    connection = None
    try:
        connection = _connect(config)
    except Exception as exc:
        return {
            "enabled": True,
            "connected": False,
            "message": f"MySQL connection failed: {exc}",
        }
    finally:
        if connection is not None:
            connection.close()

    return {"enabled": True, "connected": True, "message": "MySQL is connected. Results will be saved."}


def save_analysis(query: str, result: dict[str, Any]) -> dict[str, Any]:
    config = get_mysql_config()
    if not config.enabled:
        return {"saved": False, "reason": "mysql_disabled", "message": "MySQL is disabled."}

    if _mysql_connector() is None:
        return {
            "saved": False,
            "reason": "mysql_connector_missing",
            "message": "mysql-connector-python is missing; result was not saved.",
        }

    connection = None
    cursor = None
    try:
        connection = _connect(config)
        cursor = connection.cursor()
        book = result.get("book") or {}
        stats = result.get("stats") or {}
        cursor.execute(
            """
            INSERT INTO analyses
              (query_text, status, title, authors_text, source_name, source_url, notice, stats_json, result_json)
            VALUES
              (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                query,
                result.get("status", ""),
                book.get("title"),
                _authors_text(book.get("authors")),
                book.get("sourceName"),
                book.get("sourceUrl"),
                result.get("notice"),
                json.dumps(stats, ensure_ascii=False),
                json.dumps(result, ensure_ascii=False),
            ),
        )
        analysis_id = int(cursor.lastrowid)
        _insert_quotes(cursor, analysis_id, result.get("quotes") or [])
        _insert_vocabulary(cursor, analysis_id, result.get("vocabulary") or [])
        connection.commit()
    except Exception as exc:
        if connection is not None:
            connection.rollback()
        return {"saved": False, "reason": "mysql_error", "message": f"MySQL save failed: {exc}"}
    finally:
        _close_cursor_connection(cursor, connection)

    return {"saved": True, "analysisId": analysis_id, "message": "Saved to MySQL."}


def list_recent_analyses(limit: int = 20) -> list[dict[str, Any]]:
    config = get_mysql_config()
    if not config.enabled or _mysql_connector() is None:
        return []

    connection = None
    cursor = None
    try:
        connection = _connect(config)
        cursor = connection.cursor(dictionary=True)
        cursor.execute(
            """
            SELECT id, query_text, status, title, authors_text, source_name, created_at
            FROM analyses
            ORDER BY created_at DESC
            LIMIT %s
            """,
            (max(1, min(limit, 100)),),
        )
        return [_serialize_row(row) for row in cursor.fetchall()]
    except Exception:
        return []
    finally:
        _close_cursor_connection(cursor, connection)


def get_analysis(analysis_id: int) -> dict[str, Any] | None:
    config = get_mysql_config()
    if not config.enabled or _mysql_connector() is None:
        return None

    connection = None
    cursor = None
    try:
        connection = _connect(config)
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT result_json FROM analyses WHERE id = %s", (analysis_id,))
        row = cursor.fetchone()
    except Exception:
        return None
    finally:
        _close_cursor_connection(cursor, connection)

    if not row:
        return None
    value = row["result_json"]
    if isinstance(value, (dict, list)):
        return value
    return json.loads(value)


def list_featured_quotes(limit: int = 12, analysis_id: int | None = None) -> list[dict[str, Any]]:
    config = get_mysql_config()
    if not config.enabled or _mysql_connector() is None:
        return []

    connection = None
    cursor = None
    safe_limit = max(1, min(limit, 80))
    try:
        connection = _connect(config)
        cursor = connection.cursor(dictionary=True)
        if analysis_id:
            cursor.execute(
                """
                SELECT
                  a.id,
                  a.title,
                  a.authors_text,
                  a.stats_json,
                  a.result_json,
                  a.created_at,
                  q.quote_text,
                  q.note,
                  q.position
                FROM analyses a
                JOIN analysis_quotes q ON q.analysis_id = a.id
                WHERE a.id = %s
                ORDER BY q.position ASC, q.id ASC
                LIMIT %s
                """,
                (analysis_id, safe_limit),
            )
            return [_featured_quote_from_joined_row(row) for row in cursor.fetchall() if row.get("quote_text")]

        cursor.execute(
            """
            SELECT
              a.id,
              a.title,
              a.authors_text,
              a.stats_json,
              a.result_json,
              a.created_at,
              q.quote_text,
              q.note,
              q.position
            FROM analyses a
            JOIN analysis_quotes q ON q.analysis_id = a.id
            WHERE q.quote_text IS NOT NULL AND q.quote_text <> ''
            ORDER BY RAND()
            LIMIT %s
            """,
            (safe_limit,),
        )
        rows = cursor.fetchall()
    except Exception:
        rows = []
    finally:
        _close_cursor_connection(cursor, connection)

    joined_items = [_featured_quote_from_joined_row(row) for row in rows if row.get("quote_text")]
    if joined_items:
        return joined_items

    connection = None
    cursor = None
    try:
        connection = _connect(config)
        cursor = connection.cursor(dictionary=True)
        cursor.execute(
            """
            SELECT id, title, authors_text, result_json, created_at
            FROM analyses
            ORDER BY created_at DESC
            LIMIT 80
            """
        )
        rows = cursor.fetchall()
    except Exception:
        return []
    finally:
        _close_cursor_connection(cursor, connection)

    items: list[dict[str, Any]] = []
    for row in rows:
        result = _json_value(row.get("result_json"))
        if not isinstance(result, dict):
            continue
        quotes = [quote for quote in result.get("quotes") or [] if quote.get("text")]
        if not quotes:
            continue
        book = result.get("book") or {}
        stats = result.get("stats") or {}
        vocabulary = result.get("vocabulary") or []
        quote = random.choice(quotes)
        title = book.get("title") or row.get("title") or result.get("query") or "未命名书籍"
        authors = book.get("authors")
        author_text = _authors_text(authors) or row.get("authors_text") or "作者未记"
        items.append(
            {
                "analysisId": int(row["id"]),
                "title": title,
                "author": author_text,
                "quote": quote.get("text"),
                "note": quote.get("note"),
                "words": stats.get("words"),
                "vocabularyCount": len(vocabulary) if isinstance(vocabulary, list) else 0,
                "createdAt": _serialize_value(row.get("created_at")),
                "coverUrl": book.get("coverUrl"),
                "coverSeed": sum(ord(char) for char in str(title)) % 6,
            }
        )

    random.shuffle(items)
    return items[: max(1, min(limit, 30))]


def _featured_quote_from_joined_row(row: dict[str, Any]) -> dict[str, Any]:
    result = _json_value(row.get("result_json"))
    stats = _json_value(row.get("stats_json")) or {}
    book = result.get("book") if isinstance(result, dict) else {}
    title = (book or {}).get("title") or row.get("title") or "未命名书籍"
    authors = (book or {}).get("authors")
    author_text = _authors_text(authors) or row.get("authors_text") or "作者未记"
    vocabulary = result.get("vocabulary") if isinstance(result, dict) else []
    return {
        "analysisId": int(row["id"]),
        "title": title,
        "author": author_text,
        "quote": row.get("quote_text"),
        "note": row.get("note"),
        "words": stats.get("words") if isinstance(stats, dict) else None,
        "vocabularyCount": len(vocabulary) if isinstance(vocabulary, list) else 0,
        "createdAt": _serialize_value(row.get("created_at")),
        "coverUrl": (book or {}).get("coverUrl"),
        "coverSeed": sum(ord(char) for char in str(title)) % 6,
    }


def save_clicked_word(analysis_id: int | None, payload: dict[str, Any]) -> dict[str, Any]:
    config = get_mysql_config()
    if not config.enabled:
        return {"saved": False, "reason": "mysql_disabled", "message": "MySQL is disabled."}

    if _mysql_connector() is None:
        return {
            "saved": False,
            "reason": "mysql_connector_missing",
            "message": "mysql-connector-python is missing; clicked word was not saved.",
        }

    word = str(payload.get("word") or "").strip()
    if not word:
        return {"saved": False, "reason": "empty_word", "message": "Word is empty."}

    connection = None
    cursor = None
    try:
        connection = _connect(config)
        cursor = connection.cursor()
        _ensure_clicked_words_table(cursor)
        cursor.execute(
            """
            INSERT INTO booklearner_clicked_words
              (analysis_id, book_title, word, part_of_speech, definition_text, example_text, memory_hint, occurrence_count)
            VALUES
              (%s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
              click_count = click_count + 1,
              last_clicked_at = CURRENT_TIMESTAMP,
              part_of_speech = VALUES(part_of_speech),
              definition_text = VALUES(definition_text),
              example_text = VALUES(example_text),
              memory_hint = VALUES(memory_hint),
              occurrence_count = VALUES(occurrence_count)
            """,
            (
                analysis_id,
                payload.get("bookTitle"),
                word,
                payload.get("partOfSpeech"),
                payload.get("definition"),
                payload.get("example"),
                payload.get("memoryHint"),
                int(payload.get("count") or 0),
            ),
        )
        connection.commit()
    except Exception as exc:
        if connection is not None:
            connection.rollback()
        return {"saved": False, "reason": "mysql_error", "message": f"MySQL save failed: {exc}"}
    finally:
        _close_cursor_connection(cursor, connection)

    return {"saved": True, "message": "Clicked word saved."}


def _mysql_connector():
    try:
        return importlib.import_module("mysql.connector")
    except ImportError:
        return None


def _connect(config: MySQLConfig):
    connector = _mysql_connector()
    if connector is None:
        raise RuntimeError("mysql-connector-python is not installed")
    return connector.connect(
        host=config.host,
        port=config.port,
        database=config.database,
        user=config.user,
        password=config.password,
        charset=config.charset,
        autocommit=False,
    )


def _authors_text(authors: Any) -> str:
    if isinstance(authors, list):
        return " / ".join(str(author) for author in authors if author)
    return str(authors or "")


def _insert_quotes(cursor: Any, analysis_id: int, quotes: list[dict[str, Any]]) -> None:
    rows = [
        (analysis_id, index + 1, quote.get("text"), quote.get("note"), quote.get("score"))
        for index, quote in enumerate(quotes)
    ]
    if rows:
        cursor.executemany(
            """
            INSERT INTO analysis_quotes
              (analysis_id, position, quote_text, note, score)
            VALUES (%s, %s, %s, %s, %s)
            """,
            rows,
        )


def _insert_vocabulary(cursor: Any, analysis_id: int, vocabulary: list[dict[str, Any]]) -> None:
    rows = [
        (
            analysis_id,
            index + 1,
            item.get("word"),
            item.get("partOfSpeech"),
            item.get("definition"),
            item.get("example"),
            item.get("memoryHint"),
            item.get("count"),
        )
        for index, item in enumerate(vocabulary)
    ]
    if rows:
        cursor.executemany(
            """
            INSERT INTO analysis_vocabulary
              (analysis_id, position, word, part_of_speech, definition_text, example_text, memory_hint, occurrence_count)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """,
            rows,
        )


def _ensure_clicked_words_table(cursor: Any) -> None:
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS booklearner_clicked_words (
          id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
          analysis_id BIGINT UNSIGNED NULL,
          book_title VARCHAR(512) NULL,
          word VARCHAR(120) NOT NULL,
          part_of_speech VARCHAR(80) NULL,
          definition_text TEXT NULL,
          example_text TEXT NULL,
          memory_hint TEXT NULL,
          occurrence_count INT NOT NULL DEFAULT 0,
          click_count INT NOT NULL DEFAULT 1,
          first_clicked_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
          last_clicked_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
          PRIMARY KEY (id),
          UNIQUE KEY uniq_clicked_analysis_word (analysis_id, word),
          KEY idx_clicked_word (word),
          KEY idx_clicked_last_clicked_at (last_clicked_at),
          CONSTRAINT fk_clicked_analysis
            FOREIGN KEY (analysis_id) REFERENCES analyses(id)
            ON DELETE SET NULL
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """
    )


def _close_cursor_connection(cursor: Any, connection: Any) -> None:
    if cursor is not None:
        try:
            cursor.close()
        except Exception:
            pass
    if connection is not None:
        try:
            connection.close()
        except Exception:
            pass


def _serialize_row(row: dict[str, Any]) -> dict[str, Any]:
    return {key: _serialize_value(value) for key, value in row.items()}


def _serialize_value(value: Any) -> Any:
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return value


def _json_value(value: Any) -> Any:
    if isinstance(value, (dict, list)):
        return value
    try:
        return json.loads(value)
    except Exception:
        return None
