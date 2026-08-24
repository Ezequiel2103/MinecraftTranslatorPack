import re
import threading

from json_io import write_json_atomic
from translation.translation_memory import (
    load_memory,
    memory_path,
    translate_with_memory
)
from ai.ai_translator import MockAITranslator, QuotaExceededError
from analyzer.text_protector import protect_text, restore_text
from analyzer.translation_validator import (
    attempt_placeholder_repair,
    validate_translation,
    validate_translation_quality
)
from translation.retry_manager import TranslationRetryManager
from translation.terminology_manager import load_terminology
from translation.template_manager import load_templates


_WORD_PATTERN = re.compile(r"[A-Za-z]+")

# Short/common words skipped when looking for text Argos left untranslated:
# either too generic to signal a real miss (stopwords) or short enough that
# a match is more likely a coincidental substring than real leftover English.
_COMMON_ENGLISH_WORDS = {
    "a", "an", "the", "of", "in", "on", "for", "to", "and", "or",
    "with", "by", "from", "is", "at", "as"
}

# Bounds for the minimal-pair word inference below: phrases longer than
# this are quest sentences, not item names, and not what this is for;
# a skeleton shared by more than this many phrases is more likely a
# generic carrier ("Compressed *") than a useful signal, and comparing
# every pair inside a huge group gets expensive for no real benefit.
_INFER_MAX_WORDS = 5
_INFER_MAX_GROUP_SIZE = 200


def _diff_single_word(translation_a, translation_b):
    """
    If two translations have the same word count and differ at exactly
    one position, returns that word from each side. Returns (None, None)
    for anything messier -- a different word count (reordering, an
    article added/dropped), more than one differing position, or
    punctuation stuck to the word -- since a clean answer isn't
    guessable from a messy diff. Deliberately simple/fast (plain
    position-by-position comparison, not a general sequence diff): this
    runs over every minimal pair found across the whole glossary, so it
    needs to stay cheap per call.
    """

    tokens_a = translation_a.split()
    tokens_b = translation_b.split()

    if not tokens_a or len(tokens_a) != len(tokens_b):
        return None, None

    diff_positions = [
        index for index in range(len(tokens_a))
        if tokens_a[index] != tokens_b[index]
    ]

    if len(diff_positions) != 1:
        return None, None

    index = diff_positions[0]
    word_a = tokens_a[index].strip(".,;:()")
    word_b = tokens_b[index].strip(".,;:()")

    if not word_a.isalpha() or not word_b.isalpha():
        return None, None

    return word_a, word_b


