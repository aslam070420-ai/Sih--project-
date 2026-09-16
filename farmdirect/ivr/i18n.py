"""Bilingual IVR prompt strings (Tamil + English).

The Tamil terminology matches the FarmDirect application's existing vocabulary
(விளைபொருள் / சந்தை விலை / ஆர்டர் / டெலிவரி / வருமானம் / தரம்).
Every prompt has both a ``ta`` and an ``en`` form so the dialog manager can
serve either language on the same call without reloading.
"""
from typing import Dict

# --------------------------------------------------------------------- Welcome
WELCOME = {
    "ta": [
        "வணக்கம். உழவர் நேரடி சேவைக்கு வரவேற்கிறோம்.",
        "தமிழில் தொடர 1 அழுத்தவும்.",
        "English-க்கு 2 அழுத்தவும்.",
    ],
    "en": [
        "Welcome to Uzhavar Direct.",
        "Press 1 for Tamil.",
        "Press 2 for English.",
    ],
}

# --------------------------------------------------------------------- Main menu
MAIN_MENU = {
    "ta": [
        "வணக்கம். உழவர் நேரடி குரல் சேவைக்கு வரவேற்கிறோம்.",
        "விளைபொருள் வாங்கி புதிய ஆர்டர் செய்ய 1 அழுத்தவும்.",
        "விளைபொருளை விற்பனைக்கு பதிவு செய்ய 2 அழுத்தவும்.",
        "இன்றைய சந்தை விலையை அறிய 3 அழுத்தவும்.",
        "எனது ஆர்டர்களை அறிய 4 அழுத்தவும்.",
        "டெலிவரி நிலையை அறிய 5 அழுத்தவும்.",
        "மொத்த ஆர்டர் வாய்ப்புகளை அறிய 6 அழுத்தவும்.",
        "எனது வருமானத்தை அறிய 7 அழுத்தவும்.",
        "மொழியை மாற்ற 8 அழுத்தவும்.",
        "மேலும் சேவைகளுக்கு 9 அழுத்தவும்.",
        "உதவிக்கு ஸ்டார் விசையை அழுத்தவும்.",
    ],
    "en": [
        "Welcome to Uzhavar Direct voice service.",
        "To buy produce and place a new order, press 1.",
        "To list your produce for sale, press 2.",
        "To hear today's market price, press 3.",
        "To check your orders, press 4.",
        "To check delivery status, press 5.",
        "To check bulk order opportunities, press 6.",
        "To check your earnings, press 7.",
        "To change language, press 8.",
        "For more services, press 9.",
        "For help, press star.",
    ],
}

# --------------------------------------------------------------------- More services
MORE_SERVICES_MENU = {
    "ta": [
        "மேலும் சேவைகள்.",
        "AI தேவை முன்னறிவிப்புக்கு 1 அழுத்தவும்.",
        "எனது செயலில் உள்ள பட்டியல்களுக்கு 2 அழுத்தவும்.",
        "பணம் மற்றும் நிலுவை தொகை நிலைக்கு 3 அழுத்தவும்.",
        "எனது பண்ணை சுயவிவரத்திற்கு 4 அழுத்தவும்.",
        "AI விலை பரிந்துரைக்கு 5 அழுத்தவும்.",
        "உதவிக்கு 6 அழுத்தவும்.",
        "மொழியை மாற்ற 8 அழுத்தவும். முக்கிய மெனுவுக்கு 0 அழுத்தவும்.",
    ],
    "en": [
        "More services.",
        "For AI demand forecast, press 1.",
        "For my active listings, press 2.",
        "For payment and settlement status, press 3.",
        "For my farm profile, press 4.",
        "For AI price recommendation, press 5.",
        "For help, press 6.",
        "To change language, press 8. To return to the main menu, press 0.",
    ],
}

# --------------------------------------------------------------------- Help
HELP_TEXT = {
    "ta": [
        "இந்த சேவை உங்கள் விளைபொருளை நேரடியாக வாடிக்கையாளர்களுக்கு விற்க உதவுகிறது.",
        "நீங்கள் குரலில் அல்லது விசைகள் மூலம் பேசலாம்.",
        "உதாரணம்: என்னிடம் நூறு கிலோ தக்காளி இருக்கு.",
        "முக்கிய மெனுவுக்கு திரும்ப 0 அழுத்தவும்.",
    ],
    "en": [
        "This service lets you sell your produce directly to buyers.",
        "You can speak naturally or use the keypad.",
        "For example: I have one hundred kilos of tomatoes.",
        "Press 0 to return to the main menu.",
    ],
}

