import asyncio
import json
import unittest
from unittest.mock import AsyncMock, patch

import httpx

from app.config import Settings
from app.services import translation as t


def response(data=None, status=200, headers=None):
    return httpx.Response(status, json=data or {}, headers=headers, request=httpx.Request("GET", "https://example.test"))


def settings(**kwargs):
    return Settings(_env_file=None, translation_provider=kwargs.pop("translation_provider", "mymemory"),
                    dashscope_api_key=kwargs.pop("dashscope_api_key", ""), **kwargs)


class TranslationFallbackTest(unittest.TestCase):
    def setUp(self):
        t._TRANSLATIONS.clear()
        t._COOLDOWNS.clear()

    def test_none_disables_all_providers_and_cache(self):
        t._TRANSLATIONS[("none", "", "meaning")] = (t.time.monotonic(), "缓存释义")
        with patch.object(t.httpx.AsyncClient, "get", new=AsyncMock()) as get, \
             patch.object(t.httpx.AsyncClient, "post", new=AsyncMock()) as post:
            self.assertIsNone(asyncio.run(t.TranslationClient(settings(translation_provider="none", dashscope_api_key="test")).translate_definition("meaning")))
            get.assert_not_awaited(); post.assert_not_awaited()

    def test_success_is_cached_across_clients(self):
        result = response({"responseStatus": 200, "responseData": {"translatedText": " 洗涤衣物。 "}})
        with patch.object(t.httpx.AsyncClient, "get", new=AsyncMock(return_value=result)) as get:
            for _ in range(2):
                self.assertEqual(asyncio.run(t.TranslationClient(settings()).translate_definition("to wash clothing")), "洗涤衣物。")
            self.assertEqual(get.await_count, 1)

    def test_other_selected_ai_provider_does_not_use_retained_dashscope_key(self):
        with patch.object(t.httpx.AsyncClient, "post", new=AsyncMock()) as post:
            self.assertIsNone(asyncio.run(t.request_dashscope_json(
                settings(ai_text_provider="openai", dashscope_api_key="unused-test-key"),
                "Translate", {"text": "to wash clothing"},
            )))
            post.assert_not_awaited()

    def test_translation_quota_word_itself_is_not_an_error(self):
        self.assertEqual(t._chinese_translation("允许的一定配额。"), "允许的一定配额。")

    def test_429_uses_configured_text_provider_and_batch_cooldown(self):
        fallback = response({"choices": [{"message": {"content": json.dumps({"translation": "洗涤衣物。"})}}]})
        with patch.object(t.httpx.AsyncClient, "get", new=AsyncMock(return_value=response(status=429, headers={"Retry-After": "120"}))) as get, \
             patch.object(t.httpx.AsyncClient, "post", new=AsyncMock(return_value=fallback)) as post:
            client = t.TranslationClient(settings(dashscope_api_key="not-a-real-key"))
            self.assertEqual(asyncio.run(client.translate_definition("to wash clothing")), "洗涤衣物。")
            self.assertEqual(asyncio.run(client.translate_definition("to clean clothing")), "洗涤衣物。")
            self.assertEqual(get.await_count, 1)
            self.assertEqual(post.await_count, 2)
            payload = post.await_args.kwargs["json"]
            self.assertEqual(json.loads(payload["messages"][1]["content"]), {"english_definition": "to clean clothing"})
            self.assertEqual(payload["response_format"], {"type": "json_object"})

    def test_short_retry_after_is_respected_once(self):
        replies = [response(status=429, headers={"Retry-After": "1"}),
                   response({"responseStatus": "200", "responseData": {"translatedText": "洗涤"}})]
        with patch.object(t.httpx.AsyncClient, "get", new=AsyncMock(side_effect=replies)) as get, \
             patch.object(t.asyncio, "sleep", new=AsyncMock()) as sleep:
            self.assertEqual(asyncio.run(t.TranslationClient(settings()).translate_definition("to wash")), "洗涤")
            self.assertEqual(get.await_count, 2)
            sleep.assert_awaited_once_with(1)

    def test_500_retries_only_once(self):
        with patch.object(t.httpx.AsyncClient, "get", new=AsyncMock(return_value=response(status=503))) as get, \
             patch.object(t.asyncio, "sleep", new=AsyncMock()):
            self.assertIsNone(asyncio.run(t.TranslationClient(settings()).translate_definition("to wash")))
            self.assertEqual(get.await_count, 2)

    def test_http_200_embedded_failure_is_not_a_definition(self):
        for data in [
            {"responseData": {"translatedText": "洗涤"}},
            {"responseStatus": 403, "responseData": {"translatedText": "今日配额已用尽"}},
            {"responseStatus": 429, "responseData": {"translatedText": "洗涤"}},
            {"responseStatus": 200, "responseData": {"translatedText": "MYMEMORY WARNING: YOU USED ALL AVAILABLE FREE TRANSLATIONS FOR TODAY. 次日重试"}},
            {"responseStatus": 200, "responseData": {"translatedText": "No translation found"}},
            {"responseStatus": 200, "responseData": {"translatedText": "<div>洗涤</div>"}},
        ]:
            with self.subTest(data=data):
                t._COOLDOWNS.clear()
                with patch.object(t.httpx.AsyncClient, "get", new=AsyncMock(return_value=response(data))):
                    self.assertIsNone(asyncio.run(t.TranslationClient(settings()).translate_definition("to wash")))
                self.assertFalse(t._TRANSLATIONS)

    def test_timeout_has_safe_none_result(self):
        with patch.object(t.httpx.AsyncClient, "get", new=AsyncMock(side_effect=httpx.ReadTimeout("secret must not escape"))) as get, \
             patch.object(t.asyncio, "sleep", new=AsyncMock()):
            self.assertIsNone(asyncio.run(t.TranslationClient(settings()).translate_definition("to wash")))
            self.assertEqual(get.await_count, 2)

    def test_transient_timeout_retries_once_and_recovers(self):
        replies = [httpx.ReadTimeout("temporary"), response({"responseStatus": 200, "responseData": {"translatedText": "洗涤"}})]
        with patch.object(t.httpx.AsyncClient, "get", new=AsyncMock(side_effect=replies)) as get, \
             patch.object(t.asyncio, "sleep", new=AsyncMock()):
            self.assertEqual(asyncio.run(t.TranslationClient(settings()).translate_definition("to wash")), "洗涤")
            self.assertEqual(get.await_count, 2)

    def test_dashscope_invalid_json_and_non_chinese_are_rejected(self):
        for content in ['```json\n{"translation":"洗涤"}\n```', '{"translation":"to wash"}', '[]', '{}']:
            with self.subTest(content=content), \
                 patch.object(t.TranslationClient, "_mymemory", new=AsyncMock(return_value=None)), \
                 patch.object(t.httpx.AsyncClient, "post", new=AsyncMock(return_value=response({"choices": [{"message": {"content": content}}]}))):
                self.assertIsNone(asyncio.run(t.TranslationClient(settings(dashscope_api_key="test")).translate_definition("to wash")))

    def test_dashscope_failure_cools_down_without_exposing_errors(self):
        with patch.object(t.TranslationClient, "_mymemory", new=AsyncMock(return_value=None)), \
             patch.object(t.httpx.AsyncClient, "post", new=AsyncMock(return_value=response(status=429))) as post:
            client = t.TranslationClient(settings(dashscope_api_key="test"))
            self.assertIsNone(asyncio.run(client.translate_definition("meaning one")))
            self.assertIsNone(asyncio.run(client.translate_definition("meaning two")))
            self.assertEqual(post.await_count, 1)

    def test_libretranslate_success_validated_and_fallback_available(self):
        with patch.object(t.httpx.AsyncClient, "post", new=AsyncMock(return_value=response({"translatedText": "洗涤"}))):
            self.assertEqual(asyncio.run(t.TranslationClient(settings(translation_provider="libretranslate", libretranslate_url="https://example.test")).translate_definition("to wash")), "洗涤")

    def test_success_cache_is_bounded(self):
        with patch.object(t, "_CACHE_LIMIT", 2), \
             patch.object(t.TranslationClient, "_mymemory", new=AsyncMock(return_value="测试翻译")):
            for text in ["one", "two", "three"]:
                asyncio.run(t.TranslationClient(settings()).translate_definition(text))
        self.assertEqual(len(t._TRANSLATIONS), 2)
        self.assertNotIn(("mymemory", "", "one"), t._TRANSLATIONS)

    def test_expired_success_cache_is_refreshed(self):
        t._TRANSLATIONS[("mymemory", "", "to wash")] = (t.time.monotonic() - t._CACHE_TTL - 1, "旧释义")
        with patch.object(t.TranslationClient, "_mymemory", new=AsyncMock(return_value="洗涤")) as get:
            self.assertEqual(asyncio.run(t.TranslationClient(settings()).translate_definition("to wash")), "洗涤")
            get.assert_awaited_once()


if __name__ == "__main__":
    unittest.main()
