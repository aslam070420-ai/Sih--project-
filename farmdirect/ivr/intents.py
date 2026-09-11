"""IVR intent recognizer.

Pure-Python rule-based NLU. No external API key, works 100% offline —
just like the rest of FarmDirect's AI stack (forecasting / pricing /
routing all use local scikit-learn + rules).

Inputs: a spoken/typed phrase (Tamil, English, Tanglish) or a DTMF key.
Output: a structured ``IntentResult`` with the top-level intent and
extracted entities (product, quantity, unit, price, grade, harvest).

Why rule-based for a hackathon:
  * deterministic and explainable (matches the app's AI philosophy)
  * zero extra infrastructure
  * trivially supports Tamil + Tanglish without a Tamil-language model
  * easy to extend via ``PRODUCT_SYNONYMS`` + keyword lists
"""
from dataclasses import dataclass, field, asdict
from typing import Optional, Dict, Any

from .products_dict import normalize_product
from .numbers import parse_quantity, parse_price, parse_grade, parse_harvest_offset

# ----------------------------------------------------------------- intent constants
LIST_PRODUCE   = "LIST_PRODUCE"
MARKET_PRICE   = "MARKET_PRICE"
ORDER_STATUS   = "ORDER_STATUS"
DELIVERY_STATUS= "DELIVERY_STATUS"
BULK_ORDER     = "BULK_ORDER"
EARNINGS       = "EARNINGS"
HELP           = "HELP"
LANGUAGE_CHANGE= "LANGUAGE_CHANGE"
MORE_SERVICES  = "MORE_SERVICES"
DEMAND_FORECAST= "DEMAND_FORECAST"
MY_LISTINGS    = "MY_LISTINGS"
PAYMENT_STATUS = "PAYMENT_STATUS"
PROFILE_SUMMARY= "PROFILE_SUMMARY"
AI_PRICE_RECOMMENDATION = "AI_PRICE_RECOMMENDATION"
PLACE_ORDER    = "PLACE_ORDER"
CANCEL         = "CANCEL"
CONFIRM        = "CONFIRM"
CHANGE         = "CHANGE"
REPEAT         = "REPEAT"
GO_BACK        = "GO_BACK"
MAIN_MENU      = "MAIN_MENU"
UNKNOWN        = "UNKNOWN"
RAW_NUMBER     = "RAW_NUMBER"      # used inside listing flow when user just said '100'

# Tamil keyword groups — order matters, more specific first
_TAMIL_PRICE_WORDS = ["விலை", "விலையை", "விலையென்ன", "விலை என்ன"]
_TAMIL_LIST_WORDS  = ["விற்க", "விற்பனை", "பதிவு", "என்னிடம்", "இருக்கு", "விளைபொருள்"]
_TAMIL_ORDER_WORDS = ["ஆர்டர்", "ஆர்டர்கள்", "ஆர்டர் எங்கே", "எனது ஆர்டர்"]
_TAMIL_DELIVERY_WORDS = ["டெலிவரி", "pickup", "பிக்கப்", "டெலிவரி நிலை"]
_TAMIL_BULK_WORDS = ["மொத்த", "பெரிய ஆர்டர்", "பெரிய ஆர்டர் ஏதாவது", "bulk"]
_TAMIL_EARN_WORDS = ["வருமானம்", "வருமானத்தை", "பணம்", "எவ்வளவு பணம்", "எனக்கு எவ்வளவு"]
_TAMIL_HELP_WORDS = ["உதவி", "உதவிக்கு", "எப்படி", "என்ன செய்ய"]
_TAMIL_CANCEL_WORDS = ["ரத்து", "ரத்து செய்", "வேண்டாம்"]
_TAMIL_REPEAT_WORDS = ["மீண்டும்", "மீண்டும் சொல்லுங்கள்", "திரும்ப சொல்லுங்கள்"]
_TAMIL_BACK_WORDS = ["பின்னாடி", "பின்னாடி போ", "திரும்பி போ", "பின்"]
_TAMIL_MAIN_MENU_WORDS = ["முக்கிய மெனு", "முதன்மை மெனு", "பிரதான மெனு"]
_TAMIL_CONFIRM_WORDS = ["சரி", "ஆம்", "பதிவு செய்", "உறுதி", "சரி பதிவு செய்"]
_TAMIL_CHANGE_WORDS = ["மாற்ற", "மாற்று", "வேறு"]

