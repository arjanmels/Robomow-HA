#!/usr/bin/env python3
"""Script to translate strings.json into all languages using Google Translate."""
# ruff: noqa: T201

import json
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import TYPE_CHECKING, Any

from deep_translator import GoogleTranslator

if TYPE_CHECKING:
    from collections.abc import Iterator

ROOT = Path("/workspaces/Robomow-HA/custom_components/robomow_ble")
SOURCE_PATH = ROOT / "strings.json"
TRANS_DIR = ROOT / "translations"

with SOURCE_PATH.open("r", encoding="utf-8") as f:
    SOURCE = json.load(f)

SUPPORTED = dict(GoogleTranslator().get_supported_languages(as_dict=True))
SUPPORTED_CODES = {code.lower() for code in SUPPORTED.values()}

LANG_MAP = {
    "he": "iw",
    "nb": "no",
}

TOKEN_RE = re.compile(r"(\{[^{}]+\}|%[a-zA-Z])")


def _protect_tokens(text: str) -> tuple[str, list[str]]:
    tokens: list[str] = []

    def repl(match: re.Match[str]) -> str:
        idx = len(tokens)
        tokens.append(match.group(0))
        return f"__TOK{idx}__"

    return TOKEN_RE.sub(repl, text), tokens


def _restore_tokens(text: str, tokens: list[str]) -> str:
    restored = text
    for idx, token in enumerate(tokens):
        restored = restored.replace(f"__TOK{idx}__", token)
    return restored


def _iter_strings(obj: Any) -> Iterator[str]:
    if isinstance(obj, dict):
        for value in obj.values():
            yield from _iter_strings(value)
    elif isinstance(obj, list):
        for value in obj:
            yield from _iter_strings(value)
    elif isinstance(obj, str):
        yield obj


def _apply_map(obj: Any, mapping: dict[str, str]) -> Any:
    if isinstance(obj, dict):
        return {k: _apply_map(v, mapping) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_apply_map(v, mapping) for v in obj]
    if isinstance(obj, str):
        return mapping.get(obj, obj)
    return obj


def _write_lang_file(lang: str, payload: Any) -> None:
    out_path = TRANS_DIR / f"{lang}.json"
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=4)
        f.write("\n")


def _resolve_translation_target(lang: str) -> str | None:
    lower_lang = lang.lower()
    if lower_lang in SUPPORTED_CODES:
        return lang

    mapped = LANG_MAP.get(lang)
    if mapped and mapped.lower() in SUPPORTED_CODES:
        return mapped

    return None


def _translate_items(
    translator: GoogleTranslator,
    protected_chunk: list[str],
) -> list[str | None]:
    translations: list[str | None] = []
    for item in protected_chunk:
        translated_item = None
        for _ in range(2):
            try:
                translated_item = translator.translate(item)
                break
            except ConnectionError, TimeoutError, ValueError:
                continue
        translations.append(None if translated_item is None else str(translated_item))
    return translations


def _translate_batch(
    translator: GoogleTranslator, protected_chunk: list[str]
) -> list[str | None]:
    for _ in range(3):
        try:
            batch_result = translator.translate_batch(protected_chunk)
            if not isinstance(batch_result, list):
                batch_result = [batch_result]
            return [None if x is None else str(x) for x in batch_result]
        except ConnectionError, TimeoutError, ValueError:
            continue
    return _translate_items(translator, protected_chunk)


def _translate_chunk(translator: GoogleTranslator, chunk: list[str]) -> dict[str, str]:
    protected_chunk: list[str] = []
    token_sets: list[list[str]] = []

    for text in chunk:
        protected, tokens = _protect_tokens(text)
        protected_chunk.append(protected)
        token_sets.append(tokens)

    translated = _translate_batch(translator, protected_chunk)
    return {
        src_text: _restore_tokens(src_text if tr_text is None else tr_text, tokens)
        for src_text, tr_text, tokens in zip(
            chunk, translated, token_sets, strict=False
        )
    }


def _translate_language(lang: str, unique_strings: list[str]) -> str:
    if lang == "en":
        return f"{lang}: skipped source"

    target = _resolve_translation_target(lang)
    if target is None:
        return f"{lang}: unsupported target {lang}, skipped"

    translator = GoogleTranslator(source="en", target=target)
    translated_map: dict[str, str] = {}
    chunk_size = 999

    for i in range(0, len(unique_strings), chunk_size):
        chunk = unique_strings[i : i + chunk_size]
        translated_map.update(_translate_chunk(translator, chunk))

    output = _apply_map(SOURCE, translated_map)
    _write_lang_file(lang, output)
    return f"{lang}: translated via {target}"


def main() -> None:
    """Translate the source strings into all target languages."""
    unique_strings = sorted(set(_iter_strings(SOURCE)))
    languages = sorted(path.stem for path in TRANS_DIR.glob("*.json"))

    with ThreadPoolExecutor(max_workers=24) as executor:
        futures = {
            executor.submit(_translate_language, lang, unique_strings): lang
            for lang in languages
        }
        for future in as_completed(futures):
            exception = future.exception()
            lang = futures[future]
            if exception is not None:
                print(f"{lang}: failed {type(exception).__name__} - {exception}")
                continue
            print(future.result())

    print("DONE")


if __name__ == "__main__":
    main()
