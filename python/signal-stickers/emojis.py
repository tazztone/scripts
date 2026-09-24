"""Emoji definitions, metadata, and lookup for Signal stickers.

Shared between classify_and_build.py and review.py.
"""

from typing import Any, Dict, List, Optional, Tuple

# Emoji dictionary: emoji -> {"name": keyword, "category": category, "description": human_desc}
EMOJI_REGISTRY: Dict[str, Dict[str, str]] = {
    # Joy & Positive
    "😀": {"name": "grinning", "category": "smileys", "description": "grinning face"},
    "😃": {"name": "smiley", "category": "smileys", "description": "grinning face with big eyes"},
    "😄": {"name": "smile", "category": "smileys", "description": "grinning face with smiling eyes"},
    "😁": {"name": "beaming", "category": "smileys", "description": "beaming face with smiling eyes"},
    "😆": {"name": "laughing", "category": "smileys", "description": "grinning squinting face"},
    "😅": {"name": "sweat smile", "category": "smileys", "description": "grinning face with sweat"},
    "😂": {"name": "joy", "category": "smileys", "description": "face with tears of joy"},
    "🤣": {"name": "rofl", "category": "smileys", "description": "rolling on the floor laughing"},
    "🙂": {"name": "slight smile", "category": "smileys", "description": "slightly smiling face"},
    "🙃": {"name": "upside down", "category": "smileys", "description": "upside-down face"},
    "😉": {"name": "wink", "category": "smileys", "description": "winking face"},
    "😊": {"name": "blush", "category": "smileys", "description": "smiling face with smiling eyes"},
    "😇": {"name": "halo", "category": "smileys", "description": "smiling face with halo"},
    "🥰": {"name": "hearts", "category": "smileys", "description": "smiling face with hearts"},
    "😍": {"name": "heart eyes", "category": "smileys", "description": "smiling face with heart-eyes"},
    "🤩": {"name": "star struck", "category": "smileys", "description": "star-struck / star eyes"},
    "😘": {"name": "kiss heart", "category": "smileys", "description": "face blowing a kiss"},
    "😗": {"name": "kiss", "category": "smileys", "description": "kissing face"},
    "😚": {"name": "kiss closed eyes", "category": "smileys", "description": "kissing face with closed eyes"},
    "😙": {"name": "kiss smile", "category": "smileys", "description": "kissing face with smiling eyes"},

    # Tongue & Playful
    "😋": {"name": "yum", "category": "tongue", "description": "face savoring food"},
    "😛": {"name": "tongue", "category": "tongue", "description": "face with tongue out"},
    "😜": {"name": "tongue wink", "category": "tongue", "description": "winking face with tongue"},
    "🤪": {"name": "zany", "category": "tongue", "description": "zany / wild face"},
    "😝": {"name": "squint tongue", "category": "tongue", "description": "squinting face with tongue"},
    "🤑": {"name": "money mouth", "category": "tongue", "description": "money-mouth face"},

    # Thinking & Skeptical
    "🤔": {"name": "thinking", "category": "thinking", "description": "thinking face, hand on chin"},
    "🤨": {"name": "raised eyebrow", "category": "thinking", "description": "face with raised eyebrow"},
    "🧐": {"name": "monocle", "category": "thinking", "description": "face with monocle"},
    "🤓": {"name": "nerd", "category": "thinking", "description": "nerd face with glasses"},
    "😎": {"name": "sunglasses", "category": "props", "description": "smiling face with sunglasses"},
    "😏": {"name": "smirk", "category": "smileys", "description": "smirking face"},
    "😒": {"name": "unamused", "category": "negative", "description": "unamused face / side-eye"},
    "🙄": {"name": "rolling eyes", "category": "negative", "description": "face with rolling eyes"},
    "😬": {"name": "grimacing", "category": "negative", "description": "grimacing face / clenched teeth"},
    "🤐": {"name": "zipper mouth", "category": "neutral", "description": "zipper-mouth face"},
    "🤫": {"name": "shushing", "category": "neutral", "description": "shushing face, finger to lips"},
    "🤭": {"name": "hand over mouth", "category": "neutral", "description": "face with hand over mouth"},
    "🤥": {"name": "lying", "category": "neutral", "description": "lying face with long nose"},

    # Neutral & Quiet
    "😐": {"name": "neutral", "category": "neutral", "description": "neutral face"},
    "😑": {"name": "expressionless", "category": "neutral", "description": "expressionless face"},
    "😶": {"name": "no mouth", "category": "neutral", "description": "face without mouth"},
    "😌": {"name": "relieved", "category": "smileys", "description": "relieved / peaceful face"},
    "😴": {"name": "sleeping", "category": "sleep", "description": "sleeping face with zZZ"},
    "🤤": {"name": "drooling", "category": "sleep", "description": "drooling face"},
    "😪": {"name": "sleepy", "category": "sleep", "description": "sleepy face with bubble"},
    "🥱": {"name": "yawning", "category": "sleep", "description": "yawning face"},

    # Sad & Pleading
    "😔": {"name": "pensive", "category": "sad", "description": "pensive face"},
    "😪": {"name": "sleepy", "category": "sad", "description": "sleepy face"},
    "🙁": {"name": "slightly frowning", "category": "sad", "description": "slightly frowning face"},
    "☹️": {"name": "frowning", "category": "sad", "description": "frowning face"},
    "😮‍💨": {"name": "sighing", "category": "sad", "description": "face exhaling"},
    "🥺": {"name": "pleading", "category": "sad", "description": "pleading puppy eyes"},
    "😢": {"name": "cry", "category": "sad", "description": "crying face with single tear"},
    "😭": {"name": "sob", "category": "sad", "description": "loudly crying face with tears streaming"},
    "😥": {"name": "sad relieved", "category": "sad", "description": "sad but relieved face"},
    "😓": {"name": "downcast sweat", "category": "sad", "description": "downcast face with sweat"},

    # Fearful & Shocked
    "😟": {"name": "worried", "category": "fear", "description": "worried face"},
    "😦": {"name": "frowning open mouth", "category": "fear", "description": "frowning face with open mouth"},
    "😧": {"name": "anguished", "category": "fear", "description": "anguished face"},
    "😨": {"name": "fearful", "category": "fear", "description": "fearful face"},
    "😰": {"name": "anxious sweat", "category": "fear", "description": "anxious face with sweat"},
    "😱": {"name": "screaming", "category": "fear", "description": "face screaming in fear / Munch style"},
    "😳": {"name": "flushed", "category": "shock", "description": "flushed face, wide eyes"},
    "🤯": {"name": "mind blown", "category": "shock", "description": "exploding head"},
    "😮": {"name": "open mouth", "category": "shock", "description": "face with open mouth"},
    "😯": {"name": "hushed", "category": "shock", "description": "hushed face"},
    "😲": {"name": "astonished", "category": "shock", "description": "astonished face"},
    "🥱": {"name": "yawn", "category": "sleep", "description": "yawning face"},

    # Angry & Furious
    "😤": {"name": "triumph", "category": "anger", "description": "face with steam from nose / ears"},
    "😠": {"name": "angry", "category": "anger", "description": "angry face with furrowed brow"},
    "😡": {"name": "pouting rage", "category": "anger", "description": "enraged pouting face"},
    "🤬": {"name": "cursing", "category": "anger", "description": "face with symbols on mouth"},
    "😈": {"name": "smiling imp", "category": "props", "description": "smiling face with horns"},
    "👿": {"name": "angry imp", "category": "props", "description": "angry face with horns"},
    "💀": {"name": "skull", "category": "props", "description": "skull / dead laughing"},
    "🤡": {"name": "clown", "category": "props", "description": "clown face"},

    # Ill & Physical Sensation
    "🤢": {"name": "nauseated", "category": "ill", "description": "nauseated green face"},
    "🤮": {"name": "vomiting", "category": "ill", "description": "face vomiting green vomit"},
    "🤧": {"name": "sneezing", "category": "ill", "description": "sneezing face"},
    "🥵": {"name": "hot face", "category": "ill", "description": "hot face with sweat"},
    "🥶": {"name": "cold face", "category": "ill", "description": "freezing cold blue face"},
    "🥴": {"name": "woozy", "category": "ill", "description": "woozy drunk / uneven face"},
    "😵": {"name": "dizzy", "category": "ill", "description": "dizzy face"},
    "😵‍💫": {"name": "spiral eyes", "category": "ill", "description": "face with spiral eyes"},
    "🤕": {"name": "head bandage", "category": "ill", "description": "face with head-bandage"},
    "🤒": {"name": "thermometer", "category": "ill", "description": "face with thermometer"},

    # Gestures / Extras
    "👀": {"name": "eyes", "category": "gestures", "description": "eyes looking sideways / side eye"},
    "👍": {"name": "thumbs up", "category": "gestures", "description": "thumbs up"},
    "👎": {"name": "thumbs down", "category": "gestures", "description": "thumbs down"},
    "🙏": {"name": "folded hands", "category": "gestures", "description": "folded hands / pray / please"},
    "🎉": {"name": "party popper", "category": "props", "description": "party popper celebration"},
    "🔥": {"name": "fire", "category": "props", "description": "fire / lit"},
    "🧠": {"name": "brain", "category": "props", "description": "brain / galaxy brain"},
    "💡": {"name": "light bulb", "category": "props", "description": "light bulb / idea"},
    "❤️": {"name": "red heart", "category": "props", "description": "red heart"},
}

