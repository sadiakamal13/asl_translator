"""
LLM Translation Bridge
Reads translate_request events from the detector, queries Ollama,
and returns a structured translation with diff markup.
"""

import json
import sys
import requests
import re

OLLAMA_URL   = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "llama3"      # change to llama3.2, mistral, etc. if needed


SYSTEM_PROMPT = """You are an expert ASL (American Sign Language) interpreter.
You receive a sequence of ASL signs and associated facial expressions/grammatical markers.
Your job is to produce a natural English translation.

IMPORTANT RULES:
1. ASL grammar differs from English — it is topic-comment, often omits articles/auxiliaries.
2. Facial expressions carry grammatical weight in ASL:
   - raised_eyebrows + yes/no_question → turn into a yes/no question
   - furrowed_brows + wh_question → turn into a who/what/where/when/why question
   - puffed_cheeks + large_size_or_intensity → add intensity words (very, huge, etc.)
   - smile + positive_sentiment → use positive, warm language
   - grimace + negative_or_difficult → reflect difficulty or negativity
   - squinted_eyes + intensity_or_negation → consider negation or strong emphasis
   - head_tilt + rhetorical_or_topicalization → may indicate topic shift

3. Return ONLY valid JSON, no markdown, no backticks, no commentary.

JSON format:
{
  "raw_gloss": "the signs as-is, space separated",
  "translation": "natural English sentence",
  "modified_words": ["word1", "word2"],
  "confidence": 0.0 to 1.0,
  "notes": "brief interpreter note or empty string"
}

modified_words must be the exact words in translation that you added or changed
to make the English flow naturally (articles, auxiliaries, tense markers, etc.).
"""


def build_prompt(sequence: list) -> str:
    signs    = [s["sign"] for s in sequence]
    all_mods = []
    all_expr = []
    for s in sequence:
        all_mods.extend(s.get("modifiers", []))
        all_expr.extend(s.get("expressions", []))

    unique_mods = list(dict.fromkeys(all_mods))
    unique_expr = list(dict.fromkeys(all_expr))

    return (
        f"ASL sign sequence: {' '.join(signs)}\n"
        f"Facial expressions observed: {', '.join(unique_expr) if unique_expr else 'neutral'}\n"
        f"Grammatical modifiers: {', '.join(unique_mods) if unique_mods else 'none'}\n\n"
        "Translate this ASL into natural English."
    )


def query_ollama(prompt: str) -> dict:
    payload = {
        "model":  OLLAMA_MODEL,
        "prompt": f"{SYSTEM_PROMPT}\n\nUSER:\n{prompt}\n\nASSISTANT:",
        "stream": False,
        "options": {
            "temperature": 0.3,
            "top_p":       0.9,
        },
    }
    try:
        resp = requests.post(OLLAMA_URL, json=payload, timeout=30)
        resp.raise_for_status()
        raw_text = resp.json().get("response", "")

        # Strip any accidental markdown fences
        raw_text = re.sub(r"```json|```", "", raw_text).strip()

        result = json.loads(raw_text)
        return result
    except requests.exceptions.ConnectionError:
        return {
            "raw_gloss":      " ".join([]),
            "translation":    "[Ollama not running — start with: ollama serve]",
            "modified_words": [],
            "confidence":     0.0,
            "notes":          "Connection to Ollama failed.",
        }
    except (json.JSONDecodeError, KeyError) as e:
        return {
            "raw_gloss":      "",
            "translation":    f"[Parse error: {e}]",
            "modified_words": [],
            "confidence":     0.0,
            "notes":          str(e),
        }


def emit(data: dict):
    sys.stdout.write(json.dumps(data) + "\n")
    sys.stdout.flush()


def run():
    """Read translate_request lines from stdin, respond with translation."""
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue

        if event.get("type") != "translate_request":
            continue

        sequence = event.get("sequence", [])
        if not sequence:
            continue

        prompt   = build_prompt(sequence)
        result   = query_ollama(prompt)

        emit({
            "type":         "translation",
            "raw_gloss":    result.get("raw_gloss",      ""),
            "translation":  result.get("translation",    ""),
            "modified":     result.get("modified_words", []),
            "confidence":   result.get("confidence",     0.0),
            "notes":        result.get("notes",          ""),
            "sequence":     sequence,
        })


if __name__ == "__main__":
    run()
