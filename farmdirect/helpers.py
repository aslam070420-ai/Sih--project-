"""Shared helpers: formatting, crop metadata, status pipelines."""
from datetime import datetime, timedelta
from html import escape

from markupsafe import Markup

# India-wide crop metadata (icon + gradient + category).
# Kept in a standalone catalogue so marketplace, seeder and IVR share one source of truth.
from india_catalog import CROP_BY_NAME, crop_meta

CROP_META = crop_meta()

ORDER_STEPS = ["pending", "confirmed", "picked_up", "in_transit", "delivered"]



def _slug(value):
    return "".join(ch.lower() if ch.isalnum() else "-" for ch in str(value)).strip("-")


def _crop_family(crop, category=""):
    name = (crop or "").lower()
    category = (category or "").lower()
    groups = {
        "tomato": {"tomato"},
        "onion": {"onion", "spring onion", "leek"},
        "potato": {"potato", "sweet potato"},
        "eggplant": {"brinjal"},
        "okra": {"okra", "drumstick"},
        "leaf": {"cabbage", "spinach", "lettuce", "celery", "coriander leaves", "mint leaves", "curry leaves", "fenugreek leaves", "amaranth greens", "knol khol", "tulsi", "aloe vera", "lemongrass", "stevia", "ashwagandha", "isabgol", "kalmegh", "safed musli", "shatavari", "brahmi", "senna", "vetiver", "giloy", "patchouli"},
        "floret": {"cauliflower", "broccoli"},
        "root": {"carrot", "radish", "beetroot", "turnip"},
        "pod": {"green peas", "french bean", "cluster bean", "cowpea vegetable", "broad bean", "cowpea", "lablab bean", "field pea", "green gram", "black gram", "kidney bean", "moth bean", "horse gram", "chickpea", "pigeon pea", "lentil", "soybean"},
        "pepper": {"capsicum"},
        "chili": {"green chili", "dry chili"},
        "cucumber": {"cucumber", "gherkin", "bottle gourd", "bitter gourd", "ridge gourd", "sponge gourd", "snake gourd", "pointed gourd", "ivy gourd", "summer squash", "zucchini"},
        "pumpkin": {"ash gourd", "pumpkin"},
        "corn": {"sweet corn", "baby corn", "maize", "fodder maize"},
        "mushroom": {"mushroom"},
        "tuber": {"yam", "elephant foot yam", "colocasia", "tapioca"},
        "mango": {"mango"},
        "banana": {"banana"},
        "apple": {"apple", "custard apple"},
        "grapes": {"grapes"},
        "citrus": {"orange", "mandarin", "sweet lime", "lemon", "lime"},
        "guava": {"guava", "pear", "sapota"},
        "melon": {"papaya", "watermelon", "muskmelon", "jackfruit", "bael", "wood apple"},
        "pineapple": {"pineapple"},
        "pomegranate": {"pomegranate"},
        "berry": {"litchi", "ber", "jamun", "fig", "strawberry", "mulberry", "karonda", "phalsa", "cherry", "plum", "passion fruit", "rambutan", "mangosteen"},
        "dragonfruit": {"dragon fruit", "kiwi", "avocado", "apricot", "peach"},
        "date": {"date fruit", "amla"},
        "rice": {"rice", "basmati rice", "sona masoori rice", "red rice", "black rice"},
        "wheat": {"wheat", "durum wheat"},
        "barley": {"barley", "oats", "fodder oats"},
        "millet": {"sorghum", "buckwheat", "pearl millet", "finger millet", "foxtail millet", "little millet", "kodo millet", "barnyard millet", "proso millet", "browntop millet", "fodder sorghum"},
        "oilseed": {"groundnut", "mustard", "rapeseed", "sesame", "sunflower seed", "safflower", "linseed", "niger seed", "castor seed"},
        "turmeric": {"turmeric"},
        "pepper-spice": {"black pepper", "small cardamom", "large cardamom", "clove", "cinnamon", "cassia", "nutmeg", "mace", "star anise", "saffron", "bay leaf", "vanilla", "kokum"},
        "ginger": {"ginger"},
        "garlic": {"garlic"},
        "seed-spice": {"coriander seed", "cumin", "fennel", "fenugreek seed", "ajwain", "dill seed", "tamarind"},
        "tea": {"tea"},
        "coffee": {"coffee arabica", "coffee robusta"},
        "cocoa": {"cocoa"},
        "tree-crop": {"rubber", "arecanut", "coconut", "cashew", "jute"},
        "sugarcane": {"sugarcane"},
        "cotton": {"cotton"},
        "nut": {"walnut", "almond", "pistachio", "chironji", "pine nut"},
        "flower": {"marigold", "rose", "jasmine", "tuberose", "chrysanthemum", "gladiolus", "gerbera", "carnation", "orchid", "anthurium", "lily", "lotus", "aster", "gaillardia", "crossandra", "hibiscus", "dahlia"},
        "grass": {"berseem", "lucerne", "napier grass", "fodder cowpea"},
    }
    for family, names in groups.items():
        if name in names:
            return family
    if "flower" in category:
        return "flower"
    if "fruit" in category:
        return "apple"
    if "grain" in category:
        return "wheat"
    if "millet" in category:
        return "millet"
    if "pulse" in category or "legume" in category:
        return "pod"
    if "oil" in category:
        return "oilseed"
    if "spice" in category:
        return "seed-spice"
    if "plantation" in category:
        return "tree-crop"
    if "herb" in category:
        return "leaf"
    if "fodder" in category:
        return "grass"
    return "leaf"


