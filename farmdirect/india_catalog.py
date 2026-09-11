"""India-wide agricultural crop catalogue used by FarmDirect.

The catalogue intentionally focuses on farm-gate produce that can reasonably be
listed in the marketplace. Categories/names are aligned with common Indian
agricultural and horticultural groupings (APEDA/NHB-style categories).

Each entry provides a stable canonical crop name, category, emoji, indicative
base farm-gate price used only for deterministic demo data, indicative weekly
regional demand for the offline forecasting demo, and common spoken aliases.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CropSpec:
    name: str
    category: str
    icon: str
    base_price: float
    base_demand: float
    aliases: tuple[str, ...] = ()


# The app's marketplace is a hackathon/demo environment. Prices below are NOT
# live mandi prices; they seed coherent synthetic history for the offline AI.
_CATEGORY_DEFAULTS = {
    "Vegetables": (32.0, 650.0, "🥬"),
    "Fruits": (65.0, 520.0, "🍎"),
    "Cereals & Grains": (38.0, 1250.0, "🌾"),
    "Millets": (45.0, 520.0, "🌾"),
    "Pulses & Legumes": (92.0, 620.0, "🫘"),
    "Oilseeds": (78.0, 560.0, "🌻"),
    "Spices": (150.0, 260.0, "🌶️"),
    "Plantation & Commercial": (95.0, 430.0, "🌱"),
    "Nuts & Dry Fruits": (320.0, 180.0, "🥜"),
    "Flowers": (95.0, 210.0, "🌸"),
    "Herbs & Medicinal": (85.0, 190.0, "🌿"),
    "Fodder & Forage": (18.0, 900.0, "🌿"),
}

# category -> [(canonical name, optional price, optional demand, optional icon, aliases)]
_RAW: dict[str, list[tuple]] = {
    "Vegetables": [
        ("Tomato", 24, 1400, "🍅", ("tamatar", "thakkali", "தக்காளி")),
        ("Onion", 19, 2600, "🧅", ("pyaz", "pyaaz", "vengayam", "வெங்காயம்")),
        ("Potato", 22, 2200, "🥔", ("aloo", "alu", "urulai", "உருளைக்கிழங்கு")),
        ("Brinjal", 34, 700, "🍆", ("eggplant", "aubergine", "baingan", "kathirikai", "கத்தரிக்காய்")),
        ("Okra", 42, 620, "🥬", ("lady finger", "ladies finger", "bhindi", "vendakkai", "வெண்டைக்காய்")),
        ("Cabbage", 28, 600, "🥬", ("patta gobhi", "muttaikos", "முட்டைகோஸ்")),
        ("Cauliflower", 35, 650, "🥦", ("phool gobhi", "gobi", "cauli flower")),
        ("Carrot", 34, 520, "🥕", ("gajar", "carrots")),
        ("Radish", 26, 420, "🥕", ("mooli", "mulangi", "முள்ளங்கி")),
        ("Beetroot", 38, 350, "🫜", ("beet", "beet root", "chukandar")),
        ("Turnip", 30, 260, "🫜", ("shaljam", "turnips")),
        ("Green Peas", 58, 480, "🫛", ("peas", "matar", "green pea")),
        ("French Bean", 62, 360, "🫛", ("french beans", "green beans", "beans")),
        ("Cluster Bean", 48, 290, "🫛", ("guar", "guar bean", "kothavarangai")),
        ("Cowpea Vegetable", 46, 280, "🫛", ("yardlong bean", "long bean", "lobia beans")),
        ("Broad Bean", 52, 240, "🫛", ("fava bean", "sem", "avarai")),
        ("Capsicum", 55, 450, "🫑", ("bell pepper", "shimla mirch", "sweet pepper")),
        ("Green Chili", 48, 360, "🌶️", ("green chilli", "hari mirch", "pachai milagai", "பச்சை மிளகாய்")),
        ("Cucumber", 28, 640, "🥒", ("kheera", "vellari", "cucumbers")),
        ("Gherkin", 36, 250, "🥒", ("gherkin cucumber", "pickling cucumber")),
        ("Bottle Gourd", 30, 420, "🥒", ("lauki", "dudhi", "sorakkai", "சுரைக்காய்")),
        ("Bitter Gourd", 44, 340, "🥒", ("karela", "pavakkai", "பாகற்காய்")),
        ("Ridge Gourd", 40, 330, "🥒", ("turai", "peerkangai", "பீர்க்கங்காய்")),
        ("Sponge Gourd", 38, 260, "🥒", ("gilki", "spongeguard", "luffa")),
        ("Ash Gourd", 26, 300, "🎃", ("winter melon", "petha", "poosanikai")),
        ("Snake Gourd", 36, 260, "🥒", ("padwal", "pudalangai", "புடலங்காய்")),
        ("Pointed Gourd", 48, 250, "🥒", ("parwal", "potol")),
        ("Ivy Gourd", 42, 250, "🥒", ("tindora", "kovakkai", "கோவைக்காய்")),
        ("Pumpkin", 25, 520, "🎃", ("kaddu", "poosanikai", "pumpkins")),
        ("Summer Squash", 42, 220, "🥒", ("squash", "yellow squash")),
        ("Zucchini", 70, 180, "🥒", ("courgette", "zucchinis")),
        ("Drumstick", 68, 300, "🌿", ("moringa pod", "moringa", "murungakkai", "முருங்கைக்காய்")),
        ("Knol Khol", 36, 240, "🥬", ("kohlrabi", "ganth gobhi", "noolkol")),
        ("Broccoli", 90, 210, "🥦", ("green broccoli",)),
        ("Sweet Corn", 42, 420, "🌽", ("corn", "sweetcorn")),
        ("Baby Corn", 74, 210, "🌽", ("babycorn",)),
        ("Spinach", 24, 360, "🥬", ("palak", "keerai", "பாலக்கீரை")),
        ("Amaranth Greens", 26, 300, "🥬", ("amaranthus", "chaulai", "arai keerai", "thandu keerai")),
        ("Fenugreek Leaves", 32, 260, "🌿", ("methi leaves", "methi", "vendhaya keerai")),
        ("Coriander Leaves", 36, 320, "🌿", ("coriander", "cilantro", "dhania leaves", "kothamalli")),
        ("Curry Leaves", 70, 180, "🌿", ("kadi patta", "karuveppilai", "கருவேப்பிலை")),
        ("Mint Leaves", 48, 200, "🌿", ("mint", "pudina", "pudhina")),
        ("Lettuce", 70, 180, "🥬", ("iceberg lettuce", "leaf lettuce")),
        ("Celery", 90, 120, "🌿", ("celery stalk",)),
        ("Spring Onion", 48, 220, "🧅", ("green onion", "scallion")),
        ("Leek", 85, 110, "🌿", ("leeks",)),
        ("Mushroom", 130, 260, "🍄", ("button mushroom", "mushrooms")),
        ("Sweet Potato", 38, 360, "🍠", ("shakarkand", "sakkaravalli kilangu")),
        ("Yam", 48, 280, "🍠", ("suran", "senai kilangu")),
        ("Elephant Foot Yam", 52, 260, "🍠", ("suran", "jimikand", "senai")),
        ("Colocasia", 44, 240, "🍠", ("arbi", "taro", "seppankilangu")),
        ("Tapioca", 30, 420, "🍠", ("cassava", "maravalli kilangu", "kappa")),
    ],
    "Fruits": [
        ("Mango", 110, 900, "🥭", ("aam", "mampazham", "மாம்பழம்")),
        ("Banana", 30, 1200, "🍌", ("kela", "vazhaipazham", "வாழைப்பழம்")),
        ("Apple", 125, 620, "🍎", ("seb", "apples")),
        ("Grapes", 90, 650, "🍇", ("angoor", "grape")),
        ("Orange", 70, 650, "🍊", ("santra", "oranges")),
        ("Mandarin", 85, 400, "🍊", ("mandarin orange", "kinnow", "nagpur orange")),
        ("Sweet Lime", 65, 430, "🍋", ("mosambi", "mausambi", "sweet lemon")),
        ("Lemon", 68, 520, "🍋", ("nimbu", "elumichai", "எலுமிச்சை")),
        ("Lime", 62, 360, "🍋", ("key lime", "acid lime")),
        ("Guava", 52, 500, "🍐", ("amrud", "koyya", "கொய்யா")),
        ("Papaya", 34, 520, "🍈", ("papita", "pappali", "பப்பாளி")),
        ("Pineapple", 48, 380, "🍍", ("ananas", "annachi pazham")),
        ("Pomegranate", 145, 420, "🔴", ("anar", "mathulai", "மாதுளை")),
        ("Watermelon", 24, 720, "🍉", ("tarbooz", "tharboosani")),
        ("Muskmelon", 42, 420, "🍈", ("kharbuja", "cantaloupe", "kirni")),
        ("Sapota", 58, 300, "🥝", ("chikoo", "chiku", "sapodilla")),
        ("Litchi", 135, 240, "🍒", ("lychee", "lichi")),
        ("Jackfruit", 42, 360, "🍈", ("kathal", "palaa pazham", "பலாப்பழம்")),
        ("Custard Apple", 88, 260, "🍏", ("sitaphal", "seethapazham", "sugar apple")),
        ("Amla", 62, 280, "🟢", ("indian gooseberry", "nellikai", "நெல்லிக்காய்")),
        ("Ber", 55, 220, "🍒", ("indian jujube", "bor", "ilanthai")),
        ("Jamun", 120, 180, "🫐", ("java plum", "black plum", "naval pazham")),
        ("Fig", 160, 160, "🟣", ("anjeer", "figs")),
        ("Dragon Fruit", 170, 180, "🐉", ("pitaya", "dragonfruit")),
        ("Strawberry", 180, 180, "🍓", ("strawberries",)),
        ("Kiwi", 220, 120, "🥝", ("kiwi fruit",)),
        ("Pear", 110, 210, "🍐", ("nashpati", "pears")),
        ("Peach", 145, 150, "🍑", ("aadu fruit", "peaches")),
        ("Plum", 145, 150, "🟣", ("aloo bukhara", "plums")),
        ("Apricot", 180, 120, "🍑", ("khubani", "apricots")),
        ("Cherry", 240, 100, "🍒", ("cherries",)),
        ("Avocado", 210, 130, "🥑", ("butter fruit", "avocados")),
        ("Passion Fruit", 150, 110, "🟣", ("passionfruit",)),
        ("Rambutan", 190, 90, "🔴", ("rambutans",)),
        ("Mangosteen", 240, 80, "🟣", ("mangostin",)),
        ("Date Fruit", 260, 100, "🟤", ("dates", "khajur", "date palm fruit")),
        ("Bael", 70, 150, "🟢", ("wood apple bael", "bel fruit")),
        ("Wood Apple", 75, 130, "🟤", ("kaitha", "vilam pazham")),
        ("Mulberry", 160, 100, "🫐", ("shahtoot", "mulberries")),
        ("Karonda", 90, 100, "🔴", ("carissa", "karonda fruit")),
        ("Phalsa", 140, 80, "🫐", ("falsa", "grewia asiatica")),
    ],
    "Cereals & Grains": [
        ("Rice", 52, 1250, "🌾", ("paddy", "chawal", "arisi", "அரிசி")),
        ("Basmati Rice", 92, 600, "🌾", ("basmati", "basmati chawal")),
        ("Sona Masoori Rice", 60, 540, "🌾", ("sona masuri", "sona masoori")),
        ("Red Rice", 86, 220, "🌾", ("matta rice", "kerala red rice")),
        ("Black Rice", 180, 120, "🌾", ("chak hao", "forbidden rice")),
        ("Wheat", 38, 1500, "🌾", ("gehun", "godhumai", "கோதுமை")),
        ("Durum Wheat", 48, 430, "🌾", ("macaroni wheat", "durum")),
        ("Maize", 28, 1100, "🌽", ("corn grain", "makka", "makkai")),
        ("Barley", 36, 430, "🌾", ("jau", "barley grain")),
        ("Oats", 54, 320, "🌾", ("oat grain", "jai")),
        ("Sorghum", 38, 520, "🌾", ("jowar", "cholam", "சோளம்")),
        ("Buckwheat", 85, 170, "🌾", ("kuttu", "buck wheat")),
    ],
    "Millets": [
        ("Pearl Millet", 35, 600, "🌾", ("bajra", "kambu", "கம்பு")),
        ("Finger Millet", 48, 520, "🌾", ("ragi", "nachni", "kelvaragu", "கேழ்வரகு")),
        ("Foxtail Millet", 72, 300, "🌾", ("kangni", "thinai", "தினை")),
        ("Little Millet", 76, 260, "🌾", ("kutki", "samai", "சாமை")),
        ("Kodo Millet", 70, 250, "🌾", ("kodra", "varagu", "வரகு")),
        ("Barnyard Millet", 82, 230, "🌾", ("sanwa", "jhangora", "kuthiraivali")),
        ("Proso Millet", 68, 200, "🌾", ("cheena", "barri", "panivaragu")),
        ("Browntop Millet", 95, 130, "🌾", ("brown top millet", "korale")),
    ],
    "Pulses & Legumes": [
        ("Chickpea", 86, 720, "🫘", ("gram", "chana", "bengal gram", "kondakadalai")),
        ("Pigeon Pea", 110, 680, "🫘", ("tur", "toor", "arhar", "thuvaram paruppu")),
        ("Green Gram", 108, 520, "🫘", ("moong", "mung bean", "pachai payaru")),
        ("Black Gram", 116, 500, "🫘", ("urad", "black matpe", "ulundhu")),
        ("Lentil", 94, 520, "🫘", ("masoor", "masur", "red lentil")),
        ("Field Pea", 76, 330, "🫛", ("dry peas", "matar dal")),
        ("Kidney Bean", 145, 310, "🫘", ("rajma", "red kidney bean")),
        ("Moth Bean", 96, 210, "🫘", ("matki", "moth dal")),
        ("Horse Gram", 72, 240, "🫘", ("kulthi", "kollu", "கொள்ளு")),
        ("Cowpea", 88, 260, "🫘", ("lobia", "black eyed pea", "karamani")),
        ("Lablab Bean", 90, 230, "🫘", ("field bean", "hyacinth bean", "avarekalu")),
        ("Soybean", 54, 780, "🫘", ("soya bean", "soy bean")),
    ],
    "Oilseeds": [
        ("Groundnut", 72, 720, "🥜", ("peanut", "moongfali", "verkadalai")),
        ("Mustard", 68, 600, "🌼", ("sarson", "mustard seed")),
        ("Rapeseed", 66, 430, "🌼", ("rape seed", "canola seed")),
        ("Sesame", 135, 360, "🌱", ("til", "gingelly", "ellu", "எள்")),
        ("Sunflower Seed", 62, 380, "🌻", ("sunflower", "surajmukhi seed")),
        ("Safflower", 70, 250, "🌼", ("kusum", "karadi seed")),
        ("Linseed", 88, 260, "🌱", ("flaxseed", "flax seed", "alsi")),
        ("Niger Seed", 92, 180, "🌱", ("ramtil", "nigerseed")),
        ("Castor Seed", 64, 300, "🌱", ("castor", "arandi", "amanakku")),
    ],
    "Spices": [
        ("Turmeric", 135, 420, "🟡", ("haldi", "manjal", "மஞ்சள்")),
        ("Dry Chili", 180, 400, "🌶️", ("dry chilli", "red chili", "lal mirch", "vatral milagai")),
        ("Black Pepper", 620, 250, "⚫", ("pepper", "kali mirch", "milagu", "மிளகு")),
        ("Small Cardamom", 1550, 130, "🌿", ("green cardamom", "elaichi", "elakkai")),
        ("Large Cardamom", 980, 90, "🌿", ("black cardamom", "badi elaichi")),
        ("Coriander Seed", 105, 330, "🌿", ("dhania seed", "coriander seeds", "malli seed")),
        ("Cumin", 280, 300, "🌿", ("jeera", "cumin seed", "seeragam")),
        ("Fennel", 170, 220, "🌿", ("saunf", "fennel seed", "sombu")),
        ("Fenugreek Seed", 92, 240, "🌿", ("methi seed", "vendhayam")),
        ("Ajwain", 190, 150, "🌿", ("carom seed", "omam")),
        ("Dill Seed", 145, 110, "🌿", ("suva seed", "dill seeds")),
        ("Clove", 760, 90, "🌿", ("laung", "cloves", "kirambu")),
        ("Cinnamon", 380, 120, "🌿", ("dalchini", "cinnamon bark", "lavangapattai")),
        ("Cassia", 290, 100, "🌿", ("cassia bark",)),
        ("Nutmeg", 520, 100, "🌰", ("jaiphal", "jathikai")),
        ("Mace", 980, 70, "🌰", ("javitri", "mace spice")),
        ("Star Anise", 640, 70, "⭐", ("chakra phool", "star anise spice")),
        ("Saffron", 185000, 15, "🌺", ("kesar", "zafran", "saffron strands")),
        ("Tamarind", 115, 260, "🟤", ("imli", "puli", "புளி")),
        ("Ginger", 95, 420, "🫚", ("adrak", "inji", "இஞ்சி")),
        ("Garlic", 150, 520, "🧄", ("lahsun", "poondu", "பூண்டு")),
        ("Bay Leaf", 180, 120, "🌿", ("tej patta", "bayleaf")),
        ("Vanilla", 1250, 60, "🌿", ("vanilla bean", "vanilla pods")),
        ("Kokum", 210, 90, "🟣", ("kokam", "garcinia indica")),
    ],
    "Plantation & Commercial": [
        ("Tea", 190, 520, "🍃", ("tea leaves", "chai patti")),
        ("Coffee Arabica", 420, 280, "☕", ("arabica coffee", "coffee bean arabica")),
        ("Coffee Robusta", 300, 320, "☕", ("robusta coffee", "coffee bean robusta")),
        ("Cocoa", 260, 180, "🍫", ("cacao", "cocoa bean")),
        ("Rubber", 180, 260, "🌳", ("natural rubber", "rubber latex")),
        ("Arecanut", 480, 240, "🌴", ("areca nut", "supari", "pakku")),
        ("Coconut", 42, 650, "🥥", ("nariyal", "thengai", "தேங்காய்")),
        ("Cashew", 180, 300, "🥜", ("cashew nut in shell", "kaju", "mundhiri")),
        ("Sugarcane", 4.5, 1600, "🎋", ("sugar cane", "ganna", "karumbu", "கரும்பு")),
        ("Cotton", 72, 900, "☁️", ("kapas", "cotton lint", "paruthi")),
        ("Jute", 58, 420, "🧵", ("raw jute", "patson")),
    ],
    "Nuts & Dry Fruits": [
        ("Walnut", 520, 160, "🌰", ("akhrot", "walnuts")),
        ("Almond", 620, 160, "🌰", ("badam", "almonds")),
        ("Pistachio", 980, 90, "🌰", ("pista", "pistachios")),
        ("Chironji", 850, 70, "🌰", ("charoli", "chironjee")),
        ("Pine Nut", 1700, 55, "🌰", ("chilgoza", "pine nuts")),
    ],
    "Flowers": [
        ("Marigold", 85, 360, "🌼", ("genda", "samandhi", "செவ்வந்தி")),
        ("Rose", 160, 300, "🌹", ("gulab", "roses")),
        ("Jasmine", 480, 220, "🌼", ("malli", "malligai", "மல்லிகை")),
        ("Tuberose", 210, 180, "🌸", ("rajnigandha", "sampangi")),
        ("Chrysanthemum", 120, 190, "🌼", ("shevanti", "chrysanthemum flower")),
        ("Gladiolus", 180, 120, "🌷", ("gladioli",)),
        ("Gerbera", 210, 130, "🌼", ("gerbera flower",)),
        ("Carnation", 240, 110, "🌸", ("carnation flower",)),
        ("Orchid", 380, 90, "🌺", ("orchids",)),
        ("Anthurium", 320, 80, "🌺", ("anthurium flower",)),
        ("Lily", 260, 100, "🌸", ("lilies",)),
        ("Lotus", 180, 120, "🪷", ("kamal", "thamarai")),
        ("Aster", 160, 100, "🌼", ("aster flower",)),
        ("Gaillardia", 110, 110, "🌼", ("blanket flower",)),
        ("Crossandra", 220, 130, "🌺", ("kanakambaram", "firecracker flower")),
        ("Hibiscus", 160, 110, "🌺", ("gudhal", "semparuthi")),
        ("Dahlia", 190, 90, "🌸", ("dahlia flower",)),
    ],
    "Herbs & Medicinal": [
        ("Tulsi", 90, 220, "🌿", ("holy basil", "tulasi")),
        ("Ashwagandha", 180, 180, "🌿", ("indian ginseng", "withania")),
        ("Aloe Vera", 35, 260, "🌿", ("aloe", "ghritkumari", "katralai")),
        ("Lemongrass", 55, 180, "🌿", ("lemon grass", "citronella grass")),
        ("Stevia", 160, 100, "🌿", ("sweet leaf", "stevia leaf")),
        ("Isabgol", 210, 150, "🌿", ("psyllium", "psyllium husk seed")),
        ("Kalmegh", 130, 90, "🌿", ("andrographis",)),
        ("Safed Musli", 680, 60, "🌿", ("white musli",)),
        ("Shatavari", 260, 90, "🌿", ("asparagus racemosus",)),
        ("Brahmi", 120, 100, "🌿", ("bacopa", "water hyssop")),
        ("Senna", 95, 120, "🌿", ("senna leaves", "sonamukhi")),
        ("Vetiver", 140, 100, "🌿", ("khus", "vettiver")),
        ("Giloy", 85, 100, "🌿", ("guduchi", "tinospora")),
        ("Patchouli", 145, 70, "🌿", ("patchouli leaves",)),
    ],
    "Fodder & Forage": [
        ("Berseem", 16, 1000, "🌿", ("egyptian clover", "berseem fodder")),
        ("Lucerne", 18, 900, "🌿", ("alfalfa", "lucerne fodder")),
        ("Napier Grass", 12, 1200, "🌿", ("elephant grass", "hybrid napier")),
        ("Fodder Maize", 14, 1150, "🌽", ("maize fodder", "corn fodder")),
        ("Fodder Sorghum", 14, 1100, "🌾", ("jowar fodder", "sorghum fodder")),
        ("Fodder Cowpea", 18, 850, "🌿", ("cowpea fodder", "lobia fodder")),
        ("Fodder Oats", 17, 850, "🌾", ("oat fodder", "oats fodder")),
    ],
}


def _build_catalog() -> tuple[CropSpec, ...]:
    out: list[CropSpec] = []
    seen: set[str] = set()
    for category, rows in _RAW.items():
        default_price, default_demand, default_icon = _CATEGORY_DEFAULTS[category]
        for row in rows:
            name = row[0]
            if name in seen:
                raise RuntimeError(f"Duplicate crop in India catalogue: {name}")
            seen.add(name)
            price = float(row[1] if len(row) > 1 and row[1] is not None else default_price)
            demand = float(row[2] if len(row) > 2 and row[2] is not None else default_demand)
            icon = str(row[3] if len(row) > 3 and row[3] else default_icon)
            aliases = tuple(row[4] if len(row) > 4 else ())
            out.append(CropSpec(name, category, icon, price, demand, aliases))
    return tuple(out)


CROP_CATALOG: tuple[CropSpec, ...] = _build_catalog()
CROP_BY_NAME = {c.name: c for c in CROP_CATALOG}
CROP_NAMES = tuple(c.name for c in CROP_CATALOG)
CATEGORIES = tuple(_RAW.keys())

# Common premium / region-specific listing names. Crops not present here use
# "Farm Fresh <crop>" automatically.
LISTING_TITLES = {
    "Tomato": ("Nashik Red Tomato — Grade A", "Hybrid Tomato — Farm Fresh"),
    "Onion": ("Lasalgaon Red Onion — Sorted", "Farm Cured Onion"),
    "Potato": ("Kufri Jyoti Potato", "Fresh Dug Table Potato"),
    "Mango": ("Alphonso Mango — Premium", "Kesar Mango — Farm Fresh"),
    "Banana": ("Grand Naine Banana", "Nendran Banana"),
    "Apple": ("Himachal Royal Delicious Apple", "Kashmir Apple — Premium"),
    "Grapes": ("Nashik Thompson Seedless Grapes", "Sharad Seedless Grapes"),
    "Pomegranate": ("Bhagwa Pomegranate",),
    "Orange": ("Nagpur Orange",),
    "Mandarin": ("Kinnow Mandarin",),
    "Rice": ("Sona Masoori Rice", "Farm Fresh Paddy Rice"),
    "Basmati Rice": ("Traditional Basmati Rice", "Pusa Basmati 1121"),
    "Wheat": ("Lokwan Wheat", "Sharbati Wheat"),
    "Pearl Millet": ("Bajra — Cleaned Grain",),
    "Finger Millet": ("Ragi — Premium Grain",),
    "Chickpea": ("Desi Chana", "Kabuli Chickpea"),
    "Pigeon Pea": ("Tur / Arhar — Cleaned",),
    "Groundnut": ("Bold Groundnut Pods",),
    "Mustard": ("Yellow Mustard Seed",),
    "Turmeric": ("Erode Turmeric Fingers", "Lakadong Turmeric"),
    "Dry Chili": ("Guntur Sannam Dry Chilli", "Byadgi Dry Chilli"),
    "Black Pepper": ("Malabar Black Pepper",),
    "Small Cardamom": ("Kerala Green Cardamom",),
    "Saffron": ("Kashmir Saffron — Mongra",),
    "Tea": ("Assam Orthodox Tea Leaf", "Nilgiri Tea Leaf"),
    "Coffee Arabica": ("Coorg Arabica Coffee",),
    "Coffee Robusta": ("Chikmagalur Robusta Coffee",),
    "Coconut": ("Pollachi Mature Coconut",),
    "Cashew": ("Goa Raw Cashew Nut",),
    "Arecanut": ("Coastal Arecanut",),
    "Marigold": ("Fresh Marigold Flowers",),
    "Jasmine": ("Madurai Malli Jasmine",),
    "Rose": ("Fresh Cut Rose",),
}

# Region keys used by catalog_seed.py. Special mappings keep iconic crops in
# plausible origin regions while general crops are distributed nationwide.
CROP_REGION_HINTS = {
    "Saffron": "srinagar", "Apple": "shimla", "Cherry": "srinagar",
    "Apricot": "srinagar", "Walnut": "srinagar", "Pine Nut": "shimla",
    "Tea": "guwahati", "Large Cardamom": "gangtok", "Small Cardamom": "kochi",
    "Black Pepper": "kochi", "Coffee Arabica": "chikmagalur", "Coffee Robusta": "chikmagalur",
    "Rubber": "kochi", "Coconut": "coimbatore", "Arecanut": "mangaluru",
    "Cashew": "goa", "Mango": "ratnagiri", "Grapes": "nashik", "Pomegranate": "nashik",
    "Onion": "nashik", "Orange": "nagpur", "Mandarin": "amritsar",
    "Turmeric": "erode", "Jasmine": "madurai", "Banana": "trichy",
    "Dry Chili": "guntur", "Basmati Rice": "karnal", "Rice": "thanjavur",
    "Jute": "kolkata", "Litchi": "muzaffarpur", "Pineapple": "agartala",
    "Kiwi": "itanagar", "Dragon Fruit": "pune", "Kokum": "goa",
}


def crop_meta() -> dict[str, dict[str, str]]:
    """Return the shape expected by existing Jinja templates."""
    gradients = {
        "Vegetables": "linear-gradient(135deg,#b7f7c9,#5ecf82)",
        "Fruits": "linear-gradient(135deg,#ffe59a,#ff9f68)",
        "Cereals & Grains": "linear-gradient(135deg,#f7e4a0,#caa743)",
        "Millets": "linear-gradient(135deg,#e8d79c,#b98e45)",
        "Pulses & Legumes": "linear-gradient(135deg,#e9c6a2,#b9764d)",
        "Oilseeds": "linear-gradient(135deg,#ffe37a,#eeb93d)",
        "Spices": "linear-gradient(135deg,#ffbd75,#e5583f)",
        "Plantation & Commercial": "linear-gradient(135deg,#a4e0b2,#3d9b65)",
        "Nuts & Dry Fruits": "linear-gradient(135deg,#e5c6a1,#9f6f4d)",
        "Flowers": "linear-gradient(135deg,#ffc6e1,#b08cff)",
        "Herbs & Medicinal": "linear-gradient(135deg,#b6efc5,#61b878)",
        "Fodder & Forage": "linear-gradient(135deg,#cae8a5,#76ad55)",
    }
    return {c.name: {"icon": c.icon, "grad": gradients[c.category], "category": c.category}
            for c in CROP_CATALOG}