_EN_PRICE_WORDS = ["price", "what price", "today price", "market price", "rate"]
_EN_LIST_WORDS  = ["i have", "sell", "list", "listing", "produce", "harvest"]
_EN_ORDER_WORDS = ["my order", "where is my order", "order status", "orders"]
_EN_DELIVERY_WORDS = ["delivery", "pickup", "delivery status", "where is the delivery"]
_EN_BULK_WORDS = ["bulk", "bulk order", "big order", "any bulk"]
_EN_EARN_WORDS = ["earnings", "income", "how much money", "money received", "payment"]
_EN_HELP_WORDS = ["help", "how to", "support"]
_EN_CANCEL_WORDS = ["cancel", "no", "never mind", "stop"]
_EN_REPEAT_WORDS = ["repeat", "say again", "again", "what did you say"]
_EN_BACK_WORDS = ["back", "go back", "previous"]
_EN_MAIN_MENU_WORDS = ["main menu", "home", "start over"]
_EN_CONFIRM_WORDS = ["confirm", "yes", "ok", "okay", "go ahead", "register", "submit"]
_EN_CHANGE_WORDS = ["change", "edit", "modify", "different"]
_EN_MORE_WORDS = ["more services", "more options", "other services", "extra services"]
_TAMIL_MORE_WORDS = ["மேலும் சேவை", "மேலும் சேவைகள்", "வேறு சேவை", "கூடுதல் சேவை"]
_TAMIL_PLACE_ORDER_WORDS = ["ஆர்டர் செய்ய", "புதிய ஆர்டர்", "வாங்க வேண்டும்", "வாங்க", "பொருள் வாங்க"]
_EN_PLACE_ORDER_WORDS = ["place order", "new order", "buy produce", "buy product", "buy vegetables", "i want to buy"]


_TANG_HELPERS = ["enna", "irukku", "irukkku", "engga", "enga", "vendam", "seri", "ok"]