def _crop_palette(crop, category=""):
    name = (crop or "").lower()
    base = {
        "tomato": ("#ff927f", "#eb4f47", "#226c42", "#fff2cf"),
        "onion": ("#f7d8aa", "#d89b5a", "#5f8c46", "#fff6dd"),
        "potato": ("#e2bf8b", "#b68049", "#4d7f3d", "#fff2d7"),
        "eggplant": ("#b487ff", "#6f3db3", "#4ca24f", "#f9ecff"),
        "okra": ("#b9ef76", "#6bb34d", "#478b3d", "#f7ffd9"),
        "leaf": ("#bff0a5", "#4ec46d", "#2d8d58", "#edfff2"),
        "floret": ("#d8f8bf", "#6fd76f", "#3d9452", "#f5ffef"),
        "root": ("#ffa86d", "#f4693f", "#4e8f46", "#fff0d7"),
        "pod": ("#c8f47e", "#72c95d", "#4d964a", "#f7ffe5"),
        "pepper": ("#ffcf6e", "#ff8a3d", "#4a9c4b", "#fff8d8"),
        "chili": ("#ff9077", "#ed4b3a", "#3f8f42", "#fff0dd"),
        "cucumber": ("#baf2a1", "#6fca67", "#3a8c50", "#ebffec"),
        "pumpkin": ("#ffd39a", "#f08f41", "#4f944a", "#fff3db"),
        "corn": ("#ffe98a", "#f5b93d", "#4f9a46", "#fff8df"),
        "mushroom": ("#ead5c3", "#c79a76", "#9c6d4b", "#fff7ee"),
        "tuber": ("#f0cb8c", "#b57c4a", "#588a49", "#fff2dd"),
        "mango": ("#ffe27b", "#ff9f39", "#3ea74f", "#fff6d8"),
        "banana": ("#fff18c", "#ffd642", "#5ca247", "#fffce0"),
        "apple": ("#ffb1a6", "#ef5450", "#4aa05b", "#fff1ec"),
        "grapes": ("#ccb5ff", "#8454d8", "#57a16c", "#f4efff"),
        "citrus": ("#ffd883", "#ff9f39", "#56a84d", "#fff7dd"),
        "guava": ("#c9f19e", "#7fcd68", "#5ea850", "#f6ffea"),
        "melon": ("#ffa9ac", "#fa6f78", "#68b750", "#fff3e4"),
        "pineapple": ("#ffe97f", "#efb43d", "#4aa65e", "#fff8dc"),
        "pomegranate": ("#ffb3be", "#db4157", "#6dbf59", "#fff0f2"),
        "berry": ("#d1b5ff", "#874de6", "#5a9e55", "#f6f0ff"),
        "dragonfruit": ("#ffb2e0", "#e84a91", "#76c566", "#fff0f8"),
        "date": ("#dec09a", "#a56d42", "#6aa65c", "#fff3e0"),
        "rice": ("#f5e7a7", "#d7b65a", "#87b85d", "#fff8dd"),
        "wheat": ("#f5dea3", "#d09d4b", "#72a85a", "#fff5dc"),
        "barley": ("#efd8a1", "#b98b43", "#7bb660", "#fff7e1"),
        "millet": ("#eed39d", "#bc8944", "#77ac57", "#fff4dd"),
        "oilseed": ("#ffe988", "#ebb73b", "#67a84f", "#fff9df"),
        "turmeric": ("#ffe064", "#f0a91f", "#598d43", "#fff7cd"),
        "pepper-spice": ("#ead9c2", "#6e503f", "#7eb564", "#fbf4ee"),
        "ginger": ("#f2cc9a", "#c78554", "#72a55a", "#fff4e5"),
        "garlic": ("#fff0e4", "#dcbca0", "#6ba55f", "#fffdf9"),
        "seed-spice": ("#d6efc2", "#74b054", "#4f8e43", "#f5ffeb"),
        "tea": ("#b7f0b1", "#4ab26a", "#2b7e53", "#efffee"),
        "coffee": ("#e6c6a7", "#8a5a3a", "#4a8e55", "#fff0e5"),
        "cocoa": ("#dfbc99", "#965d3c", "#63a063", "#fff1e5"),
        "tree-crop": ("#caefa5", "#62ae58", "#2f7b4f", "#f2ffe7"),
        "sugarcane": ("#c2f0b8", "#72ca79", "#4a915f", "#efffee"),
        "cotton": ("#ffffff", "#d5e3dc", "#70a360", "#f8ffff"),
        "nut": ("#e7c39d", "#9b6a47", "#70a85a", "#fff3e5"),
        "flower": ("#ffc8e6", "#df64b2", "#7dc95f", "#fff2fa"),
        "grass": ("#c9f2a6", "#7ec962", "#458f4f", "#f1ffea"),
    }
    family = _crop_family(crop, category)
    return base.get(family, base["leaf"]), family