def _infer_word_translations(pairs):
    """
    Infers single-word translations from minimal pairs already sitting
    in existing multi-word entries: two phrases whose English side
    differs by exactly one word, whose Spanish side also differs by
    exactly one word, pin down that word's translation the same way a
    person spotting the pattern by eye would -- seeing "Iron Ingot" ->
    "Lingote de Hierro" and "Copper Ingot" -> "Lingote de Cobre" reveals
    "Iron" -> "Hierro" and "Ingot" -> "Lingote", even though neither word
    was ever saved on its own. A word that gets two conflicting inferred
    translations from different pairs is dropped rather than guessed at
    -- the same conflict-safe rule the cross-mod glossary itself uses.

    pairs: iterable of (original_text, translation_text).
    Returns {lowercased_english_word: translated_word}.
    """

    skeleton_groups = {}

    for original, translation in pairs:
        words = original.split()

        if len(words) < 2 or len(words) > _INFER_MAX_WORDS:
            continue

        for position in range(len(words)):
            skeleton = tuple(
                words[:position] + ["*"] + words[position + 1:]
            )
            skeleton_groups.setdefault(skeleton, []).append(
                (words[position], translation)
            )

    inferred = {}
    conflicted = set()

    for group in skeleton_groups.values():
        if len(group) < 2 or len(group) > _INFER_MAX_GROUP_SIZE:
            continue

        for a in range(len(group)):
            word_a, translation_a = group[a]

            for b in range(a + 1, len(group)):
                word_b, translation_b = group[b]

                if word_a.lower() == word_b.lower():
                    continue

                diff_a, diff_b = _diff_single_word(translation_a, translation_b)

                if diff_a is None:
                    continue

                for word, piece in ((word_a, diff_a), (word_b, diff_b)):
                    key = word.lower()

                    if key in conflicted:
                        continue

                    existing = inferred.get(key)

                    if existing is None:
                        inferred[key] = piece
                    elif existing.lower() != piece.lower():
                        conflicted.add(key)
                        del inferred[key]

    return inferred


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
        self._skeleton_index_cache = None
        self._skeleton_index_lock = threading.Lock()
        self._word_glossary_cache = None
        self._word_glossary_lock = threading.Lock()

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

        # 6. Skeleton match: same fixed wording as an existing memory
        # entry, differing only in the protected content (a color-coded
        # name, a placeholder value...). Same idea as the hand-written
        # templates above, but discovered automatically from whatever is
        # already in memory instead of needing to be curated by hand.

        skeleton_result = self._try_skeleton_match(text)

        if skeleton_result is not None:
            return skeleton_result

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

            if result.get("source") == "argos_translate":
                word_repaired = self._repair_leftover_words(
                    text, restored_translation
                )
                if word_repaired is not None:
                    restored_translation = word_repaired

            validation = validate_translation(
                text,
                restored_translation
            )

            if not validation["valid"]:
                repaired = attempt_placeholder_repair(text, restored_translation)
                if repaired is not None:
                    restored_translation = repaired
                    validation = validate_translation(text, restored_translation)

            quality = validate_translation_quality(
                text,
                restored_translation,
                target_language=target_language
            )

            if validation["valid"] and quality["valid"]:

                # Argos sometimes leaves a word untranslated without
                # tripping any of the checks above (it's not empty, not
                # unchanged as a whole, not the wrong script). Word-level
                # repair above already fixed what it could recognize; if
                # something is still left over, don't ship it silently —
                # send it to Pending for a human to check. Argos ignores
                # retry feedback, so another attempt on it would just
                # produce the exact same result: no point looping.
                if result.get("source") == "argos_translate" and (
                    self._has_leftover_words(text, restored_translation)
                ):
                    return {
                        "translation": restored_translation,
                        "source": result["source"],
                        "valid": False,
                        "validation_reason": "possible_untranslated_words",
                        "attempts": attempt + 1
                    }

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

            entry_source = entry.get("source", "batch")

            if entry_source == "argos_translate":
                word_repaired = self._repair_leftover_words(
                    text, restored_translation
                )
                if word_repaired is not None:
                    restored_translation = word_repaired

            validation = validate_translation(text, restored_translation)

            if not validation["valid"]:
                repaired = attempt_placeholder_repair(text, restored_translation)
                if repaired is not None:
                    restored_translation = repaired
                    validation = validate_translation(text, restored_translation)

            quality = validate_translation_quality(
                text, restored_translation, target_language=target_language
            )

            if validation["valid"] and quality["valid"]:
                # Same reasoning as the single-item path: a leftover word
                # Argos couldn't be repaired for goes to Pending instead
                # of being retried (retrying won't change Argos's answer).
                if entry_source == "argos_translate" and (
                    self._has_leftover_words(text, restored_translation)
                ):
                    results[index] = {
                        "translation": restored_translation,
                        "source": entry_source,
                        "valid": False,
                        "validation_reason": "possible_untranslated_words",
                        "attempts": 1
                    }
                    continue

                with self._new_memory_lock:
                    self._new_memory_entries[text] = restored_translation

                results[index] = {
                    "translation": restored_translation,
                    "source": entry_source,
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

    def _word_glossary(self):
        """
        Single-word English->Spanish pairs used to patch words a weak
        engine (Argos) leaves untranslated inside a short item/block
        name. Two sources, direct entries taking priority:

        1. Words already saved on their own in the item glossary/memory.
        2. Words inferred from minimal pairs of existing multi-word
           entries (see _infer_word_translations) -- e.g. "Iron" ->
           "Hierro" deduced from "Iron Ingot"/"Copper Ingot" even though
           "Iron" alone was never translated before.

        A multi-word phrase's translation is never sliced apart on its
        own (Spanish reorders and inflects), only used as input to the
        minimal-pair inference above, which only accepts a slice when a
        second, differing phrase confirms exactly where it splits. Built
        once per service instance and cached, same as the skeleton index.
        """

        with self._word_glossary_lock:
            if self._word_glossary_cache is not None:
                return self._word_glossary_cache

            memory = load_memory(self.language_pair)

            memory_words = {
                original: (
                    entry.get("translation") if isinstance(entry, dict) else entry
                )
                for original, entry in memory.items()
            }

            word_glossary = {}
            multiword_pairs = []

            for source in (self.mod_item_glossary, memory_words):
                for original, translation in source.items():
                    if not original or not translation:
                        continue

                    original = original.strip()
                    translation = translation.strip()

                    if not original or not translation:
                        continue

                    if original.isalpha() and " " not in original:
                        word_glossary.setdefault(original.lower(), translation)
                    else:
                        multiword_pairs.append((original, translation))

            for word, translation in _infer_word_translations(
                multiword_pairs
            ).items():
                word_glossary.setdefault(word, translation)

            self._word_glossary_cache = word_glossary
            return word_glossary

    def _repair_leftover_words(self, original, translation):
        """
        Swaps in known single-word translations for any word from the
        original text that's still sitting untranslated, verbatim, inside
        the translation — the specific weak spot Argos has on short,
        context-free noun phrases like item/block names. Returns None if
        nothing needed fixing (or nothing could be fixed), leaving the
        translation untouched.
        """

        word_glossary = self._word_glossary()
        protected_words = {term.lower() for term in self.protected_terms}
        repaired = translation
        changed = False

        for word in set(_WORD_PATTERN.findall(original)):
            if word.lower() in protected_words:
                continue

            replacement = word_glossary.get(word.lower())

            if not replacement:
                continue

            pattern = re.compile(r"\b" + re.escape(word) + r"\b")

            if not pattern.search(repaired):
                continue

            repaired = pattern.sub(replacement, repaired, count=1)
            changed = True

        if not changed:
            return None

        return repaired

    def _has_leftover_words(self, original, translation):
        """
        Heuristic safety net for the Argos path: true if a word from the
        original text (that word repair above couldn't resolve) is still
        sitting untouched in the translation. Short/common words are
        skipped since a match there is more likely a coincidence than a
        real miss. This can flag genuine coincidences too — a word that's
        legitimately spelled the same in Spanish — which is the safe
        direction to err in: it only sends a result to Pending for a
        human to glance at, never blocks or breaks anything.
        """

        protected_words = {term.lower() for term in self.protected_terms}

        for word in set(_WORD_PATTERN.findall(original)):
            lowered = word.lower()

            if len(word) < 3:
                continue
            if lowered in protected_words or lowered in _COMMON_ENGLISH_WORDS:
                continue
            if re.search(r"\b" + re.escape(word) + r"\b", translation):
                return True

        return False

    def _skeleton_index(self):
        """
        Groups every disk-memory entry by its "skeleton" — the text with
        color codes, placeholders and protected mod names blanked out to
        __MTP_PROTECTED_N__ markers — so a brand new text sharing that
        exact skeleton with something already translated can reuse it by
        swapping in its own protected content, instead of asking the AI
        to translate a sentence it has effectively already seen. Built
        once per service instance and cached, since disk memory doesn't
        change out from under a single translation run.
        """

        with self._skeleton_index_lock:
            if self._skeleton_index_cache is not None:
                return self._skeleton_index_cache

            index = {}
            memory = load_memory(self.language_pair)

            for original, entry in memory.items():
                translation = (
                    entry.get("translation") if isinstance(entry, dict) else entry
                )

                if not translation:
                    continue

                skeleton, tokens = protect_text(
                    original, extra_terms=self.protected_terms
                )

                # No protected content at all: this is just plain text,
                # already covered by the exact-match memory tier — a
                # skeleton with nothing blanked out isn't a template.
                if not tokens:
                    continue

                index.setdefault(skeleton, []).append((original, translation))

            self._skeleton_index_cache = index
            return index

    def _try_skeleton_match(self, text):
        protected_text, protected_tokens = protect_text(
            text, extra_terms=self.protected_terms
        )

        if not protected_tokens:
            return None

        candidates = self._skeleton_index().get(protected_text)

        if not candidates:
            return None

        for original_text, translation_text in candidates:
            if original_text == text:
                continue

            candidate_translation_skeleton, candidate_translation_tokens = (
                protect_text(translation_text, extra_terms=self.protected_terms)
            )

            if len(candidate_translation_tokens) != len(protected_tokens):
                continue

            combined = restore_text(
                candidate_translation_skeleton, protected_tokens
            )

            validation = validate_translation(text, combined)

            if not validation["valid"]:
                continue

            with self._new_memory_lock:
                self._new_memory_entries[text] = combined

            return {
                "translation": combined,
                "source": "skeleton_match",
                "valid": True,
                "validation_reason": None,
                "attempts": 0
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

        write_json_atomic(
            memory_path(self.language_pair), memory,
            ensure_ascii=False, indent=4
        )

        self._new_memory_entries = {}