# Primary menu speech vocabulary for the rest of India's Scheduled Languages.
# DTMF remains the deterministic fallback for every flow; these keywords make
# the top-level voice menu naturally usable in the selected language too.
_MULTI_MENU_WORDS = {
    "hi": {"price":["बाजार भाव","कीमत","भाव"],"list":["उपज बेच","उत्पादन बेच","बेचना"],"order":["ऑर्डर"],"delivery":["डिलीवरी"],"bulk":["थोक"],"earn":["कमाई","आय"],"help":["मदद","सहायता"],"language":["भाषा"]},
    "te": {"price":["మార్కెట్ ధర","ధర"],"list":["పంట అమ్మ","అమ్మకానికి","ఉత్పత్తి అమ్మ"],"order":["ఆర్డర్"],"delivery":["డెలివరీ"],"bulk":["బల్క్"],"earn":["ఆదాయం","సంపాదన"],"help":["సహాయం"],"language":["భాష"]},
    "kn": {"price":["ಮಾರುಕಟ್ಟೆ ಬೆಲೆ","ಬೆಲೆ"],"list":["ಮಾರಾಟ","ಉತ್ಪನ್ನ","ಬೆಳೆ ಮಾರಾಟ"],"order":["ಆರ್ಡರ್"],"delivery":["ವಿತರಣೆ","ಡೆಲಿವರಿ"],"bulk":["ಸಗಟು"],"earn":["ಆದಾಯ"],"help":["ಸಹಾಯ"],"language":["ಭಾಷೆ"]},
    "ml": {"price":["മാർക്കറ്റ് വില","വില"],"list":["വിൽപ്പന","ഉൽപ്പന്നം വിൽക്ക"],"order":["ഓർഡർ"],"delivery":["ഡെലിവറി"],"bulk":["ബൾക്ക്"],"earn":["വരുമാനം"],"help":["സഹായം"],"language":["ഭാഷ"]},
    "mr": {"price":["बाजारभाव","बाजार भाव","किंमत"],"list":["उत्पादन विक","पीक विक","विक्री"],"order":["ऑर्डर"],"delivery":["डिलिव्हरी"],"bulk":["घाऊक"],"earn":["कमाई","उत्पन्न"],"help":["मदत"],"language":["भाषा"]},
    "bn": {"price":["বাজারদর","বাজার দর","দাম","মূল্য"],"list":["পণ্য বিক্রি","বিক্রি"],"order":["অর্ডার"],"delivery":["ডেলিভারি"],"bulk":["পাইকারি"],"earn":["আয়"],"help":["সহায়তা","সাহায্য"],"language":["ভাষা"]},
    "gu": {"price":["બજાર ભાવ","ભાવ","કિંમત"],"list":["ઉત્પાદન વેચ","વેચાણ"],"order":["ઓર્ડર"],"delivery":["ડિલિવરી"],"bulk":["બલ્ક"],"earn":["આવક"],"help":["મદદ"],"language":["ભાષા"]},
    "pa": {"price":["ਮਾਰਕੀਟ ਕੀਮਤ","ਕੀਮਤ","ਭਾਅ"],"list":["ਉਪਜ ਵੇਚ","ਵੇਚਣ"],"order":["ਆਰਡਰ"],"delivery":["ਡਿਲਿਵਰੀ"],"bulk":["ਥੋਕ"],"earn":["ਕਮਾਈ"],"help":["ਮਦਦ"],"language":["ਭਾਸ਼ਾ"]},
    "or": {"price":["ବଜାର ଦର","ଦର","ମୂଲ୍ୟ"],"list":["ଉତ୍ପାଦ ବିକ୍ରି","ବିକ୍ରି"],"order":["ଅର୍ଡର"],"delivery":["ଡେଲିଭରି"],"bulk":["ହୋଲସେଲ୍"],"earn":["ଆୟ"],"help":["ସହାୟତା"],"language":["ଭାଷା"]},
    "as": {"price":["বজাৰ মূল্য","মূল্য","দাম"],"list":["উৎপাদন বিক্ৰী","বিক্ৰী"],"order":["অৰ্ডাৰ"],"delivery":["ডেলিভাৰী"],"bulk":["পাইকাৰী"],"earn":["উপাৰ্জন"],"help":["সহায়"],"language":["ভাষা"]},
    "brx":{"price":["बाजार दाम","दाम"],"list":["फसल फान","फाननो"],"order":["अर्डार"],"delivery":["डेलिभारि"],"bulk":["बल्क"],"earn":["आय"],"help":["मदद"],"language":["राव"]},
    "doi":{"price":["बाजार भाव","भाव"],"list":["पैदावार बेच","बेचने"],"order":["ऑर्डर"],"delivery":["डिलीवरी"],"bulk":["थोक"],"earn":["कमाई"],"help":["मदद"],"language":["भाषा"]},
    "ks":{"price":["بازار ریٹ","ریٹ"],"list":["پیداوار فروخت","فروخت"],"order":["آرڈر"],"delivery":["ڈلیوری"],"bulk":["تھوک"],"earn":["کمٲیی"],"help":["مدد"],"language":["زبان"]},
    "kok":{"price":["बाजार भाव","भाव"],"list":["उत्पादन विक","विकपाक"],"order":["ऑर्डर"],"delivery":["डिलिव्हरी"],"bulk":["घाऊक"],"earn":["कमाई"],"help":["मदत"],"language":["भास"]},
    "mai":{"price":["बाजार भाव","भाव"],"list":["उपज बेच","बेचबाक"],"order":["ऑर्डर"],"delivery":["डिलिवरी"],"bulk":["थोक"],"earn":["आमदनी"],"help":["मदद"],"language":["भाषा"]},
    "mni":{"price":["মার্কেট মমল","মমল"],"list":["পোৎ য়োন","য়োনবা"],"order":["অর্ডর"],"delivery":["ডেলিভরি"],"bulk":["বাল্ক"],"earn":["ইনকাম"],"help":["হেল্প"],"language":["লোন"]},
    "ne":{"price":["बजार मूल्य","मूल्य"],"list":["उत्पादन बेच","बेच्न"],"order":["अर्डर"],"delivery":["डेलिभरी"],"bulk":["थोक"],"earn":["आम्दानी"],"help":["सहायता"],"language":["भाषा"]},
    "sa":{"price":["विपणिमूल्य","मूल्य"],"list":["उत्पादनस्य विक्रय","विक्रय"],"order":["आदेश"],"delivery":["वितरण"],"bulk":["स्थूलादेश"],"earn":["आय"],"help":["सहाय"],"language":["भाषा"]},
    "sat":{"price":["ᱵᱟᱡᱟᱨ ᱫᱟᱢ","ᱫᱟᱢ"],"list":["ᱯᱷᱚᱥᱚᱞ ᱟᱠᱷᱨᱤᱧ","ᱟᱠᱷᱨᱤᱧ"],"order":["ᱚᱨᱰᱟᱨ"],"delivery":["ᱰᱮᱞᱤᱵᱷᱟᱨᱤ"],"bulk":["ᱵᱟᱞᱠ"],"earn":["ᱟᱭ"],"help":["ᱜᱚᱲᱚ"],"language":["ᱯᱟᱹᱨᱥᱤ"]},
    "sd":{"price":["بازار قيمت","قيمت"],"list":["فصل وڪڻ","وڪڻڻ"],"order":["آرڊر"],"delivery":["ڊليوري"],"bulk":["ٿوڪ"],"earn":["آمدني"],"help":["مدد"],"language":["ٻولي"]},
    "ur":{"price":["مارکیٹ قیمت","قیمت"],"list":["پیداوار فروخت","فروخت"],"order":["آرڈر"],"delivery":["ڈیلیوری"],"bulk":["تھوک"],"earn":["آمدنی"],"help":["مدد"],"language":["زبان"]},
}