# Whitelist dict for backwards compatibility: emoji -> search term
WHITELIST: Dict[str, str] = {e: d["name"] for e, d in EMOJI_REGISTRY.items()}


def get_all_emojis() -> List[str]:
    """Returns list of all registered emojis."""
    return list(EMOJI_REGISTRY.keys())


def get_emoji_info(emoji: str) -> Optional[Dict[str, str]]:
    """Returns metadata for an emoji or None if not registered."""
    return EMOJI_REGISTRY.get(emoji)


def is_valid_emoji(emoji: str) -> bool:
    """Checks if string is a valid emoji in registry."""
    return emoji in EMOJI_REGISTRY


def extract_emojis(text: str) -> List[str]:
    """Extracts known emojis from text, preserving order, removing duplicates."""
    found = []
    # Match registered emojis (longest first if multi-char like composite emojis)
    # Sort keys by length descending to match composite sequences first
    sorted_emojis = sorted(EMOJI_REGISTRY.keys(), key=len, reverse=True)
    i = 0
    while i < len(text):
        matched = False
        for e in sorted_emojis:
            if text.startswith(e, i):
                if e not in found:
                    found.append(e)
                i += len(e)
                matched = True
                break
        if not matched:
            i += 1
    return found


def validate_emoji_sequence(text: str) -> Tuple[bool, List[str], Optional[str]]:
    """Strictly validates that text consists solely of 1-3 registered emojis.

    Returns:
        (is_valid, extracted_emojis, error_message)
    """
    if not isinstance(text, str):
        return False, [], "Input must be a string."
    clean = "".join(text.split())
    if not clean:
        return False, [], "Emoji assignment cannot be empty."

    extracted = extract_emojis(clean)
    reconstructed = "".join(extracted)
    if reconstructed != clean:
        return False, extracted, "Contains invalid or unregistered characters."
    if not (1 <= len(extracted) <= 3):
        return False, extracted, f"Must have 1 to 3 emojis (found {len(extracted)})."
    return True, extracted, None