# --------------------------------------------------------------------- Errors
ERRORS = {
    "speech_unclear_1": {
        "ta": "மன்னிக்கவும். மீண்டும் சொல்லுங்கள்.",
        "en": "Sorry, I didn't catch that. Could you say it again?",
    },
    "speech_unclear_2": {
        "ta": "உங்கள் பதிலை எளிதாக சொல்லுங்கள்.",
        "en": "Please speak your answer a little more simply.",
    },
    "speech_unclear_3": {
        "ta": "குரல் மூலம் புரிந்து கொள்ள முடியவில்லை. தொலைபேசி விசைகளை பயன்படுத்தலாம்.",
        "en": "I still can't understand your voice. You can use the keypad instead.",
    },
    "invalid_choice": {
        "ta": "தவறான தேர்வு. மீண்டும் முயற்சிக்கவும்.",
        "en": "Invalid choice. Please try again.",
    },
    "no_account": {
        "ta": "இந்த தொலைபேசி எண்ணில் உழவர் நேரடி கணக்கு இல்லை. கணக்கு உருவாக்க உதவிக்கு 7 அழுத்தவும்.",
        "en": "There is no Uzhavar Direct account for this phone number. Press 7 for help creating an account.",
    },
    "no_orders": {
        "ta": "உங்களுக்கு தற்போது ஆர்டர்கள் இல்லை.",
        "en": "You have no orders at this time.",
    },
    "no_listings": {
        "ta": "உங்களுக்கு தற்போது விற்பனைக்கான விளைபொருள் இல்லை.",
        "en": "You have no produce listed for sale.",
    },
    "no_bulk": {
        "ta": "உங்கள் பகுதியில் தற்போது மொத்த ஆர்டர் வாய்ப்புகள் இல்லை.",
        "en": "There are no bulk order opportunities in your area right now.",
    },
    "product_unknown": {
        "ta": "நீங்கள் கூறிய விளைபொருள் புரியவில்லை. மீண்டும் சொல்லுங்கள்.",
        "en": "I didn't recognise that produce. Please say it again.",
    },
    "quantity_missing": {
        "ta": "எவ்வளவு அளவு என்பதை கூறுங்கள். உதாரணம்: நூறு கிலோ.",
        "en": "Please tell me the quantity, for example: one hundred kilos.",
    },
    "price_missing": {
        "ta": "ஒரு கிலோவுக்கு எவ்வளவு விலை என்பதை கூறுங்கள். உதாரணம்: முப்பத்து எட்டு ரூபாய்.",
        "en": "Please tell me the price per kilo, for example: thirty eight rupees.",
    },
    "db_unavailable": {
        "ta": "இப்போது சேவை இயங்கவில்லை. சிறிது நேரம் கழித்து மீண்டும் அழைக்கவும்.",
        "en": "The service is temporarily unavailable. Please call back shortly.",
    },
}

