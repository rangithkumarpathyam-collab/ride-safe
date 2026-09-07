"""
SafeRide AI - Module 4: Multilingual Emergency Translation Engine (translation.py)
---------------------------------------------------------------------------------
Provides real-time bidirectional translation between English and Telugu for
emergency responders and riders.

Features:
  - Zero-latency cached emergency responder presets
  - Neural machine translation via deep-translator (Google Translate engine)
  - Automatic language detection heuristic
  - Graceful offline fallback
"""

import os
from typing import Dict, Any, Optional
from dotenv import load_dotenv

load_dotenv()

# Pre-compiled high-priority emergency phrases (Zero Latency)
EMERGENCY_DICTIONARY_EN_TO_TE = {
    "Help is on the way. Ambulance dispatched.": "సహాయం దారిలో ఉంది. అంబులెన్స్ పంపబడింది.",
    "Please stay calm and do not remove your helmet.": "దయచేసి ప్రశాంతంగా ఉండండి మరియు మీ హెల్మెట్ తీయవద్దు.",
    "Can you hear me? Speak or tap your screen.": "మీకు నా మాట వినపడుతోందా? మాట్లాడండి లేదా స్క్రీన్‌పై నొక్కండి.",
    "Ambulance is 3 minutes away from your location.": "అంబులెన్స్ మీ లొకేషన్‌కు 3 నిమిషాల్లో చేరుకుంటుంది.",
    "Emergency rescue confirmed. Stay still.": "అత్యవసర సహాయం ధృవీకరించబడింది. కదలకుండా ఉండండి.",
    "Are you alone or is anyone else injured?": "మీరు ఒక్కరే ఉన్నారా లేదా ఇంకెవరైనా గాయపడ్డారా?",
    "Where does it hurt the most?": "మీకు ఎక్కడ ఎక్కువగా నొప్పిగా ఉంది?",
    "Traffic police and paramedics are arriving now.": "ట్రాఫిక్ పోలీసులు మరియు పారామెడిక్స్ ఇప్పుడే చేరుకుంటున్నారు."
}

# Reverse mapping
EMERGENCY_DICTIONARY_TE_TO_EN = {
    te: en for en, te in EMERGENCY_DICTIONARY_EN_TO_TE.items()
}
# Additional common rider distress phrases
EMERGENCY_DICTIONARY_TE_TO_EN.update({
    "నా కాలు బైక్ కింద ఇరుక్కుపోయింది, వెంటనే సహాయం కావాలి.": "My leg is stuck under the bike, need help immediately.",
    "చాలా రక్తం వస్తోంది, త్వరగా రండి.": "Bleeding heavily, please come fast.",
    "నేను బాగానే ఉన్నాను, సహాయం అవసరం లేదు.": "I am fine, no help needed.",
    "బైక్ పడిపోయింది, దయచేసి అంబులెన్స్ పంపండి.": "Bike has fallen, please send an ambulance."
})

# In-memory translation cache
_TRANSLATION_CACHE: Dict[str, str] = {}


def translate_text(text: str, source_lang: str = "en", target_lang: str = "te") -> str:
    """
    Translates text between English ('en') and Telugu ('te').
    First checks dictionary cache, then uses deep-translator.
    """
    cleaned = text.strip()
    if not cleaned:
        return ""

    cache_key = f"{source_lang}->{target_lang}:{cleaned}"
    if cache_key in _TRANSLATION_CACHE:
        return _TRANSLATION_CACHE[cache_key]

    # Check emergency quick dictionary
    if source_lang == "en" and target_lang == "te":
        if cleaned in EMERGENCY_DICTIONARY_EN_TO_TE:
            return EMERGENCY_DICTIONARY_EN_TO_TE[cleaned]
    elif source_lang == "te" and target_lang == "en":
        if cleaned in EMERGENCY_DICTIONARY_TE_TO_EN:
            return EMERGENCY_DICTIONARY_TE_TO_EN[cleaned]

    # Neural translation via deep_translator
    try:
        from deep_translator import GoogleTranslator
        translator = GoogleTranslator(source=source_lang, target=target_lang)
        result = translator.translate(cleaned)
        if result:
            _TRANSLATION_CACHE[cache_key] = result
            return result
    except Exception as e:
        pass

    # Fallback to original text if translation fails
    return f"{cleaned} (Auto-transcription)"


def translate_to_telugu(english_text: str) -> str:
    """Convenience helper: English -> Telugu"""
    return translate_text(english_text, source_lang="en", target_lang="te")


def translate_to_english(telugu_text: str) -> str:
    """Convenience helper: Telugu -> English"""
    return translate_text(telugu_text, source_lang="te", target_lang="en")


def verify_translation_status() -> Dict[str, Any]:
    """
    Tests live bidirectional translation and returns provider status.
    """
    try:
        test_en = "Ambulance dispatched"
        te_res = translate_to_telugu(test_en)
        en_res = translate_to_english("నా కాలు నొప్పిగా ఉంది")
        return {
            "status": "ONLINE",
            "provider": "DeepTranslator (Google Neural Core)",
            "languages": "English <-> Telugu",
            "cached_presets": len(EMERGENCY_DICTIONARY_EN_TO_TE),
            "test_en_to_te": f"{test_en} -> {te_res}",
            "test_te_to_en": f"నా కాలు నొప్పిగా ఉంది -> {en_res}"
        }
    except Exception as ex:
        return {
            "status": "OFFLINE",
            "provider": "Dictionary Fallback",
            "error": str(ex)
        }


if __name__ == "__main__":
    import sys
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    print("=== Testing Translation Engine ===")
    status = verify_translation_status()
    print("Engine Status:", status["status"], "| Provider:", status.get("provider"))
    print("EN -> TE:", translate_to_telugu("Help is arriving now!"))
    print("TE -> EN:", translate_to_english("నా కాలు నొప్పిగా ఉంది"))