@dataclass
class IntentResult:
    """Structured intent + extracted entities."""
    intent: str = UNKNOWN
    confidence: float = 0.0
    product: Optional[str] = None        # canonical crop name
    quantity: Optional[float] = None
    unit: Optional[str] = None
    price: Optional[float] = None
    grade: Optional[str] = None          # 'A', 'B', 'C'
    harvest_label: Optional[str] = None  # 'today' / 'yesterday' / ISO date
    harvest_offset: Optional[int] = None
    raw_text: str = ""
    dtmf: Optional[str] = None
    entities: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)


def _has_any(text: str, words: list[str]) -> bool:
    return any(w in text for w in words)


def recognize_intent(text: str, language: str = "ta", dtmf: Optional[str] = None,
                    context: Optional[str] = None) -> IntentResult:
    """Top-level intent + entity extraction.

    ``text`` may be Tamil / English / Tanglish. ``language`` is the active
    IVR language ('ta' or 'en'). ``dtmf`` is the keypad digit if any.
    ``context`` is the current IVR state name (e.g. 'list_ask_qty'); when
    in a multi-step listing flow the recognizer will give preference to
    entity extraction rather than top-level intents.
    """
    raw = (text or "").strip().lower()
    res = IntentResult(raw_text=raw, dtmf=dtmf)

    # ----- DTMF paths ------------------------------------------------------
    if dtmf is not None:
        d = str(dtmf).strip()
        res.dtmf = d
        # numeric answers inside listing flow
        if context in ("list_ask_qty", "list_ask_price", "order_place_ask_qty"):
            try:
                num = float(d) if "." in d else int(d)
                if context in ("list_ask_qty", "order_place_ask_qty"):
                    res.quantity, res.unit = float(num), "kg"
                    res.intent = PLACE_ORDER if context == "order_place_ask_qty" else RAW_NUMBER
                    res.confidence = 0.95
                    return res
                else:
                    res.price = float(num)
                    res.intent = RAW_NUMBER
                    res.confidence = 0.95
                    return res
            except ValueError:
                pass
        if context in ("list_ask_grade", "order_place_ask_grade"):
            g = parse_grade(d)
            if g:
                res.grade = g
                res.intent = PLACE_ORDER if context == "order_place_ask_grade" else RAW_NUMBER
                res.confidence = 0.95
                return res
        if context in ("list_confirm", "bulk_confirm", "price_hint_offer", "price_hint_recommend", "order_place_confirm"):
            if d == "1":
                res.intent = CONFIRM; res.confidence = 0.95; return res
            if d == "2":
                # In price_hint_offer, DTMF 2 means "skip the AI hint, keep my price"
                # In list_confirm, DTMF 2 means "change my entry"
                # In other confirm contexts, treat 2 as a soft "no" (CHANGE)
                res.intent = CHANGE; res.confidence = 0.95; return res
            if d == "3":
                res.intent = CANCEL; res.confidence = 0.95; return res

        # extra-services submenu DTMF mapping
        if context == "more_services":
            mapping = {
                "1": DEMAND_FORECAST,
                "2": MY_LISTINGS,
                "3": PAYMENT_STATUS,
                "4": PROFILE_SUMMARY,
                "5": AI_PRICE_RECOMMENDATION,
                "6": HELP,
                "8": LANGUAGE_CHANGE,
                "0": MAIN_MENU,
            }
            if d in mapping:
                res.intent = mapping[d]
                res.confidence = 0.99
                return res

        # main-menu top-level DTMF mapping
        if context in (None, "", "main_menu", "help"):
            mapping = {
                "1": PLACE_ORDER, "2": LIST_PRODUCE, "3": MARKET_PRICE,
                "4": ORDER_STATUS, "5": DELIVERY_STATUS, "6": BULK_ORDER,
                "7": EARNINGS, "8": LANGUAGE_CHANGE, "9": MORE_SERVICES,
                "*": HELP, "0": MAIN_MENU,
            }
            if d in mapping:
                res.intent = mapping[d]
                res.confidence = 0.99
                return res

    if not raw:
        res.intent = UNKNOWN
        return res

    # ----- extra-services voice shortcuts ---------------------------------
    if context == "more_services":
        if _has_any(raw, ["forecast", "demand forecast", "தேவை முன்னறிவிப்பு", "முன்னறிவிப்பு"]):
            res.intent = DEMAND_FORECAST; res.confidence = 0.9; return res
        if _has_any(raw, ["active listings", "my listings", "inventory", "stock", "என் பட்டியல்", "பட்டியல்கள்", "இருப்பு"]):
            res.intent = MY_LISTINGS; res.confidence = 0.9; return res
        if _has_any(raw, ["payment status", "settlement", "pending payment", "பணம் நிலை", "நிலுவை தொகை"]):
            res.intent = PAYMENT_STATUS; res.confidence = 0.9; return res
        if _has_any(raw, ["farm profile", "my profile", "profile", "பண்ணை சுயவிவரம்", "சுயவிவரம்"]):
            res.intent = PROFILE_SUMMARY; res.confidence = 0.9; return res
        if _has_any(raw, ["ai price", "price recommendation", "recommended price", "விலை பரிந்துரை", "AI விலை"]):
            res.intent = AI_PRICE_RECOMMENDATION; res.confidence = 0.9; return res
        if _has_any(raw, _TAMIL_PLACE_ORDER_WORDS + _EN_PLACE_ORDER_WORDS):
            res.intent = PLACE_ORDER; res.confidence = 0.94; return res

    # ----- IVR purchase flow ----------------------------------------------
    if context == "order_place_ask_crop":
        p = normalize_product(raw)
        if p:
            res.product = p
            res.intent = PLACE_ORDER
            res.confidence = 0.96
            return res
    if context == "order_place_ask_qty":
        q, u = parse_quantity(raw)
        if q:
            res.quantity, res.unit = q, u
            res.intent = PLACE_ORDER
            res.confidence = 0.96
            return res
    if context == "order_place_ask_grade":
        g = parse_grade(raw)
        if g:
            res.grade = g
            res.intent = PLACE_ORDER
            res.confidence = 0.96
            return res

    # ----- global control intents (work in any state) ---------------------
    if _has_any(raw, _TAMIL_REPEAT_WORDS + _EN_REPEAT_WORDS):
        res.intent = REPEAT; res.confidence = 0.85; return res
    if _has_any(raw, _TAMIL_BACK_WORDS + _EN_BACK_WORDS):
        res.intent = GO_BACK; res.confidence = 0.85; return res
    if _has_any(raw, _TAMIL_MAIN_MENU_WORDS + _EN_MAIN_MENU_WORDS):
        res.intent = MAIN_MENU; res.confidence = 0.9; return res
    if _has_any(raw, _TAMIL_CANCEL_WORDS + _EN_CANCEL_WORDS):
        # Don't hijack raw 'no' in confirm context unless explicitly cancel
        if context in ("list_confirm", "bulk_confirm"):
            res.intent = CANCEL
        else:
            res.intent = CANCEL
        res.confidence = 0.85; return res
    if _has_any(raw, _TAMIL_CHANGE_WORDS + _EN_CHANGE_WORDS):
        res.intent = CHANGE; res.confidence = 0.8; return res
    if _has_any(raw, _TAMIL_CONFIRM_WORDS + _EN_CONFIRM_WORDS):
        res.intent = CONFIRM; res.confidence = 0.85; return res

    if context in (None, "", "main_menu", "help") and _has_any(raw, _TAMIL_MORE_WORDS + _EN_MORE_WORDS):
        res.intent = MORE_SERVICES; res.confidence = 0.9; return res

    if context in (None, "", "main_menu", "help") and _has_any(raw, _TAMIL_PLACE_ORDER_WORDS + _EN_PLACE_ORDER_WORDS):
        res.intent = PLACE_ORDER; res.confidence = 0.94; return res

    # ----- selected-language top-level voice menu -------------------------
    # Keep context-specific transactional entity parsing unchanged.  At the
    # main menu, however, native keywords can select the same existing flows.
    if context in (None, "", "main_menu", "help") and language in _MULTI_MENU_WORDS:
        words = _MULTI_MENU_WORDS[language]
        mapping = (("help", HELP), ("language", LANGUAGE_CHANGE),
                   ("bulk", BULK_ORDER), ("delivery", DELIVERY_STATUS),
                   ("order", ORDER_STATUS), ("earn", EARNINGS),
                   ("price", MARKET_PRICE), ("list", LIST_PRODUCE))
        for group, intent_name in mapping:
            if _has_any(raw, words.get(group, [])):
                res.intent = intent_name
                res.confidence = 0.88
                return res

    # ----- multi-step listing flow: extract entities ----------------------
    if context in ("list_ask_crop", "list_ask_qty", "list_ask_price",
                   "list_ask_harvest", "list_ask_grade"):
        # Try to extract the relevant entity first
        if context == "list_ask_crop":
            p = normalize_product(raw)
            if p:
                res.product = p
                res.intent = LIST_PRODUCE
                res.confidence = 0.95
                return res
        if context == "list_ask_qty":
            q, u = parse_quantity(raw)
            if q:
                res.quantity, res.unit = q, u
                res.intent = LIST_PRODUCE
                res.confidence = 0.95
                return res
        if context == "list_ask_price":
            p = parse_price(raw)
            if p:
                res.price = p
                res.intent = LIST_PRODUCE
                res.confidence = 0.95
                return res
        if context == "list_ask_harvest":
            lbl, off = parse_harvest_offset(raw)
            if lbl:
                res.harvest_label, res.harvest_offset = lbl, off
                res.intent = LIST_PRODUCE
                res.confidence = 0.95
                return res
        if context == "list_ask_grade":
            g = parse_grade(raw)
            if g:
                res.grade = g
                res.intent = LIST_PRODUCE
                res.confidence = 0.95
                return res
        # fall through to top-level recognition (user may have switched topics)

    # ----- crop-prompt flows ------------------------------------------------
    if context in ("price_ask_crop", "forecast_ask_crop", "ai_price_ask_crop"):
        p = normalize_product(raw)
        if p:
            res.product = p
            if context == "forecast_ask_crop":
                res.intent = DEMAND_FORECAST
            elif context == "ai_price_ask_crop":
                res.intent = AI_PRICE_RECOMMENDATION
            else:
                res.intent = MARKET_PRICE
            res.confidence = 0.95
            return res

    # ----- top-level intent classification --------------------------------
    # We try product extraction first because most Tamil/English/Tanglish
    # intents include the produce name ('tomato price enna').
    product = normalize_product(raw)
    qty, unit = parse_quantity(raw)
    price = parse_price(raw)

    has_price_word = _has_any(raw, _TAMIL_PRICE_WORDS + _EN_PRICE_WORDS)
    has_list_word = _has_any(raw, _TAMIL_LIST_WORDS + _EN_LIST_WORDS)
    has_order_word = _has_any(raw, _TAMIL_ORDER_WORDS + _EN_ORDER_WORDS)
    has_delivery_word = _has_any(raw, _TAMIL_DELIVERY_WORDS + _EN_DELIVERY_WORDS)
    has_bulk_word = _has_any(raw, _TAMIL_BULK_WORDS + _EN_BULK_WORDS)
    has_earn_word = _has_any(raw, _TAMIL_EARN_WORDS + _EN_EARN_WORDS)
    has_help_word = _has_any(raw, _TAMIL_HELP_WORDS + _EN_HELP_WORDS)

    # Priority: explicit help first (so 'help' isn't misinterpreted as list)
    if has_help_word and not has_price_word and not has_list_word:
        res.intent = HELP; res.confidence = 0.85
        return res

    # bulk 'bulk order for tomato' / '500 kg tomato bulk order'
    if has_bulk_word:
        res.product = product
        res.intent = BULK_ORDER; res.confidence = 0.85
        return res

    # price intent — even if no product, intent still classified
    if has_price_word:
        res.product = product
        res.intent = MARKET_PRICE; res.confidence = 0.9
        return res

    # delivery status
    if has_delivery_word:
        res.intent = DELIVERY_STATUS; res.confidence = 0.9
        return res

    # order status
    if has_order_word:
        res.intent = ORDER_STATUS; res.confidence = 0.9
        return res

    # earnings
    if has_earn_word:
        res.intent = EARNINGS; res.confidence = 0.9
        return res

    # listing intent: "i have 100 kg tomato" or "என்னிடம் தக்காளி இருக்கு"
    if (has_list_word or product or qty) and not has_order_word and not has_delivery_word:
        res.product = product or res.product
        res.quantity, res.unit = (qty, unit) if qty else (res.quantity, res.unit)
        res.price = price if price else res.price
        # Only emit LIST_PRODUCE if we found a product or quantity
        if product or qty:
            res.intent = LIST_PRODUCE
            res.confidence = 0.85 if product else 0.6
            return res

    # fallback: if there is a recognised product but no clear verb, treat as MARKET_PRICE
    if product:
        res.product = product
        res.intent = MARKET_PRICE
        res.confidence = 0.55
        return res

    # fallback: if only a number was said, return RAW_NUMBER (caller's context decides)
    if qty:
        res.quantity, res.unit = qty, unit
        res.intent = RAW_NUMBER
        res.confidence = 0.5
        return res

    res.intent = UNKNOWN
    return res