def _crop_svg(family, crop, colors):
    p1, p2, leaf, glow = colors
    # Generic stage/background shared by all marks.
    stage = f'<defs><linearGradient id="fdg" x1="0" y1="0" x2="1" y2="1"><stop offset="0%" stop-color="{glow}"/><stop offset="100%" stop-color="{p1}"/></linearGradient><linearGradient id="fdh" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stop-color="{p1}"/><stop offset="100%" stop-color="{p2}"/></linearGradient></defs><rect x="8" y="8" width="84" height="84" rx="28" fill="url(#fdg)"/><circle cx="77" cy="24" r="11" fill="rgba(255,255,255,.35)"/>'
    svg = {
        'tomato': f'<g class="fd-crop-body"><circle cx="50" cy="53" r="22" fill="url(#fdh)"/><path d="M39 36c5 6 17 5 22 0 2 5 8 7 12 8-5 2-7 7-6 12-6-3-12-3-17 0 1-5-2-10-7-12 4-2 8-4 10-8Z" fill="{leaf}"/></g>',
        'onion': f'<g class="fd-crop-body"><path d="M50 29c13 10 20 20 20 31 0 12-9 21-20 21s-20-9-20-21c0-11 7-21 20-31Z" fill="url(#fdh)"/><path d="M49 20c-6 8-4 12 0 17 5-5 7-10 2-17Z" fill="{leaf}"/></g>',
        'potato': f'<g class="fd-crop-body"><path d="M32 43c3-8 29-14 36 0 8 4 8 24-3 30-7 8-29 6-35-7-5-8-2-17 2-23Z" fill="url(#fdh)"/><circle cx="43" cy="54" r="2" fill="#9f6f40"/><circle cx="58" cy="47" r="2" fill="#9f6f40"/><circle cx="54" cy="62" r="2" fill="#9f6f40"/></g>',
        'eggplant': f'<g class="fd-crop-body"><path d="M39 39c-8 7-10 25 7 34 18 8 33-14 23-30-7-9-23-11-30-4Z" fill="url(#fdh)"/><path d="M40 35c6-8 18-9 22-1-5 0-8 2-10 6-4-2-7-3-12-5Z" fill="{leaf}"/></g>',
        'okra': f'<g class="fd-crop-body"><path d="M43 30c7 4 15 25 15 40 0 7-17 7-16 0-1-15 3-32 1-40Z" fill="url(#fdh)"/><path d="M43 30 50 23 57 30" fill="none" stroke="{leaf}" stroke-width="5" stroke-linecap="round" stroke-linejoin="round"/></g>',
        'leaf': f'<g class="fd-crop-body"><path d="M28 61c0-19 15-35 41-35-2 28-14 45-33 45-5 0-8-4-8-10Z" fill="url(#fdh)"/><path d="M39 68c9-9 15-18 22-34" stroke="{leaf}" stroke-width="3.5" stroke-linecap="round"/></g>',
        'floret': f'<g class="fd-crop-body"><circle cx="40" cy="48" r="10" fill="{p1}"/><circle cx="52" cy="43" r="12" fill="{p1}"/><circle cx="63" cy="49" r="10" fill="{p1}"/><path d="M50 53v18" stroke="{leaf}" stroke-width="6" stroke-linecap="round"/></g>',
        'root': f'<g class="fd-crop-body"><path d="M48 30c9 4 13 17 8 28-6 12-16 18-23 13-7-5-6-18 3-29 3-4 6-8 12-12Z" fill="url(#fdh)"/><path d="M50 28c7-7 12-8 18-7-3 6-6 10-13 12" fill="{leaf}"/><path d="M41 61l-4 11M53 63l2 10" stroke="#cf7d45" stroke-width="3" stroke-linecap="round"/></g>',
        'pod': f'<g class="fd-crop-body"><path d="M28 55c8-17 22-24 41-18-8 18-23 27-41 18Z" fill="url(#fdh)"/><circle cx="45" cy="48" r="5" fill="#f6ffdd"/><circle cx="56" cy="46" r="5" fill="#f6ffdd"/></g>',
        'pepper': f'<g class="fd-crop-body"><path d="M36 39c3-8 24-12 31-2 7 10 7 28-7 35-11 5-28 0-31-16-2-8 1-13 7-17Z" fill="url(#fdh)"/><path d="M49 31c1-5 6-8 11-8-1 4-2 7-6 9" stroke="{leaf}" stroke-width="4" stroke-linecap="round" fill="none"/></g>',
        'chili': f'<g class="fd-crop-body"><path d="M33 59c20 8 36-3 34-19-2-14-17-14-22-9 2 4 3 9 0 14-3 7-7 10-12 14Z" fill="url(#fdh)"/><path d="M63 33c1-5 5-7 9-7" stroke="{leaf}" stroke-width="4" stroke-linecap="round"/></g>',
        'cucumber': f'<g class="fd-crop-body"><rect x="29" y="41" width="42" height="18" rx="9" fill="url(#fdh)" transform="rotate(-18 50 50)"/><circle cx="41" cy="48" r="1.5" fill="#dff7ce"/><circle cx="53" cy="54" r="1.5" fill="#dff7ce"/><circle cx="61" cy="47" r="1.5" fill="#dff7ce"/></g>',
        'pumpkin': f'<g class="fd-crop-body"><ellipse cx="50" cy="55" rx="23" ry="18" fill="url(#fdh)"/><path d="M39 40c3 6 3 18 0 30M50 38c3 8 3 22 0 34M61 40c-3 8-3 18 0 30" stroke="#db7e30" stroke-width="2.6"/><path d="M49 34c5-6 9-6 13-4-3 3-6 6-10 7" stroke="{leaf}" stroke-width="4" stroke-linecap="round"/></g>',
        'corn': f'<g class="fd-crop-body"><ellipse cx="50" cy="52" rx="14" ry="23" fill="url(#fdh)"/><path d="M39 61c-2-13 3-24 12-31 10 6 14 18 10 31" fill="#ffd95e" opacity=".85"/><path d="M43 35c-11 4-17 14-16 31 7-4 12-10 16-18M57 35c10 4 16 14 16 31-7-4-12-10-16-18" stroke="{leaf}" stroke-width="5" stroke-linecap="round"/></g>',
        'mushroom': f'<g class="fd-crop-body"><path d="M31 49c4-14 34-14 38 0Z" fill="url(#fdh)"/><rect x="43" y="49" width="14" height="22" rx="7" fill="#f4eadf"/><circle cx="42" cy="46" r="2" fill="#f9f4ec"/><circle cx="56" cy="43" r="2" fill="#f9f4ec"/></g>',
        'tuber': f'<g class="fd-crop-body"><path d="M31 43c8-10 29-8 37 5 6 13-4 29-20 29-19 0-28-19-17-34Z" fill="url(#fdh)"/><path d="M50 30c6-6 9-8 15-8" stroke="{leaf}" stroke-width="4" stroke-linecap="round"/></g>',
        'mango': f'<g class="fd-crop-body"><path d="M39 35c14-10 34 3 28 24-5 18-31 22-40 6-7-14 0-24 12-30Z" fill="url(#fdh)"/><path d="M53 29c4-7 8-9 14-8-3 4-6 8-11 9" fill="{leaf}"/></g>',
        'banana': f'<g class="fd-crop-body"><path d="M33 55c10 10 28 6 37-10-11 5-24 3-33-2-4 2-5 8-4 12Z" fill="url(#fdh)"/><path d="M38 39c6-10 18-15 27-13" stroke="#eed04d" stroke-width="4" stroke-linecap="round"/></g>',
        'apple': f'<g class="fd-crop-body"><path d="M50 35c8-9 25 0 25 18 0 15-9 25-25 25S25 68 25 53c0-17 14-28 25-18Z" fill="url(#fdh)"/><path d="M49 31c1-5 5-8 10-8" stroke="#784b2f" stroke-width="4" stroke-linecap="round"/><path d="M55 29c5-4 10-4 15-1" fill="{leaf}"/></g>',
        'grapes': f'<g class="fd-crop-body"><circle cx="41" cy="43" r="7" fill="{p1}"/><circle cx="53" cy="42" r="7" fill="{p2}"/><circle cx="47" cy="54" r="7" fill="{p1}"/><circle cx="59" cy="54" r="7" fill="{p2}"/><circle cx="41" cy="56" r="7" fill="{p2}"/><path d="M48 33c1-6 4-10 9-12" stroke="{leaf}" stroke-width="4" stroke-linecap="round"/></g>',
        'citrus': f'<g class="fd-crop-body"><circle cx="50" cy="53" r="22" fill="url(#fdh)"/><path d="M50 31v44M28 53h44" stroke="#fff1cd" stroke-width="3" opacity=".7"/><path d="M35 38l30 30M65 38 35 68" stroke="#fff1cd" stroke-width="2.2" opacity=".4"/></g>',
        'guava': f'<g class="fd-crop-body"><path d="M50 34c11 0 21 8 21 21S61 76 50 76 29 67 29 55s10-21 21-21Z" fill="url(#fdh)"/><path d="M50 34c4-6 8-9 13-9" stroke="#7d5030" stroke-width="4" stroke-linecap="round"/></g>',
        'melon': f'<g class="fd-crop-body"><ellipse cx="50" cy="55" rx="24" ry="18" fill="url(#fdh)"/><path d="M32 55h36" stroke="#ffd7dc" stroke-width="2" opacity=".55"/><path d="M50 37c5-6 10-8 15-7" stroke="{leaf}" stroke-width="4" stroke-linecap="round"/></g>',
        'pineapple': f'<g class="fd-crop-body"><ellipse cx="50" cy="57" rx="18" ry="22" fill="url(#fdh)"/><path d="M41 35 50 20 59 35M35 37l8-10M65 37l-8-10" stroke="{leaf}" stroke-width="4" stroke-linecap="round"/><path d="M39 46l22 22M61 46 39 68" stroke="#ffdba8" stroke-width="2" opacity=".5"/></g>',
        'pomegranate': f'<g class="fd-crop-body"><path d="M38 36c8-5 17-5 24 0 7 5 9 12 8 21-1 13-9 22-20 22-12 0-19-11-19-23 0-8 1-15 7-20Z" fill="url(#fdh)"/><path d="M42 35c3-6 14-6 16 0" stroke="{leaf}" stroke-width="3"/></g>',
        'berry': f'<g class="fd-crop-body"><circle cx="41" cy="55" r="10" fill="{p1}"/><circle cx="57" cy="55" r="10" fill="{p2}"/><circle cx="49" cy="43" r="10" fill="{p1}"/><path d="M49 31c4-6 8-8 13-8" stroke="{leaf}" stroke-width="4" stroke-linecap="round"/></g>',
        'dragonfruit': f'<g class="fd-crop-body"><ellipse cx="50" cy="54" rx="23" ry="17" fill="url(#fdh)"/><path d="M34 53c4-4 7-8 8-13M46 70c1-6 2-10 5-15M60 44c4-5 8-8 12-9" stroke="#78c95f" stroke-width="4" stroke-linecap="round"/></g>',
        'date': f'<g class="fd-crop-body"><path d="M40 36c8-4 20 1 22 14 2 12-4 25-17 26-13 0-20-12-18-24 1-9 5-13 13-16Z" fill="url(#fdh)"/><path d="M52 31c6-7 10-10 16-10" stroke="{leaf}" stroke-width="4" stroke-linecap="round"/></g>',
        'rice': f'<g class="fd-crop-body"><path d="M36 72c10-13 10-31 8-47M50 72c3-11 3-25 0-43M64 72c-6-12-10-25-12-41" stroke="{leaf}" stroke-width="3" stroke-linecap="round"/><g fill="#f4deb2"><ellipse cx="42" cy="37" rx="5" ry="2.4" transform="rotate(24 42 37)"/><ellipse cx="39" cy="46" rx="5" ry="2.4" transform="rotate(24 39 46)"/><ellipse cx="47" cy="43" rx="5" ry="2.4" transform="rotate(24 47 43)"/><ellipse cx="56" cy="39" rx="5" ry="2.4" transform="rotate(-25 56 39)"/><ellipse cx="60" cy="48" rx="5" ry="2.4" transform="rotate(-25 60 48)"/><ellipse cx="51" cy="52" rx="5" ry="2.4" transform="rotate(-25 51 52)"/></g></g>',
        'wheat': f'<g class="fd-crop-body"><path d="M38 72V31M50 72V25M62 72V31" stroke="{leaf}" stroke-width="3" stroke-linecap="round"/><g stroke="#d2a24c" stroke-width="3.5" stroke-linecap="round"><path d="M38 40l-5-6M38 46l-5-4M38 52l-5-4M50 34l-6-6M50 40l-6-4M50 46l-6-4M50 52l-6-4M62 40l5-6M62 46l5-4M62 52l5-4"/></g></g>',
        'barley': f'<g class="fd-crop-body"><path d="M42 73c1-16 0-31-2-45M56 73c0-15 1-30 4-45" stroke="{leaf}" stroke-width="3" stroke-linecap="round"/><g stroke="#c99444" stroke-width="2.2" stroke-linecap="round"><path d="M42 34l-10-6M42 40l-11-3M42 46l-10 0M42 52l-10 4M42 58l-8 7M56 34l10-6M56 40l11-3M56 46l10 0M56 52l10 4M56 58l8 7"/></g></g>',
        'millet': f'<g class="fd-crop-body"><path d="M43 73V34M57 73V30" stroke="{leaf}" stroke-width="3" stroke-linecap="round"/><g fill="#cb9641"><circle cx="39" cy="36" r="3"/><circle cx="36" cy="42" r="3"/><circle cx="33" cy="48" r="3"/><circle cx="56" cy="33" r="3"/><circle cx="60" cy="39" r="3"/><circle cx="63" cy="46" r="3"/><circle cx="58" cy="50" r="3"/></g></g>',
        'oilseed': f'<g class="fd-crop-body"><circle cx="50" cy="50" r="9" fill="#7e4c3f"/><g fill="{p1}"><ellipse cx="50" cy="34" rx="7" ry="11"/><ellipse cx="66" cy="50" rx="11" ry="7"/><ellipse cx="50" cy="66" rx="7" ry="11"/><ellipse cx="34" cy="50" rx="11" ry="7"/></g><circle cx="50" cy="50" r="4" fill="#fff5cd"/></g>',
        'turmeric': f'<g class="fd-crop-body"><path d="M34 59c3-10 17-17 27-15 6 2 8 11 3 16-4 4-10 5-17 7-6 2-15 0-13-8Z" fill="url(#fdh)"/><path d="M57 44c4-8 8-10 14-10" stroke="{leaf}" stroke-width="4" stroke-linecap="round"/></g>',
        'pepper-spice': f'<g class="fd-crop-body"><path d="M45 72V34" stroke="{leaf}" stroke-width="3" stroke-linecap="round"/><g fill="{p2}"><circle cx="56" cy="37" r="4"/><circle cx="61" cy="44" r="4"/><circle cx="56" cy="51" r="4"/><circle cx="61" cy="58" r="4"/></g></g>',
        'ginger': f'<g class="fd-crop-body"><path d="M37 58c0-10 6-19 14-19 4 0 6 1 8 4 2-5 6-8 11-8 6 0 11 5 11 12 0 10-8 18-18 18H48c-7 0-11-3-11-7Z" fill="url(#fdh)"/></g>',
        'garlic': f'<g class="fd-crop-body"><path d="M50 31c5 5 8 12 8 17 4-2 8 2 8 9 0 11-6 19-16 19s-16-8-16-19c0-7 4-11 8-9 0-5 3-12 8-17Z" fill="url(#fdh)"/><path d="M50 30c4-6 7-8 11-10" stroke="{leaf}" stroke-width="4" stroke-linecap="round"/></g>',
        'seed-spice': f'<g class="fd-crop-body"><path d="M35 65c10-21 21-31 34-32-2 14-10 30-34 32Z" fill="url(#fdh)"/><g fill="#fff8de"><circle cx="47" cy="49" r="2"/><circle cx="54" cy="46" r="2"/><circle cx="59" cy="42" r="2"/></g></g>',
        'tea': f'<g class="fd-crop-body"><path d="M31 60c0-18 16-31 38-29-3 20-15 38-33 38-3 0-5-3-5-9Z" fill="url(#fdh)"/><path d="M42 68c7-8 13-18 18-30" stroke="{leaf}" stroke-width="3" stroke-linecap="round"/></g>',
        'coffee': f'<g class="fd-crop-body"><ellipse cx="43" cy="54" rx="11" ry="16" fill="url(#fdh)"/><ellipse cx="58" cy="50" rx="11" ry="16" fill="#8d5c3c"/><path d="M43 43c-2 6-2 12 0 20M58 39c-2 6-2 12 0 20" stroke="#e6bf9d" stroke-width="2"/></g>',
        'cocoa': f'<g class="fd-crop-body"><path d="M50 33c13 2 21 12 20 25-1 12-10 21-22 21S28 69 29 56c1-12 8-22 21-23Z" fill="url(#fdh)"/><path d="M50 34v43" stroke="#e6c09e" stroke-width="2.2" opacity=".7"/></g>',
        'tree-crop': f'<g class="fd-crop-body"><path d="M50 72V56" stroke="#8b5b3b" stroke-width="5" stroke-linecap="round"/><path d="M32 57c4-18 31-26 37-5 9 1 11 18-1 20-4 10-33 11-36-4-10-3-7-16 0-19Z" fill="url(#fdh)"/></g>',
        'sugarcane': f'<g class="fd-crop-body"><g fill="url(#fdh)"><rect x="35" y="31" width="10" height="38" rx="4"/><rect x="48" y="27" width="10" height="42" rx="4"/><rect x="61" y="34" width="10" height="35" rx="4"/></g><path d="M40 35c-7-6-11-9-16-9M66 39c7-5 11-7 16-6" stroke="{leaf}" stroke-width="4" stroke-linecap="round"/></g>',
        'cotton': f'<g class="fd-crop-body"><path d="M50 70V40" stroke="{leaf}" stroke-width="3"/><g fill="#fff"><circle cx="41" cy="50" r="8"/><circle cx="52" cy="47" r="9"/><circle cx="59" cy="56" r="7"/></g></g>',
        'nut': f'<g class="fd-crop-body"><path d="M50 33c10 4 18 13 18 23 0 13-8 23-18 23S32 69 32 56c0-10 8-19 18-23Z" fill="url(#fdh)"/><path d="M50 34v42" stroke="#f4ddba" stroke-width="2" opacity=".55"/></g>',
        'flower': f'<g class="fd-crop-body"><circle cx="50" cy="50" r="8" fill="#ffd67b"/><g fill="url(#fdh)"><ellipse cx="50" cy="32" rx="8" ry="14"/><ellipse cx="68" cy="50" rx="14" ry="8"/><ellipse cx="50" cy="68" rx="8" ry="14"/><ellipse cx="32" cy="50" rx="14" ry="8"/><ellipse cx="63" cy="37" rx="8" ry="12" transform="rotate(45 63 37)"/><ellipse cx="37" cy="37" rx="8" ry="12" transform="rotate(-45 37 37)"/></g><path d="M50 72V60" stroke="{leaf}" stroke-width="3"/></g>',
        'grass': f'<g class="fd-crop-body"><path d="M33 72c3-17 8-29 17-42M46 72c1-17 2-31 4-46M58 72c-1-18 2-31 10-44M69 72c-2-14 0-25 8-36" stroke="url(#fdh)" stroke-width="4" stroke-linecap="round"/></g>',
    }[family]
    return f'<svg viewBox="0 0 100 100" class="fd-crop-svg" aria-hidden="true">{stage}{svg}<circle class="fd-crop-ping" cx="76" cy="24" r="4" fill="#fff"/></svg>'