def format_emoji_sequence(
    emojis: Any, max_emojis: int = 3, fallback: Optional[str] = "🙂"
) -> Optional[str]:
    """Normalizes an emoji list or string to a compact string of up to max_emojis."""
    if isinstance(emojis, str):
        extracted = extract_emojis(emojis)
    elif isinstance(emojis, (list, tuple)):
        extracted = []
        for item in emojis:
            for e in extract_emojis(str(item)):
                if e not in extracted:
                    extracted.append(e)
    else:
        return fallback

    if not extracted:
        return fallback
    return "".join(extracted[:max_emojis])


def is_valid_emoji_sequence(seq: str) -> bool:
    """Checks if sequence contains solely 1-3 valid registered emojis."""
    valid, _, _ = validate_emoji_sequence(seq)
    return valid


def get_prompt_emoji_catalog() -> str:
    """Returns a structured catalog of emojis grouped by category for LLM prompts."""
    categories: Dict[str, List[str]] = {}
    for emoji, data in EMOJI_REGISTRY.items():
        cat = data.get("category", "other").capitalize()
        categories.setdefault(cat, []).append(f"{emoji} ({data['name']}: {data['description']})")

    lines = []
    for cat, items in categories.items():
        lines.append(f"[{cat}]")
        lines.append(", ".join(items))
    return "\n".join(lines)


def get_related_emojis(emoji: str, limit: int = 10) -> List[str]:
    """Returns emojis from the same category as the input emoji for focused contrast."""
    info = EMOJI_REGISTRY.get(emoji)
    if not info:
        return list(EMOJI_REGISTRY.keys())[:limit]
    cat = info.get("category")
    same_cat = [e for e, d in EMOJI_REGISTRY.items() if d.get("category") == cat and e != emoji]
    fallbacks = ["🤔", "🤨", "🧐", "😏", "🙄", "😒", "😐", "😑", "😌", "😴", "😮", "😲"]
    for fb in fallbacks:
        if fb != emoji and fb not in same_cat:
            same_cat.append(fb)
    return [emoji] + same_cat[: limit - 1]

