import asyncio
import unittest
from unittest.mock import AsyncMock, patch

import httpx

from app.config import Settings
from app.services.dictionary import MerriamWebsterClient, _first_definition, _first_example
from app.services import merriam_webster_web as mw_web


# Synthetic, minimal fixtures of the documented API and public entry structure.
HTML = '''<div class="entry-word-section-container" id="dictionary-entry-1">
<div class="entry-header"><h1 class="hword">testword</h1>
<h2 class="parts-of-speech"><a>noun</a></h2></div>
<span class="pr">ˈtest-wərd</span>
<div class="sense"><span class="dtText"><b class="mw_t_bc">:</b> a test meaning
<span class="dxnls">see something else</span></span>
<div class="ex-sent">A <em>testword</em> appeared.<span class="aq">Author</span></div></div>
<div class="sense"><span class="dtText">second meaning</span>
<div class="ex-sent">Another sense.</div></div></div>
<section class="on-web">Unrelated news example.</section>'''


def api_entry(word="testword", example=True):
    dt = [["text", "{bc}a {it}test{/it} meaning: {sx|sample||1}"]]
    if example:
        dt.append(["vis", [{"t": "A {wi}testword{/wi} appeared."}]])
    return {
        "meta": {"id": word + ":1"},
        "hwi": {"hw": word, "prs": [{"mw": "ˈtest-wərd"}]},
        "fl": "noun", "shortdef": ["short meaning"],
        "def": [{"sseq": [[["sense", {"dt": dt}]],
                          [["sense", {"dt": [["text", "second meaning"],
                                               ["vis", [{"t": "Second example."}]]]}]]]}],
    }