def crop_mark(crop, size="md"):
    spec = CROP_BY_NAME.get(crop)
    category = spec.category if spec else CROP_META.get(crop, {}).get("category", "")
    colors, family = _crop_palette(crop, category)
    svg = _crop_svg(family, crop, colors)
    label = escape(crop or "Crop")
    return Markup(
        f'<span class="fd-crop-mark fd-crop-mark-{escape(size)}" data-crop-mark data-crop="{label}" data-family="{family}" role="img" aria-label="{label}">{svg}</span>'
    )


def inr(value, symbol="\u20B9"):
    """Format a number as Indian Rupees."""
    try:
        v = float(value)
    except (TypeError, ValueError):
        return f"{symbol}0"
    s = f"{v:,.0f}" if v >= 100 or float(v).is_integer() else f"{v:,.2f}"
    return f"{symbol}{s}"


def kg(value):
    """Format kg quantity."""
    try:
        v = float(value)
    except (TypeError, ValueError):
        return "0 kg"
    if v >= 1000:
        return f"{v / 1000:.1f} ton"
    return f"{v:g} kg"


def pretty_status(s):
    return (s or "").replace("_", " ").title()


def status_steps(status):
    """Return (current_index, total) for the delivery pipeline."""
    try:
        return ORDER_STEPS.index(status), len(ORDER_STEPS) - 1
    except ValueError:
        return -1, len(ORDER_STEPS) - 1


def days_ago(date_str):
    try:
        d = datetime.strptime(str(date_str)[:10], "%Y-%m-%d").date()
        n = (datetime.now().date() - d).days
        if n <= 0:
            return "today"
        if n == 1:
            return "yesterday"
        return f"{n} days ago"
    except (ValueError, TypeError):
        return ""


def today_str(offset_days=0):
    return (datetime.now() + timedelta(days=offset_days)).strftime("%Y-%m-%d")
