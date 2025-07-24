from PIL import Image, ImageDraw, ImageFont
import json
from datetime import datetime
import pytz
import locale
import requests
from io import BytesIO
import os
import cairosvg  # nouveau import pour SVG

# === PARAMÈTRES ===
IMG_WIDTH = 1200
IMG_HEIGHT = 825
BACKGROUND_COLOR = (255, 255, 255)
TEXT_COLOR = (0, 0, 0)
FONT_PATH = "Ubuntu-R.ttf"
icon_birthday = Image.open("birthday.png").convert("RGBA").resize((48, 48))

# === CONFIGURATION LOCALE POUR LES DATES ===
try:
    locale.setlocale(locale.LC_TIME, "fr_FR.UTF-8")
except locale.Error:
    print("⚠️ Locale fr_FR.UTF-8 non disponible. Les noms de mois/jours resteront en anglais.")

# === CHARGEMENT CONFIG.JSON ===
with open("/config/config.json", "r", encoding="utf-8") as f:
    config = json.load(f)
trash_days = config.get("trash_days", {})
title = config.get("dashboard_title", "Dashboard")
section_title = config.get("birthday_section_title", "Anniversaires")
label_years = config.get("label_years", "ans")
birthdays = config.get("anniversaires", [])
HA_URL = config.get("ha_url")
TOKEN = config.get("ha_token")
tz_here = pytz.timezone(config.get("timezone"))

# Récupération config météo
owm_conf = config.get("openweathermap", {})
API_KEY = owm_conf.get("api_key", "")
CITY = owm_conf.get("city", "Paris,FR")
UNITS = owm_conf.get("units", "metric")
LANG = owm_conf.get("lang", "fr")

HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json",
}

def get_sensor_state(entity_id):
    url = f"{HA_URL}/api/states/{entity_id}"
    response = requests.get(url, headers=HEADERS)
    if response.status_code == 200:
        data = response.json()
        state = data.get("state", "0")
        try:
            return float(state)
        except ValueError:
            print(f"Valeur non convertible en float pour {entity_id}: '{state}'")
            return 0
    else:
        print(f"Erreur API pour {entity_id}: {response.status_code}")
        return 0

# === CALCULER LES 10 PROCHAINS ANNIVERSAIRES ===
today = datetime.today()
today_md = (today.month, today.day)
upcoming_birthdays = []

for person in birthdays:
    birth_date = datetime.strptime(person["date"], "%Y-%m-%d")
    birthday_this_year = birth_date.replace(year=today.year)

    if (birth_date.month, birth_date.day) < (today.month, today.day):
        birthday_this_year = birthday_this_year.replace(year=today.year + 1)

    age = birthday_this_year.year - birth_date.year
    is_today = (birth_date.month, birth_date.day) == (today.month, today.day)

    upcoming_birthdays.append({
        "nom": person["nom"],
        "date": birthday_this_year,
        "age": age,
        "is_today": is_today
    })

upcoming_birthdays.sort(key=lambda x: x["date"])
next_10 = upcoming_birthdays[:10]

# === FONCTION POUR CHARGER SVG EN IMAGE PIL ===
def svg_to_pil(svg_path, size=(256, 256)):
    png_bytes = cairosvg.svg2png(url=svg_path, output_width=size[0], output_height=size[1])
    return Image.open(BytesIO(png_bytes)).convert("RGBA")

# === CRÉER L'IMAGE ===#
image = Image.new("RGB", (IMG_WIDTH, IMG_HEIGHT), BACKGROUND_COLOR)
#image = Image.new("RGBA", (IMG_WIDTH, IMG_HEIGHT), BACKGROUND_COLOR + (255,))
draw = ImageDraw.Draw(image)

font_title = ImageFont.truetype(FONT_PATH, 60)
font_date = ImageFont.truetype(FONT_PATH, 36)
font_subtitle = ImageFont.truetype(FONT_PATH, 40)
font_text = ImageFont.truetype(FONT_PATH, 32)
font_text2 = ImageFont.truetype(FONT_PATH, 24)
# === TITRE PRINCIPAL ===
title_w, title_h = draw.textbbox((0, 0), title, font=font_title)[2:]
draw.text(((IMG_WIDTH - title_w) / 2, 30), title, fill=TEXT_COLOR, font=font_title)

# === DATE EN DESSOUS DU TITRE ===
formatted_date = today.strftime("%A %d %B %Y").capitalize()
date_w, _ = draw.textbbox((0, 0), formatted_date, font=font_date)[2:]
draw.text(((IMG_WIDTH - date_w) / 2, 110), formatted_date, fill=TEXT_COLOR, font=font_date)

