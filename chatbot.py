import json
import os
import re
from langdetect import detect, LangDetectException

# Available languages
LANGUAGES = {
    "en": "English",
    "hi": "Hindi",
    "bn": "Bengali",
    "ur": "Urdu",
    "pa": "Punjabi"
}

# Default language
DEFAULT_LANGUAGE = "en"

# Load law data for all languages
law_data = {}
for lang in LANGUAGES.keys():
    try:
        # Load IPC data for this language
        ipc_path = f"lawdata/ipc_sec_{lang}.json"
        if os.path.exists(ipc_path):
            with open(ipc_path, "r", encoding="utf-8") as f:
                ipc_data = json.load(f)
        else:
            # Fallback to English if language file doesn't exist
            with open("lawdata/ipc_sec.json", "r", encoding="utf-8") as f:
                ipc_data = json.load(f)
        
        # Load CrPC data for this language
        crpc_path = f"lawdata/crpc_sec_{lang}.json"
        if os.path.exists(crpc_path):
            with open(crpc_path, "r", encoding="utf-8") as f:
                crpc_data = json.load(f)
        else:
            # Fallback to English if language file doesn't exist
            with open("lawdata/crpc_sec.json", "r", encoding="utf-8") as f:
                crpc_data = json.load(f)
        
        # Combine both into one lookup for this language
        law_data[lang] = {**ipc_data, **crpc_data}
    except Exception as e:
        print(f"Error loading data for language {lang}: {e}")
        # Ensure we have at least English data
        if lang == "en":
            with open("lawdata/ipc_sec.json", "r", encoding="utf-8") as f:
                ipc_data = json.load(f)
            with open("lawdata/crpc_sec.json", "r", encoding="utf-8") as f:
                crpc_data = json.load(f)
            law_data["en"] = {**ipc_data, **crpc_data}

def detect_language(text):
    """Detect the language of the input text"""
    try:
        lang_code = detect(text)
        # Map detected language to our supported languages
        if lang_code == 'hi' or lang_code == 'ne':
            return 'hi'  # Hindi
        elif lang_code == 'bn':
            return 'bn'  # Bengali
        elif lang_code == 'ur':
            return 'ur'  # Urdu
        elif lang_code == 'pa':
            return 'pa'  # Punjabi
        else:
            return 'en'  # Default to English
    except LangDetectException:
        return 'en'  # Default to English if detection fails

def get_lawbot_response(user_input, lang=None):
    """Get response from LawBot in the appropriate language"""
    user_input = user_input.lower()
    
    # Detect language if not specified
    if not lang:
        detected_lang = detect_language(user_input)
    else:
        detected_lang = lang
    
    # Fallback to English if the detected language is not supported
    if detected_lang not in law_data:
        detected_lang = DEFAULT_LANGUAGE
    
    # Get language-specific responses
    responses = {
        "en": {
            "not_found": "❌ Sorry, I couldn't match your issue with a specific law. Please rephrase your question.",
            "section": "📘 Section",
            "summary": "🔍 Summary",
            "steps": "📝 Steps to Take"
        },
        "hi": {
            "not_found": "❌ क्षमा करें, मैं आपके मुद्दे को किसी विशिष्ट कानून से मेल नहीं कर सका। कृपया अपना प्रश्न फिर से बताएं।",
            "section": "📘 धारा",
            "summary": "🔍 सारांश",
            "steps": "📝 कार्रवाई के चरण"
        },
        "bn": {
            "not_found": "❌ দুঃখিত, আমি আপনার সমস্যাটিকে কোনও নির্দিষ্ট আইনের সাথে মেলাতে পারিনি। অনুগ্রহ করে আপনার প্রশ্নটি পুনরায় বলুন।",
            "section": "📘 ধারা",
            "summary": "🔍 সারাংশ",
            "steps": "📝 পদক্ষেপ নিতে"
        },
        "ur": {
            "not_found": "❌ معذرت، میں آپ کے مسئلے کو کسی مخصوص قانون سے مطابقت نہیں کر سکا۔ براہ کرم اپنا سوال دوبارہ بیان کریں۔",
            "section": "📘 سیکشن",
            "summary": "🔍 خلاصہ",
            "steps": "📝 اقدامات"
        },
        "pa": {
            "not_found": "❌ ਮੁਆਫ ਕਰਨਾ, ਮੈਂ ਤੁਹਾਡੇ ਮੁੱਦੇ ਨੂੰ ਕਿਸੇ ਖਾਸ ਕਾਨੂੰਨ ਨਾਲ ਮੇਲ ਨਹੀਂ ਕਰ ਸਕਿਆ। ਕਿਰਪਾ ਕਰਕੇ ਆਪਣਾ ਸਵਾਲ ਦੁਬਾਰਾ ਕਹੋ।",
            "section": "📘 ਸੈਕਸ਼ਨ",
            "summary": "🔍 ਸਾਰ",
            "steps": "📝 ਕਦਮ ਚੁੱਕਣ ਲਈ"
        }
    }
    
    # Search for matching keywords in the detected language
    for section, info in law_data[detected_lang].items():
        for keyword in info.get("keywords", []):
            if all(word in user_input for word in keyword.split()):
                response_text = f"{responses[detected_lang]['section']}: {section} - {info['title']}\n\n"
                response_text += f"{responses[detected_lang]['summary']}: {info['summary']}\n\n"
                response_text += f"{responses[detected_lang]['steps']}:\n"
                for i, step in enumerate(info['steps'], 1):
                    response_text += f"{i}. {step}\n"
                return {
                    "text": response_text,
                    "detected_language": detected_lang
                }
    
    # If no match in detected language, try English as fallback
    if detected_lang != DEFAULT_LANGUAGE:
        for section, info in law_data[DEFAULT_LANGUAGE].items():
            for keyword in info.get("keywords", []):
                if all(word in user_input for word in keyword.split()):
                    response_text = f"{responses[detected_lang]['section']}: {section} - {info['title']}\n\n"
                    response_text += f"{responses[detected_lang]['summary']}: {info['summary']}\n\n"
                    response_text += f"{responses[detected_lang]['steps']}:\n"
                    for i, step in enumerate(info['steps'], 1):
                        response_text += f"{i}. {step}\n"
                    return {
                        "text": response_text,
                        "detected_language": detected_lang
                    }
    
    return {
        "text": responses[detected_lang]["not_found"],
        "detected_language": detected_lang
    }