# --------------------------------------------------------------------- Prompts
PROMPTS: Dict[str, Dict[str, str]] = {
    # Listing flow
    "list_ask_crop": {
        "ta": "எந்த விளைபொருளை விற்க விரும்புகிறீர்கள்? உதாரணம்: தக்காளி, வெங்காயம், உருளைக்கிழங்கு.",
        "en": "What produce would you like to sell? For example: tomato, onion, potato.",
    },
    "list_ask_qty": {
        "ta": "எவ்வளவு அளவு இருக்கிறது? உதாரணம்: நூறு கிலோ.",
        "en": "How much do you have? For example: one hundred kilos.",
    },
    "list_ask_price": {
        "ta": "ஒரு கிலோவுக்கு எவ்வளவு விலை எதிர்பார்க்கிறீர்கள்?",
        "en": "What price do you expect per kilo?",
    },
    "list_ask_harvest": {
        "ta": "இந்த விளைபொருள் எப்போது அறுவடை செய்யப்பட்டது? இன்று, நேற்று அல்லது தேதி சொல்லுங்கள்.",
        "en": "When was this harvested? Today, yesterday, or a date.",
    },
    "list_ask_grade": {
        "ta": "தரத்தை தேர்வு செய்யுங்கள். A தரத்திற்கு 1, B தரத்திற்கு 2, C தரத்திற்கு 3 அழுத்தவும்.",
        "en": "Select the quality grade. Press 1 for A, 2 for B, 3 for C.",
    },
    "list_summary": {
        "ta": "நீங்கள் {qty} கிலோ {crop} ஒரு கிலோ {price} ரூபாய் விலையில், {grade} தரத்தில், {harvest_label} அறுவடை செய்ததாக பதிவு செய்துள்ளீர்கள்.",
        "en": "You are listing {qty} kg of {crop} at {price} rupees per kg, {grade} grade, harvested {harvest_label}.",
    },
    "list_confirm_options": {
        "ta": "பதிவு செய்ய 1 அழுத்தவும். மாற்ற 2 அழுத்தவும். ரத்து செய்ய 3 அழுத்தவும்.",
        "en": "Press 1 to confirm. Press 2 to change. Press 3 to cancel.",
    },
    "list_success": {
        "ta": "உங்கள் விளைபொருள் வெற்றிகரமாக பதிவு செய்யப்பட்டது.",
        "en": "Your produce has been listed successfully.",
    },
    "list_cancelled": {
        "ta": "பதிவு ரத்து செய்யப்பட்டது.",
        "en": "Listing cancelled.",
    },
    # AI price hint
    "price_hint_offer": {
        "ta": "நீங்கள் பதிவு செய்த விலை கிலோவுக்கு {price} ரூபாய். தற்போதைய சந்தை விலை சுமார் {low} முதல் {high} ரூபாய். AI பரிந்துரையை கேட்க 1 அழுத்தவும்.",
        "en": "You entered {price} rupees per kg. The current market range is about {low} to {high} rupees. Press 1 to hear the AI recommendation.",
    },
    "price_hint_recommend": {
        "ta": "AI பரிந்துரை: கிலோவுக்கு {suggested} ரூபாய். உங்கள் விலையை இதற்கு மாற்ற 1 அழுத்தவும், அல்லது உங்கள் விலையை வைத்துக்கொள்ள 2 அழுத்தவும்.",
        "en": "AI recommends {suggested} rupees per kg. Press 1 to use this price, or 2 to keep your price.",
    },
    "price_hint_skipped": {
        "ta": "சரி, உங்கள் விலையே பதிவு செய்யப்படும்.",
        "en": "OK, your price will be used.",
    },
    "price_updated": {
        "ta": "சரி. உங்கள் விலை கிலோவுக்கு {price} ரூபாயாக புதுப்பிக்கப்பட்டது.",
        "en": "OK. Your price has been updated to {price} rupees per kg.",
    },
    # Market price
    "price_ask_crop": {
        "ta": "எந்த விளைபொருளின் விலையை அறிய விரும்புகிறீர்கள்?",
        "en": "Which produce price would you like to hear?",
    },
    "price_report": {
        "ta": "இன்று {crop} சந்தை விலை கிலோவுக்கு {low} முதல் {high} ரூபாய் வரை உள்ளது. சராசரி விலை {avg} ரூபாய். இந்த தகவல் {updated} அன்று புதுப்பிக்கப்பட்டது.",
        "en": "Today {crop} market price is between {low} and {high} rupees per kg. Average price is {avg} rupees. This information was updated on {updated}.",
    },
    "price_unavailable": {
        "ta": "தற்போது {crop} விலை தகவல் கிடைக்கவில்லை.",
        "en": "Market price for {crop} is not available right now.",
    },
    "demo_note": {
        "ta": "குறிப்பு: இந்த சந்தை விலை முன்னோட்ட தரவின் அடிப்படையில் உள்ளது.",
        "en": "Note: this market price is based on demo data.",
    },
    "official_market_note": {
        "ta": "இந்த விலை இந்திய அரசின் AGMARKNET சந்தை தரவிலிருந்து பெறப்பட்டது. சந்தை: {market}. மாநிலம்: {state}.",
        "en": "This is official AGMARKNET mandi data from the Government of India. Market: {market}. State: {state}.",
    },
    "cached_market_note": {
        "ta": "இது கடைசியாக வெற்றிகரமாக ஒத்திசைக்கப்பட்ட அதிகாரப்பூர்வ AGMARKNET விலை தரவு.",
        "en": "This is the last successfully synced official AGMARKNET price data.",
    },
    # Orders
    "order_latest": {
        "ta": "உங்கள் சமீபத்திய ஆர்டர் எண் {code}. தற்போதைய நிலை: {status}.",
        "en": "Your latest order is {code}. Current status: {status}.",
    },
    "order_more": {
        "ta": "மற்ற ஆர்டர்களை கேட்க 1 அழுத்தவும்.",
        "en": "Press 1 to hear other orders.",
    },
    # Delivery
    "delivery_report": {
        "ta": "ஆர்டர் {code} டெலிவரி நிலை: {status}. {extra}",
        "en": "Order {code} delivery status: {status}. {extra}",
    },
    # Bulk
    "bulk_report": {
        "ta": "உங்கள் பகுதியில் {qty} கிலோ {crop}க்கு ஒரு மொத்த ஆர்டர் உள்ளது. உங்கள் தற்போதைய இருப்பில் இருந்து {avail} கிலோ வரை வழங்கலாம். இந்த வாய்ப்பை ஏற்க 1 அழுத்தவும். வேண்டாம் என்றால் 2 அழுத்தவும்.",
        "en": "There is a bulk order in your area for {qty} kg of {crop}. You can supply up to {avail} kg from your current listings. Press 1 to accept. Press 2 to decline.",
    },
    "bulk_accept_ok": {
        "ta": "மொத்த ஆர்டர் ஏற்கப்பட்டது. விற்பனையாளர் சிறிது நேரத்தில் உங்களை தொடர்பு கொள்வார்.",
        "en": "Bulk order accepted. The buyer will contact you shortly.",
    },
    "bulk_declined": {
        "ta": "சரி, இந்த வாய்ப்பு தவிர்க்கப்பட்டது.",
        "en": "OK, this opportunity has been skipped.",
    },
    # Earnings
    "earnings_report": {
        "ta": "இன்று வருமானம் {today} ரூபாய். இந்த வாரம் {week} ரூபாய். இந்த மாதம் {month} ரூபாய். பெறப்பட்டது {paid} ரூபாய். நிலுவையில் {pending} ரூபாய்.",
        "en": "Today's earnings: {today} rupees. This week: {week} rupees. This month: {month} rupees. Paid: {paid} rupees. Pending: {pending} rupees.",
    },
    # More services
    "more_services_invalid": {
        "ta": "மேலும் சேவைகளில் 1 முதல் 6 வரை தேர்வு செய்யுங்கள். 0 முக்கிய மெனு, 8 மொழி மாற்றம்.",
        "en": "Choose an option from 1 to 6. Press 0 for main menu or 8 to change language.",
    },
    "forecast_ask_crop": {
        "ta": "எந்த விளைபொருளுக்கான AI தேவை முன்னறிவிப்பை அறிய விரும்புகிறீர்கள்?",
        "en": "Which crop would you like an AI demand forecast for?",
    },
    "forecast_report": {
        "ta": "அடுத்த {days} நாட்களுக்கு {crop} கணிக்கப்பட்ட தேவை {predicted} கிலோ. தற்போதைய வார தேவை {current} கிலோ. போக்கு {trend}. நம்பிக்கை {confidence} சதவீதம்.",
        "en": "For the next {days} days, predicted demand for {crop} is {predicted} kilograms. Current weekly demand is {current} kilograms. Trend is {trend}. Confidence is {confidence} percent.",
    },
    "listings_report": {
        "ta": "உங்களிடம் {count} செயலில் உள்ள பட்டியல்கள் உள்ளன. மொத்த கிடைக்கும் அளவு {qty} கிலோ. சமீபத்திய பட்டியல் {crop}, {grade} தரம், கிலோவுக்கு {price} ரூபாய்.",
        "en": "You have {count} active listings with {qty} kilograms available in total. Your latest listing is {crop}, grade {grade}, at {price} rupees per kilogram.",
    },
    "listings_empty": {
        "ta": "தற்போது செயலில் உள்ள பட்டியல்கள் இல்லை.",
        "en": "You do not have any active listings right now.",
    },
    "payment_report": {
        "ta": "பெறப்பட்ட தொகை {paid} ரூபாய். நிலுவையில் உள்ள தொகை {pending} ரூபாய். இந்த மாத வருமானம் {month} ரூபாய்.",
        "en": "Completed payments are {paid} rupees. Pending settlements are {pending} rupees. This month's earnings are {month} rupees.",
    },
    "profile_report": {
        "ta": "பண்ணை சுயவிவரம். பெயர் {name}. நகரம் {city}. பண்ணை {farm}. வளர்க்கப்படும் பயிர்கள் {crops}. பண்ணை பரப்பு {size} ஏக்கர்.",
        "en": "Farm profile. Name {name}. City {city}. Farm {farm}. Crops grown: {crops}. Farm size: {size} acres.",
    },
    "ai_price_ask_crop": {
        "ta": "எந்த விளைபொருளுக்கு AI விலை பரிந்துரை வேண்டும்?",
        "en": "Which crop would you like an AI price recommendation for?",
    },
    "ai_price_report": {
        "ta": "{crop} A தரம், 100 கிலோக்கு AI பரிந்துரை கிலோவுக்கு {suggested} ரூபாய். தற்போதைய மண்டி அடிப்படை {mandi} ரூபாய். கணிக்கப்பட்ட விவசாயி வருமான உயர்வு {gain} சதவீதம்.",
        "en": "For 100 kilograms of grade A {crop}, the AI recommends {suggested} rupees per kilogram. Current mandi baseline is {mandi} rupees. Estimated farmer earnings improvement is {gain} percent.",
    },
    # Buy / place order through IVR
    "order_place_ask_crop": {
        "ta": "எந்த விளைபொருளை வாங்கி ஆர்டர் செய்ய விரும்புகிறீர்கள்?",
        "en": "Which produce would you like to buy?",
    },
    "order_place_ask_qty": {
        "ta": "எத்தனை கிலோ வாங்க விரும்புகிறீர்கள்?",
        "en": "How many kilograms would you like to order?",
    },
    "order_place_ask_grade": {
        "ta": "தரம் Aக்கு 1, தரம் Bக்கு 2, தரம் Cக்கு 3 அழுத்தவும்.",
        "en": "Choose quality grade. Press 1 for A, 2 for B, or 3 for C.",
    },
    "order_place_quote": {
        "ta": "{qty} கிலோ {crop}, தரம் {grade}. கிலோவுக்கு {price} ரூபாய். விற்பனையாளர் {seller}. கட்டணங்கள் உட்பட மொத்தம் {total} ரூபாய். ஆர்டர் செய்ய 1 அழுத்தவும். ரத்து செய்ய 2 அழுத்தவும்.",
        "en": "{qty} kilograms of {crop}, grade {grade}, at {price} rupees per kilogram from {seller}. Estimated total including fees is {total} rupees. Press 1 to place the order or 2 to cancel.",
    },
    "order_place_stock_short": {
        "ta": "அந்த அளவுக்கு போதுமான இருப்பு இல்லை. அதிகபட்சம் {available} கிலோ கிடைக்கிறது. வேறு அளவை சொல்லுங்கள்.",
        "en": "There is not enough stock in one listing for that quantity. Up to {available} kilograms is available. Please say a different quantity.",
    },
    "order_place_success": {
        "ta": "ஆர்டர் வெற்றிகரமாக பதிவு செய்யப்பட்டது. ஆர்டர் எண் {code}. மொத்தம் {total} ரூபாய். பணம் டெலிவரியின் போது செலுத்தலாம்.",
        "en": "Your order has been placed successfully. Order number {code}. Total {total} rupees. Payment is Cash on Delivery.",
    },
    "order_place_cancelled": {
        "ta": "சரி. புதிய ஆர்டர் ரத்து செய்யப்பட்டது.",
        "en": "OK. The new order was cancelled.",
    },
    # Misc
    "returning_to_main": {
        "ta": "முக்கிய மெனுவுக்கு திரும்புகிறோம்.",
        "en": "Returning to the main menu.",
    },
    "goodbye": {
        "ta": "நன்றி. உழவர் நேரடி சேவையை பயன்படுத்தியதற்கு நன்றி. வணக்கம்.",
        "en": "Thank you for using Uzhavar Direct. Goodbye.",
    },
    "acknowledged": {
        "ta": "சரி.",
        "en": "OK.",
    },
}


