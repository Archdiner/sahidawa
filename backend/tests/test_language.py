from app.utils.language import detect_language


def test_english_detection():
    assert detect_language("crocin 500mg") == "en"


def test_hindi_detection():
    assert detect_language("पेरासिटामोल की कीमत बताओ") == "hi"


def test_mixed_defaults_english():
    assert detect_language("crocin tablet दो") == "en"