class MerriamWebsterTest(unittest.TestCase):
    def test_official_tagged_verbal_illustration_and_link_tokens(self):
        entry = api_entry()
        self.assertEqual(_first_definition(entry), "a test meaning: sample")
        self.assertEqual(_first_example(entry), "A testword appeared.")

    def test_official_does_not_take_example_from_another_sense(self):
        self.assertIsNone(_first_example(api_entry(example=False)))

    def test_official_shortdef_fallback_does_not_mistake_tag_for_text(self):
        self.assertEqual(_first_definition({"shortdef": ["plain meaning"]}), "plain meaning")
        self.assertEqual(_first_definition(api_entry()), "a test meaning: sample")

    def test_official_binding_substitute_is_parsed(self):
        entry = {"def": [{"sseq": [[["bs", {"sense": {"dt": [["text", "test sense"],
                    ["vis", [{"t": "Test example."}]]]}}]]]}]}
        self.assertEqual(_first_definition(entry), "test sense")
        self.assertEqual(_first_example(entry), "Test example.")

    def test_official_exact_match_skips_related_entry_and_labels_respelling(self):
        payload = [api_entry("unrelated"), api_entry()]
        response = httpx.Response(200, json=payload, request=httpx.Request("GET", "https://www.dictionaryapi.com/"))
        with patch("app.services.dictionary.httpx.AsyncClient.get", new=AsyncMock(return_value=response)):
            entry = asyncio.run(MerriamWebsterClient(Settings(merriam_webster_api_key="test-only")).lookup("TESTWORD"))
        self.assertEqual(entry.english_example, "A testword appeared.")
        self.assertEqual(entry.phonetic, "韦氏标音：ˈtest-wərd")
        self.assertIn("merriam-webster.com/dictionary/", entry.source)

    def test_official_rejects_suggestions_related_words_and_stem_only_matches(self):
        related = api_entry("related")
        related["meta"]["stems"] = ["testword"]
        for payload in (["testword"], [related], {"error": "bad"}):
            response = httpx.Response(200, json=payload, request=httpx.Request("GET", "https://www.dictionaryapi.com/"))
            with patch("app.services.dictionary.httpx.AsyncClient.get", new=AsyncMock(return_value=response)):
                with self.assertRaises(RuntimeError):
                    asyncio.run(MerriamWebsterClient(Settings(merriam_webster_api_key="test-only")).lookup("testword"))

    def test_official_partial_pronunciation_is_not_used(self):
        payload = api_entry()
        payload["hwi"]["prs"] = [{"mw": "-wərd"}]
        response = httpx.Response(200, json=[payload], request=httpx.Request("GET", "https://www.dictionaryapi.com/"))
        with patch("app.services.dictionary.httpx.AsyncClient.get", new=AsyncMock(return_value=response)):
            entry = asyncio.run(MerriamWebsterClient(Settings(merriam_webster_api_key="test-only")).lookup("testword"))
        self.assertIsNone(entry.phonetic)

    def test_official_error_does_not_leak_api_key(self):
        response = httpx.Response(403, request=httpx.Request("GET", "https://www.dictionaryapi.com/test?key=private-key"))
        with patch("app.services.dictionary.httpx.AsyncClient.get", new=AsyncMock(return_value=response)):
            with self.assertRaises(RuntimeError) as error:
                asyncio.run(MerriamWebsterClient(Settings(merriam_webster_api_key="private-key")).lookup("testword"))
        self.assertIn("403", str(error.exception))
        self.assertNotIn("private-key", str(error.exception))

    def test_web_exact_headword_first_sense_and_own_respelling(self):
        entry = mw_web.parse_merriam_webster_entry(HTML, "TESTWORD", "source")
        self.assertEqual(entry.part_of_speech, "noun")
        self.assertEqual(entry.english_definition, "a test meaning")
        self.assertEqual(entry.english_example, "A testword appeared.")
        self.assertEqual(entry.phonetic, "韦氏标音：ˈtest-wərd")
        self.assertIsNone(entry.american_audio_url)
        self.assertEqual(entry.source, "source")

    def test_web_does_not_mix_later_or_pagewide_examples(self):
        html = HTML.replace('<div class="ex-sent">A <em>testword</em> appeared.<span class="aq">Author</span></div>', '')
        self.assertIsNone(mw_web.parse_merriam_webster_entry(html, "testword", "source").english_example)

    def test_web_does_not_take_partial_or_derivative_pronunciation(self):
        html = HTML.replace('ˈtest-wərd', '-wərd').replace('</section>', '</section><div class="uros"><span class="pr">another-word</span></div>')
        self.assertIsNone(mw_web.parse_merriam_webster_entry(html, "testword", "source").phonetic)
        html = HTML.replace('<span class="pr">ˈtest-wərd</span>', '<div class="uros"><span class="pr">another-word</span></div>')
        self.assertIsNone(mw_web.parse_merriam_webster_entry(html, "testword", "source").phonetic)

    def test_web_does_not_mix_a_nested_subsense_example(self):
        html = HTML.replace('<div class="ex-sent">A <em>testword</em> appeared.<span class="aq">Author</span></div>',
                            '<div class="sense"><span class="dtText">Nested meaning</span><div class="ex-sent">Nested example.</div></div>')
        self.assertIsNone(mw_web.parse_merriam_webster_entry(html, "testword", "source").english_example)

    def test_web_rejects_derived_senses_when_main_entry_has_no_definition(self):
        for container in ("uro", "uros", "dro", "dros"):
            html = f'''<div class="entry-word-section-container">
            <div class="entry-header"><h1 class="hword">testword</h1></div>
            <div class="{container}"><h2 class="hword">testwordness</h2>
            <div class="sense"><span class="dtText">a derived meaning</span>
            <div class="ex-sent">A derived example.</div></div></div></div>'''
            with self.subTest(container=container), self.assertRaises(RuntimeError):
                mw_web.parse_merriam_webster_entry(html, "testword", "source")

    def test_web_skips_derived_senses_before_the_main_definition(self):
        for container in ("uro", "uros", "dro", "dros"):
            derived = f'''<div class="{container}"><h2 class="hword">testwordness</h2>
            <div class="sense"><span class="dtText">a derived meaning</span>
            <div class="ex-sent">A derived example.</div></div></div>'''
            html = HTML.replace('<div class="sense">', derived + '<div class="sense">', 1)
            with self.subTest(container=container):
                entry = mw_web.parse_merriam_webster_entry(html, "testword", "source")
                self.assertEqual(entry.english_definition, "a test meaning")
                self.assertEqual(entry.english_example, "A testword appeared.")

    def test_web_does_not_take_derived_example_inside_main_sense(self):
        original = '<div class="ex-sent">A <em>testword</em> appeared.<span class="aq">Author</span></div>'
        for container in ("uro", "uros", "dro", "dros"):
            derived = f'<div class="{container}"><div class="ex-sent">A derived example.</div></div>'
            with self.subTest(container=container):
                entry = mw_web.parse_merriam_webster_entry(HTML.replace(original, derived), "testword", "source")
                self.assertEqual(entry.english_definition, "a test meaning")
                self.assertIsNone(entry.english_example)

    def test_web_does_not_accept_headword_found_only_in_derived_entry(self):
        html = '''<div class="entry-word-section-container">
        <div class="sense"><span class="dtText">a different main word's meaning</span></div>
        <div class="uro"><h2 class="hword">testword</h2></div></div>'''
        with self.assertRaises(RuntimeError):
            mw_web.parse_merriam_webster_entry(html, "testword", "source")

    def test_web_rejects_unrelated_suggestion_and_missing_definition(self):
        for html in (HTML.replace('>testword<', '>different<'), '<h1 class="hword">testword</h1><p>No entry</p>',
                     HTML.replace('class="dtText"', 'class="other"')):
            with self.assertRaises(RuntimeError):
                mw_web.parse_merriam_webster_entry(html, "testword", "source")

    def test_web_accepts_syllable_separators_not_different_words(self):
        html = HTML.replace('>testword<', '>test·\u200bword<')
        self.assertEqual(mw_web.parse_merriam_webster_entry(html, "testword", "source").part_of_speech, "noun")
        with self.assertRaises(RuntimeError):
            mw_web.parse_merriam_webster_entry(html, "test word", "source")

    def test_web_blocks_cool_down_without_repeated_requests(self):
        for status in (401, 403, 429):
            response = httpx.Response(status, request=httpx.Request("GET", "https://www.merriam-webster.com/dictionary/testword"))
            with patch.object(mw_web, "_BLOCKED_UNTIL", 0), patch.object(mw_web.time, "monotonic", return_value=100), \
                 patch.object(mw_web.httpx.AsyncClient, "get", new=AsyncMock(return_value=response)) as get:
                for _ in range(2):
                    with self.assertRaisesRegex(RuntimeError, "暂不接受自动查询"):
                        asyncio.run(mw_web.MerriamWebsterWebClient().lookup("testword"))
                self.assertEqual(get.await_count, 1)
                self.assertEqual(mw_web._BLOCKED_UNTIL, 400)

    def test_web_html_challenge_cools_down(self):
        response = httpx.Response(200, text='<title>Just a moment...</title>', request=httpx.Request("GET", "https://www.merriam-webster.com/dictionary/testword"))
        with patch.object(mw_web, "_BLOCKED_UNTIL", 0), patch.object(mw_web.time, "monotonic", return_value=100), \
             patch.object(mw_web.httpx.AsyncClient, "get", new=AsyncMock(return_value=response)) as get:
            for _ in range(2):
                with self.assertRaisesRegex(RuntimeError, "暂不接受自动查询"):
                    asyncio.run(mw_web.MerriamWebsterWebClient().lookup("testword"))
            self.assertEqual(get.await_count, 1)

    def test_web_client_returns_parsed_entry_after_cooldown(self):
        response = httpx.Response(200, text=HTML, request=httpx.Request("GET", "https://www.merriam-webster.com/dictionary/testword"))
        with patch.object(mw_web, "_BLOCKED_UNTIL", 99), patch.object(mw_web.time, "monotonic", return_value=100), \
             patch.object(mw_web.httpx.AsyncClient, "get", new=AsyncMock(return_value=response)) as get:
            entry = asyncio.run(mw_web.MerriamWebsterWebClient().lookup("TESTWORD"))
            get.assert_awaited_once_with("https://www.merriam-webster.com/dictionary/testword")
        self.assertEqual(entry.english_definition, "a test meaning")

    def test_web_client_rejects_external_destination_and_oversized_page(self):
        responses = [
            httpx.Response(200, text=HTML, request=httpx.Request("GET", "https://other.example/test")),
            httpx.Response(200, text="x" * 2_000_001, request=httpx.Request("GET", "https://www.merriam-webster.com/dictionary/testword")),
        ]
        for response in responses:
            with patch.object(mw_web, "_BLOCKED_UNTIL", 0), \
                 patch.object(mw_web.httpx.AsyncClient, "get", new=AsyncMock(return_value=response)):
                with self.assertRaises(RuntimeError):
                    asyncio.run(mw_web.MerriamWebsterWebClient().lookup("testword"))

    def test_web_timeout_is_not_retried(self):
        with patch.object(mw_web, "_BLOCKED_UNTIL", 0), \
             patch.object(mw_web.httpx.AsyncClient, "get", new=AsyncMock(side_effect=httpx.ReadTimeout("timeout"))) as get:
            with self.assertRaises(httpx.ReadTimeout):
                asyncio.run(mw_web.MerriamWebsterWebClient().lookup("testword"))
        self.assertEqual(get.await_count, 1)


if __name__ == "__main__":
    unittest.main()
