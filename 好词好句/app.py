from __future__ import annotations

import argparse
import json
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from booklearner.analyzer import analyze_query, analyze_text, suggest_books
from booklearner.storage import get_analysis, get_storage_status, list_recent_analyses, save_analysis


ROOT = Path(__file__).resolve().parent


class BookLearnerHandler(BaseHTTPRequestHandler):
    server_version = "BookLearner/0.1"

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/api/health":
            self._json({"ok": True, "service": "BookLearner"})
            return

        if parsed.path == "/api/storage":
            self._json(get_storage_status())
            return

        if parsed.path == "/api/history":
            self._json({"items": list_recent_analyses()})
            return

        if parsed.path == "/api/suggest":
            query = parse_qs(parsed.query).get("q", [""])[0].strip()
            self._json({"items": suggest_books(query)})
            return

        history_match = re.fullmatch(r"/api/history/(\d+)", parsed.path)
        if history_match:
            item = get_analysis(int(history_match.group(1)))
            if not item:
                self._json({"error": "记录不存在，或 MySQL 未启用。"}, status=404)
                return
            self._json(item)
            return

        if parsed.path == "/api/analyze":
            query = parse_qs(parsed.query).get("q", [""])[0].strip()
            if not query:
                self._json({"error": "请输入书名或作者名。"}, status=400)
                return
            try:
                result = analyze_query(query)
                result["storage"] = save_analysis(query=query, result=result)
                self._json(result)
            except Exception as exc:  # pragma: no cover - protects the local server UX
                self._json({"error": f"分析失败：{exc}"}, status=500)
            return

        if parsed.path in {"/", "/index.html"}:
            self._json(
                {
                    "ok": True,
                    "service": "BookLearner API",
                    "message": "独立旧页面已退役，请在主应用打开 /booklearner 使用 Vue 页面。",
                }
            )
            return

        self._json({"error": "页面不存在。"}, status=404)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path != "/api/analyze-text":
            self._json({"error": "接口不存在。"}, status=404)
            return

        try:
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
        except Exception:
            self._json({"error": "请求内容不是有效 JSON。"}, status=400)
            return

        text = str(payload.get("text", "")).strip()
        if len(text) < 300:
            self._json({"error": "文本太短，至少粘贴 300 个字符。"}, status=400)
            return

        title = str(payload.get("title", "")).strip() or "粘贴文本"
        author = str(payload.get("author", "")).strip()
        try:
            result = analyze_text(title=title, author=author, text=text)
            result["storage"] = save_analysis(query=title, result=result)
            self._json(result)
        except Exception as exc:  # pragma: no cover
            self._json({"error": f"分析失败：{exc}"}, status=500)

    def log_message(self, format: str, *args: object) -> None:
        print(f"{self.address_string()} - {format % args}")

    def _json(self, payload: dict, status: int = 200) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the BookLearner local API server.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", default=8765, type=int)
    args = parser.parse_args()

    server = ThreadingHTTPServer((args.host, args.port), BookLearnerHandler)
    print(f"BookLearner API running at http://{args.host}:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nBookLearner stopped.")


if __name__ == "__main__":
    main()
