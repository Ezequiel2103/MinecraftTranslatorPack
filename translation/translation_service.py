import re
import threading

import json

from translation.translation_memory import (
    load_memory,
    memory_path,
    translate_with_memory
)
from ai.ai_translator import MockAITranslator, QuotaExceededError
from analyzer.text_protector import protect_text, restore_text
from analyzer.translation_validator import (
    validate_translation,
    validate_translation_quality
)
from translation.retry_manager import TranslationRetryManager
from translation.terminology_manager import load_terminology
from translation.template_manager import load_templates


class TranslationService:

    def __init__(
        self,
        language_pair,
        ai_translator=None,
        protected_terms=None,
        mod_item_glossary=None,
        templates=None,
        cancel_event=None
    ):
        self.language_pair = language_pair
        self.terminology = load_terminology(language_pair)
        self.protected_terms = protected_terms or []
        self.mod_item_glossary = mod_item_glossary or {}
        self.templates = (
            templates if templates is not None
            else load_templates(language_pair)
        )
        self.cancel_event = cancel_event
        self.quota_exceeded = False

        if ai_translator is None:
            ai_translator = MockAITranslator()

        self.ai_translator = ai_translator

        self.retry_manager = TranslationRetryManager(
            max_attempts=3
        )

        self._new_memory_entries = {}
        self._new_memory_lock = threading.Lock()

    def translate(
        self,
        text,
        path=None,
        source_language="en",
        target_language="es",
        terminology=None,
        context=None
    ):

        active_terminology = (
            terminology
            if terminology is not None
            else self.terminology
        )

        lookup_result = self._lookup_without_ai(
            text, path, source_language, target_language,
            active_terminology, context
        )

        if lookup_result is not None:
            return lookup_result

        return self._ai_translate_with_retry(
            text, source_language, target_language,
            active_terminology, context
        )

    def _lookup_without_ai(
        self, text, path, source_language, target_language,
        active_terminology, context
    ):
        """
        Everything translate() can resolve without an AI call: exact
        terminology, this run's own cache, disk memory, the cross-mod
        item glossary, and known fixed-template patterns. Returns None
        if nothing matched, meaning an AI call is actually needed.
        """

        # 1. Exact terminology match
        terminology_translation = active_terminology.get(text)

        if terminology_translation:
            validation = validate_translation(
                text,
                terminology_translation
            )

            if validation["valid"]:
                return {
                    "translation": terminology_translation,
                    "source": "terminology",
                    "valid": True,
                    "validation_reason": None,
                    "attempts": 0
                }

        # 2. Translations already learned earlier in this same run
        # (avoids repeating an AI call for text that appears more than
        # once before it has been flushed to disk).
        with self._new_memory_lock:
            cached_translation = self._new_memory_entries.get(text)

        if cached_translation is not None:
            validation = validate_translation(text, cached_translation)

            if validation["valid"]:
                return {
                    "translation": cached_translation,
                    "source": "run_cache",
                    "valid": True,
                    "validation_reason": None,
                    "attempts": 0
                }

        # 3. Translation memory

        memory_results = translate_with_memory([
            {
                "text": text,
                "path": path or ""
            }
        ], self.language_pair)

        memory_result = memory_results[0]

        if memory_result["translation"]:

            validation = validate_translation(
                text,
                memory_result["translation"]
            )

            if validation["valid"]:

                return {
                    "translation": memory_result["translation"],
                    "source": "memory",
                    "valid": True,
                    "validation_reason": None,
                    "attempts": 0
                }

        # 4. Text already translated while translating one of the mods in
        # this same modpack (e.g. a quest mentions an item name that's
        # already in a mod's own translated lang file).

        glossary_translation = self.mod_item_glossary.get(text)

        if glossary_translation:
            validation = validate_translation(text, glossary_translation)

            if validation["valid"]:
                with self._new_memory_lock:
                    self._new_memory_entries[text] = glossary_translation

                return {
                    "translation": glossary_translation,
                    "source": "mod_glossary",
                    "valid": True,
                    "validation_reason": None,
                    "attempts": 0
                }

        # 5. Template match: a known fixed prefix/suffix (e.g. "&eKill&f: ")
        # with only the middle part actually needing translation.

        template_result = self._try_template_match(
            text, source_language, target_language, context
        )

        if template_result is not None:
            return template_result

        return None

    def _ai_translate_with_retry(
        self, text, source_language, target_language,
        active_terminology, context
    ):
        """
        The single-item AI tier: protects placeholders/mod names, asks
        the AI, validates the result, and retries with feedback on
        failure. Used directly by translate(), and as the fallback for
        any item a batch call didn't come back with a valid answer for.
        """

        protected_text, protected_tokens = protect_text(
            text,
            extra_terms=self.protected_terms
        )

        # Nothing left to translate once placeholders/protected terms are
        # removed (e.g. a title that is only a formatting code plus a
        # protected mod name): keep the original text instead of asking
        # the AI to "translate" an empty string.
        if protected_tokens and not re.sub(
            r"__MTP_PROTECTED_\d+__", "", protected_text
        ).strip():
            return {
                "translation": text,
                "source": "fully_protected",
                "valid": True,
                "validation_reason": None,
                "attempts": 0
            }

        previous_translation = None
        validation_error = None

        for attempt in range(
            self.retry_manager.max_attempts
        ):

            try:
                result = self.ai_translator.translate(
                    protected_text,
                    source_language,
                    target_language,
                    terminology=active_terminology,
                    context=context,
                    previous_translation=previous_translation,
                    validation_error=validation_error
                )
            except QuotaExceededError:
                self.quota_exceeded = True

                if self.cancel_event is not None:
                    self.cancel_event.set()

                return {
                    "translation": None,
                    "source": "quota_exceeded",
                    "valid": False,
                    "validation_reason": "quota_exceeded",
                    "attempts": attempt
                }

            translation = result.get("translation")
            restored_translation = restore_text(
                translation or "",
                protected_tokens
            )

            validation = validate_translation(
                text,
                restored_translation
            )

            quality = validate_translation_quality(
                text,
                restored_translation,
                target_language=target_language
            )

            if validation["valid"] and quality["valid"]:

                with self._new_memory_lock:
                    self._new_memory_entries[text] = restored_translation

                return {
                    "translation": restored_translation,
                    "source": result["source"],
                    "valid": True,
                    "validation_reason": None,
                    "attempts": attempt + 1
                }

            previous_translation = translation

            validation_error = (
                validation["reason"]
                if not validation["valid"]
                else quality["reason"]
            )

        return {
            "translation": None,
            "source": "ai_failed",
            "valid": False,
            "validation_reason": validation_error,
            "attempts": self.retry_manager.max_attempts
        }

    def translate_batch(
        self,
        items,
        source_language="en",
        target_language="es",
        terminology=None,
        batch_size=25
    ):
        """
        Translates many items with as few AI calls as possible.

        Each item first goes through the same non-AI lookup tiers as
        translate() (terminology/run-cache/memory/mod glossary/
        templates); only texts nobody has an answer for yet get grouped
        into batched AI requests, so the fixed cost of the translation
        instructions is paid once per batch instead of once per text.
        Anything a batch response is missing or invalid for falls back
        to the normal single-item AI path with its full retry/feedback
        loop — nothing ends up worse off than calling translate() one at
        a time, it just costs less when the batch mostly succeeds.

        items: list of {"text": ..., "path": ..., "parent_path": ...}
        (parent_path is used as context, matching translate()'s callers).
        Returns a list of result dicts, same order as items.
        """

        active_terminology = (
            terminology
            if terminology is not None
            else self.terminology
        )

        results = [None] * len(items)
        needs_ai = []

        for index, item in enumerate(items):
            lookup_result = self._lookup_without_ai(
                item["text"], item.get("path"), source_language,
                target_language, active_terminology,
                item.get("parent_path")
            )

            if lookup_result is not None:
                results[index] = lookup_result
            else:
                needs_ai.append(index)

        for start in range(0, len(needs_ai), batch_size):
            chunk_indices = needs_ai[start:start + batch_size]

            if self.cancel_event is not None and self.cancel_event.is_set():
                for index in chunk_indices:
                    results[index] = {
                        "translation": None,
                        "source": "cancelled",
                        "valid": False,
                        "validation_reason": "cancelled",
                        "attempts": 0
                    }
                continue

            self._translate_ai_batch(
                chunk_indices, items, results,
                source_language, target_language, active_terminology
            )

        return results

    def _translate_ai_batch(
        self, chunk_indices, items, results,
        source_language, target_language, active_terminology
    ):
        protected_by_id = {}
        tokens_by_id = {}

        for index in chunk_indices:
            text = items[index]["text"]
            protected_text, protected_tokens = protect_text(
                text, extra_terms=self.protected_terms
            )

            if protected_tokens and not re.sub(
                r"__MTP_PROTECTED_\d+__", "", protected_text
            ).strip():
                results[index] = {
                    "translation": text,
                    "source": "fully_protected",
                    "valid": True,
                    "validation_reason": None,
                    "attempts": 0
                }
                continue

            item_id = str(index)
            protected_by_id[item_id] = protected_text
            tokens_by_id[item_id] = protected_tokens

        if not protected_by_id:
            return

        try:
            batch_result = self.ai_translator.translate_batch(
                protected_by_id, source_language, target_language,
                terminology=active_terminology
            )
        except QuotaExceededError:
            self.quota_exceeded = True

            if self.cancel_event is not None:
                self.cancel_event.set()

            for item_id in protected_by_id:
                results[int(item_id)] = {
                    "translation": None,
                    "source": "quota_exceeded",
                    "valid": False,
                    "validation_reason": "quota_exceeded",
                    "attempts": 0
                }
            return

        retry_indices = []

        for item_id in protected_by_id:
            index = int(item_id)
            text = items[index]["text"]
            entry = batch_result.get(item_id) or {}
            translation = entry.get("translation")

            if not translation:
                retry_indices.append(index)
                continue

            restored_translation = restore_text(
                translation, tokens_by_id[item_id]
            )

            validation = validate_translation(text, restored_translation)
            quality = validate_translation_quality(
                text, restored_translation, target_language=target_language
            )

            if validation["valid"] and quality["valid"]:
                with self._new_memory_lock:
                    self._new_memory_entries[text] = restored_translation

                results[index] = {
                    "translation": restored_translation,
                    "source": entry.get("source", "batch"),
                    "valid": True,
                    "validation_reason": None,
                    "attempts": 1
                }
            else:
                retry_indices.append(index)

        for index in retry_indices:
            if self.cancel_event is not None and self.cancel_event.is_set():
                results[index] = {
                    "translation": None,
                    "source": "cancelled",
                    "valid": False,
                    "validation_reason": "cancelled",
                    "attempts": 0
                }
                continue

            item = items[index]
            results[index] = self._ai_translate_with_retry(
                item["text"], source_language, target_language,
                active_terminology, item.get("parent_path")
            )

    def _try_template_match(self, text, source_language, target_language, context):
        """
        Checks known fixed prefix/suffix patterns (see templates.json) and,
        if one matches, translates only the variable middle part through
        the normal pipeline instead of asking the AI for the whole string.
        Safe from infinite recursion: the variable part is always strictly
        shorter than text, since a match requires a non-empty prefix.
        """

        for template in self.templates:
            prefix = template.get("en_prefix", "")
            suffix = template.get("en_suffix", "")

            if not prefix or not text.startswith(prefix):
                continue
            if suffix and not text.endswith(suffix):
                continue

            variable_part = text[len(prefix):]
            if suffix:
                variable_part = variable_part[:len(variable_part) - len(suffix)]

            if not variable_part.strip():
                continue

            variable_result = self.translate(
                variable_part,
                path=None,
                source_language=source_language,
                target_language=target_language,
                context=context
            )

            if not variable_result["valid"] or not variable_result["translation"]:
                continue

            combined = (
                template.get("es_prefix", "")
                + variable_result["translation"]
                + template.get("es_suffix", "")
            )

            validation = validate_translation(text, combined)
            if not validation["valid"]:
                continue

            with self._new_memory_lock:
                self._new_memory_entries[text] = combined

            return {
                "translation": combined,
                "source": "template",
                "valid": True,
                "validation_reason": None,
                "attempts": variable_result.get("attempts", 0)
            }

        return None

    def save_new_translations(self):
        """
        Persists everything learned during this run to translation
        memory in a single write, instead of one disk write per text.
        """

        if not self._new_memory_entries:
            return

        memory = load_memory(self.language_pair)

        for original, translation in self._new_memory_entries.items():
            memory[original] = {
                "translation": translation,
                "type": "ai",
                "source": "manual"
            }

        path = memory_path(self.language_pair)
        path.parent.mkdir(parents=True, exist_ok=True)

        with path.open("w", encoding="utf-8") as file:
            json.dump(memory, file, ensure_ascii=False, indent=4)

        self._new_memory_entries = {}