# === TITRE DE SECTION ===
draw.text((50, 170), section_title, fill=TEXT_COLOR, font=font_subtitle)

# === LISTE DES ANNIVERSAIRES ===
start_y = 240
line_height = 40
for i, entry in enumerate(next_10):
    date_str = entry["date"].strftime("• %d-%m")
    line = f"{date_str} : {entry['nom']} - {entry['age']} {label_years}"
    x = 50
    y = start_y + i * line_height
    draw.text((x, y), line, fill=TEXT_COLOR, font=font_text)
    if entry["is_today"]:
        text_width = draw.textlength(line, font=font_text)
        image.paste(icon_birthday, (x + int(text_width) + 10, y - 10), mask=icon_birthday)

# === URL API OPENWEATHERMAP ===
WEATHER_JSON_URL = (
    f"https://api.openweathermap.org/data/2.5/weather?"
    f"q={CITY}&units={UNITS}&lang={LANG}&appid={API_KEY}"
)
try:
    response = requests.get(WEATHER_JSON_URL)
    weather_data = response.json()

    icon_code = weather_data["weather"][0]["icon"]
    description = weather_data["weather"][0]["description"]
    temp = weather_data["main"]["temp"]
    temp_min = weather_data["main"]["temp_min"]
    temp_max = weather_data["main"]["temp_max"]
    wind_speed = round(weather_data["wind"]["speed"] * 3.6)  # m/s → km/h
    wind_deg = weather_data["wind"].get("deg", 0)

    # === CHARGER L'ICÔNE SVG LOCALE ===
    icon_svg_path = f"icons/{icon_code}.svg"
    if not os.path.exists(icon_svg_path):
        print(f"⚠️ Icône SVG manquante : {icon_svg_path}")
        icon_img = Image.new("RGBA", (256, 256), (0, 0, 0, 0))  # vide
    else:
        icon_img = svg_to_pil(icon_svg_path, size=(256, 256))

    # Affichage météo à droite
    weather_x = 850
    weather_y = 50

    image.paste(icon_img, (weather_x + 36, weather_y), mask=icon_img)

    draw.text((weather_x +50, weather_y + 250), description, fill=TEXT_COLOR, font=font_text)
    draw.text((weather_x +50, weather_y + 280), f"Temp : {temp:.1f}°C", fill=TEXT_COLOR, font=font_text)
    draw.text((weather_x +50, weather_y + 310), f"Vent : {wind_speed} km/h", fill=TEXT_COLOR, font=font_text)

except Exception as e:
    print(f"⚠️ Erreur lors du chargement météo : {e}")

# Vérifier si le jour est dans la config (attention clé string dans JSON)
jour_semaine_num = today.weekday()
key = str(jour_semaine_num)
if key in trash_days:
    icon_path = trash_days[key]
    if os.path.exists(icon_path):
        poubelle_icon = Image.open(icon_path).convert("RGBA").resize((100, 100))  # ajuster la taille
        # Coller en bas à droite (ajuster les coords si besoin)
        image.paste(poubelle_icon, (IMG_WIDTH - 120, IMG_HEIGHT - 120), poubelle_icon)
      
# === CALCUL DES DONNÉES HA ===
# Liste des entités énergétiques (depuis config)
energy_entities = config.get("energy_entities", [])

data = {
    entity["entity_id"]: get_sensor_state(entity["entity_id"])
    for entity in energy_entities
}
# === TABLEAU CONSOMMATION ÉLECTRIQUE ===
table_x = 900
table_y = 500
line_height = 25

draw.text((table_x, table_y - 40), "Conso Élec", fill=TEXT_COLOR, font=font_subtitle)

for i, entity in enumerate(energy_entities):
    entity_id = entity["entity_id"]
    label = entity["label"]
    value = data.get(entity_id, 0)
    if "€" in label:
        text_value = f"{value:.2f} €"
    else:
        text_value = f"{value:.2f} kWh"
    draw.text((table_x, table_y + i * line_height), f"{label} : {text_value}", fill=TEXT_COLOR, font=font_text2)

# Date/heure actuelle

now = datetime.now(tz_here)
update_text = now.strftime("Mis à jour le %d/%m/%Y à %H:%M")

# Position bas gauche (à adapter si nécessaire selon la taille de ton écran Inkplate)
# Exemple : 20px depuis la gauche et 20px depuis le bas

padding = 50
position = (padding, IMG_HEIGHT - padding)

# Affichage du texte
draw.text(position, update_text, fill=TEXT_COLOR, font=font_text2)

# === SAUVEGARDE ===
image.save("maginkdash.png")
print("✅ Image 'dashboard.png' générée avec succès.")