# --------------------------------------------------------------------- India language expansion
# The original Tamil/English copy above remains untouched.  Additional
# Scheduled Indian languages receive native call-navigation prompts.  Deep
# transactional prompts intentionally fall back to the exact existing English
# text unless a translated string is available, which keeps the original
# business meaning and avoids changing any flow semantics.
from .languages import LANGUAGES, CORE_LANGUAGE_PACKS

# V8: order/purchase is intentionally the first main-menu action in every
# supported language.  Native packs predate the purchase flow, so we preserve
# their translated semantic lines, renumber them safely, and insert one
# localized purchase prompt at position 1.
_ORDER_FIRST_PROMPT = {
    "hi": "उत्पाद खरीदने और नया ऑर्डर देने के लिए 1 दबाएँ।",
    "te": "ఉత్పత్తులు కొనుగోలు చేసి కొత్త ఆర్డర్ పెట్టడానికి 1 నొక్కండి.",
    "kn": "ಉತ್ಪನ್ನ ಖರೀದಿಸಿ ಹೊಸ ಆರ್ಡರ್ ಮಾಡಲು 1 ಒತ್ತಿ.",
    "ml": "ഉൽപ്പന്നം വാങ്ങി പുതിയ ഓർഡർ നൽകാൻ 1 അമർത്തുക.",
    "mr": "उत्पादन खरेदी करून नवीन ऑर्डर देण्यासाठी 1 दाबा.",
    "bn": "পণ্য কিনে নতুন অর্ডার দিতে 1 চাপুন।",
    "gu": "ઉત્પાદન ખરીદી નવો ઓર્ડર આપવા 1 દબાવો.",
    "pa": "ਫਸਲ ਖਰੀਦ ਕੇ ਨਵਾਂ ਆਰਡਰ ਕਰਨ ਲਈ 1 ਦਬਾਓ।",
    "or": "ଉତ୍ପାଦ କିଣି ନୂଆ ଅର୍ଡର କରିବାକୁ 1 ଦବାନ୍ତୁ।",
    "as": "উৎপাদন কিনি নতুন অৰ্ডাৰ দিবলৈ 1 টিপক।",
    "doi": "पैदावार खरीदने ते नमां ऑर्डर देने आस्तै 1 दबाओ।",
    "ks": "پیداوار خرید کرنہٕ تہٕ نَو آرڈر دِنہٕ خٲطرٕ 1 دبٲیِو۔",
    "kok": "उत्पादन विकत घेवन नवो ऑर्डर करपाक 1 दामात।",
    "mai": "उपज किनबाक आ नव ऑर्डर देबाक लेल 1 दबाउ।",
    "ne": "उत्पादन किन्न र नयाँ अर्डर गर्न 1 थिच्नुहोस्।",
    "sa": "उत्पादनं क्रेतुं नूतनादेशं दातुं 1 नुदतु।",
    "sd": "فصل خريد ڪري نئون آرڊر ڏيڻ لاءِ 1 دٻايو۔",
    "ur": "پیداوار خریدنے اور نیا آرڈر دینے کے لیے 1 دبائیں۔",
}

def _renumber_first_digit(text: str, old: str, new: str) -> str:
    import re as _re
    return _re.sub(rf"(?<!\d){_re.escape(old)}(?!\d)", new, text, count=1)

def _order_first_native_menu(code: str, pack: dict) -> list[str]:
    base = list(pack.get("main") or [])
    if len(base) < 9:
        return list(MAIN_MENU["en"])
    title, list_p, market_p, orders_p, delivery_p, bulk_p, earnings_p, _help_p, language_p = base[:9]
    order_p = _ORDER_FIRST_PROMPT.get(code, "To buy produce and place a new order, press 1.")
    return [
        title,
        order_p,
        _renumber_first_digit(list_p, "1", "2"),
        _renumber_first_digit(market_p, "2", "3"),
        _renumber_first_digit(orders_p, "3", "4"),
        _renumber_first_digit(delivery_p, "4", "5"),
        _renumber_first_digit(bulk_p, "5", "6"),
        _renumber_first_digit(earnings_p, "6", "7"),
        language_p,
        "For more services, press 9.",
        "For help, press star.",
    ]

for _code in LANGUAGES:
    if _code in ("ta", "en"):
        continue
    _pack = CORE_LANGUAGE_PACKS.get(_code, {})
    WELCOME[_code] = list(_pack.get("welcome") or WELCOME["en"])
    MAIN_MENU[_code] = _order_first_native_menu(_code, _pack)
    HELP_TEXT[_code] = list(_pack.get("help") or HELP_TEXT["en"])
    MORE_SERVICES_MENU[_code] = list(MORE_SERVICES_MENU["en"])

# Make every existing error/prompt safe for every supported language while
# preserving its exact original English wording as fallback.
for _entry in ERRORS.values():
    for _code in LANGUAGES:
        _entry.setdefault(_code, _entry.get("en") or _entry.get("ta") or "")
for _entry in PROMPTS.values():
    for _code in LANGUAGES:
        _entry.setdefault(_code, _entry.get("en") or _entry.get("ta") or "")


def pick_prompt(key: str, lang: str, **fmt) -> str:
    """Return the prompt for ``key`` in ``lang``, formatted with ``**fmt``."""
    entry = PROMPTS.get(key) or ERRORS.get(key) or {}
    txt = entry.get(lang) or entry.get("en") or entry.get("ta") or ""
    try:
        return txt.format(**fmt) if fmt else txt
    except (KeyError, IndexError):
        return txt
