# bot.py
import json
import os
import random
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
import requests
from deep_translator import GoogleTranslator
from config import TELEGRAM_TOKEN, JIKAN_API, SUPPORTED_LANGUAGES, DEFAULT_LANGUAGE

# Traducteur
translator = GoogleTranslator(source='auto', target='fr')

USER_DATA_FILE = 'user_data.json'

# Charger ou créer les données utilisateur
if not os.path.exists(USER_DATA_FILE):
    with open(USER_DATA_FILE, 'w') as f:
        json.dump({}, f)

def load_user_data():
    with open(USER_DATA_FILE, 'r') as f:
        return json.load(f)

def save_user_data(data):
    with open(USER_DATA_FILE, 'w') as f:
        json.dump(data, f, indent=4)

# === Fonction de traduction ===

def translate_text(text: str) -> str:
    if not text or len(text.strip()) == 0:
        return ""
    
    try:
        translated = translator.translate(text)
        return translated
    except Exception as e:
        print(f"❌ Erreur de traduction : {e}")
        return text

# === Fonctions d'interface ===

async def send_anime_card(update, context, anime):
    # Image
    image_url = anime.get('images', {}).get('jpg', {}).get('large_image_url', None)
    
    # Traduction des champs
    title = anime.get('title', 'Inconnu')
    year = anime.get('year', '?')
    score = anime.get('score', '?')
    episodes = anime.get('episodes', '?')
    status = anime.get('status', '?')
    genres = [g['name'] for g in anime.get('genres', [])]
    synopsis = translate_text(anime.get('synopsis', 'Aucun synopsis disponible.'))
    
    # Studios
    studios = [s['name'] for s in anime.get('studios', [])]
    studio_text = translate_text(', '.join(studios)) if studios else 'Inconnu'

    # Texte formaté
    text = (
        f"🎬 *{title}*\n"
        f"📅 Année : {year}\n"
        f"⭐ Note : {score}/10\n"
        f"📺 Épisodes : {episodes}\n"
        f"⏳ Statut : {status}\n"
        f"🎭 Genres : {', '.join(genres)}\n"
        f"🏢 Studio : {studio_text}"
    )

    buttons = [
        [InlineKeyboardButton("📖 Synopsis", callback_data=f"synopsis_{anime['mal_id']}")],
        [InlineKeyboardButton("🎥 Trailer", callback_data=f"trailer_{anime['mal_id']}")],
        [InlineKeyboardButton("👥 Personnages", callback_data=f"characters_{anime['mal_id']}")],
        [InlineKeyboardButton("🎯 Similaires", callback_data=f"similar_{anime['mal_id']}")],
        [InlineKeyboardButton("🌐 Streaming", callback_data=f"streaming_{anime['mal_id']}")],
        [InlineKeyboardButton("❤️ Favoris", callback_data=f"fav_{anime['mal_id']}_{title}")]
    ]

    if isinstance(update, Update):
        message = update.message
    else:
        message = update

    if image_url:
        await message.reply_photo(
            photo=image_url,
            caption=text,
            reply_markup=InlineKeyboardMarkup(buttons),
            parse_mode="Markdown"
        )
    else:
        await message.reply_text(text, reply_markup=InlineKeyboardMarkup(buttons), parse_mode="Markdown")

# === Gestion des favoris ===

async def add_favorite_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = str(query.from_user.id)
    data_parts = query.data.split('_')
    anime_id = data_parts[1]
    anime_title = '_'.join(data_parts[2:])  # Gérer les titres avec espaces
    
    # Charger les données utilisateur
    user_data = load_user_data()
    
    # Initialiser la structure si elle n'existe pas
    if user_id not in user_data:
        user_data[user_id] = {
            'favorites': [],
            'watchlist': [],
            'completed': [],
            'dropped': [],
            'custom_lists': {}
        }
    
    # Ajouter aux favoris si pas déjà présent
    if anime_title not in user_data[user_id]['favorites']:
        user_data[user_id]['favorites'].append(anime_title)
        save_user_data(user_data)
        await query.answer("✅ Ajouté aux favoris !")
    else:
        await query.answer("⚠️ Déjà dans les favoris.")

# === Commandes principales ===

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "👋 Bonjour ! Je suis votre assistant pour découvrir des animes.\n\n"
        "✨ Fonctionnalités :\n"
        "• 🔍 Recherche d'animes avec navigation interactive\n"
        "• 📝 Synopsis détaillés et traduits\n"
        "• 🎬 Liens vers les trailers officiels\n"
        "• 🎯 Recommandations d'animes similaires\n"
        "• 📅 Recherche par saison\n"
        "• 👤 Recherche de personnages\n"
        "• 🏆 Top animes\n"
        "• 🎲 Anime aléatoire\n"
        "• 📅 Planning des sorties (journalier)\n"
        "• ❤️ Système de favoris\n"
        "• 👥 Fonctionne dans les groupes et en privé\n\n"
        "📜 Utilise /help pour voir toutes les commandes !"
    )
    await update.message.reply_text(text)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "🤖 <b>Aide - Bot Anime</b>\n\n"
        "🔍 <b>Recherche d'animes />\b>\n"
        "• <code>/anime <nom></code>\n\n"
        "📅 <b>Recherche par saison />\b>\n"
        "• <code>/saison <année> <saison></code> (spring, summer, fall, winter)\n"
        "• ex : <code>/saison 2023 fall</code>\n\n"
        "👤 <b>Recherche de personnages />\b>\n"
        "• <code>/personnage <nom></code>\n"
        "• ex : <code>/personnage Naruto</code>\n\n"
        "🏆 <b>Top animes />\b>\n"
        "• <code>/top</code> - Liste des meilleurs animes du moments\n\n"
        "🎲 <b>Anime aléatoire />\b>\n"
        "• <code>/random</code> - Découvrir un anime au hasard\n\n"
        "📅 <b>Planning des sorties />\b>\n"
        "• <code>/planing</code> - Voir les sorties de la semaine\n"
        "• Cliquez sur un jour pour voir les animes du jour\n\n"
        "👤 <b>Profil utilisateur />\b>\n"
        "• <code>/profil</code> - Gérer vos listes et voir vos stats\n\n"
        "❤️ <b>Favoris />\b>\n"
        "• Cliquez sur le bouton ❤️ Favoris sur une fiche anime\n"
        "• Consultez vos favoris via /profil\n\n"
        "🎯 <b>Navigation interactive />\b>\n"
        "• Synopsis, Détails, Studio, Trailer, Personnages, Similaires, Streaming\n"
        "👥 <b>Groupes />\b>\n"
        "• Mentionne-moi puis écris le nom de l'anime"
    )
    await update.message.reply_text(help_text, parse_mode="HTML")

async def anime_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = ' '.join(context.args)
    if not query:
        await update.message.reply_text("🔎 Veuillez entrer un nom d'anime à rechercher.\nExemple : /anime Naruto")
        return

    try:
        response = requests.get(f"{JIKAN_API}/anime", params={"q": query})
        data = response.json()

        if not data.get("data"):
            await update.message.reply_text("🚫 Aucun anime trouvé.")
            return

        anime = data["data"][0]
        await send_anime_card(update, context, anime)
    except Exception as e:
        print(f"❌ Erreur lors de la recherche : {e}")
        await update.message.reply_text("❌ Erreur lors de la recherche. Veuillez réessayer plus tard.")

async def saison_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 2:
        await update.message.reply_text("📅 Format : /saison <année> <saison>\nExemple : /saison 2023 fall")
        return

    year = context.args[0]
    season = context.args[1].lower()
    
    valid_seasons = ['spring', 'summer', 'fall', 'winter']
    if season not in valid_seasons:
        await update.message.reply_text("📅 Saisons valides : spring, summer, fall, winter")
        return

    try:
        response = requests.get(f"{JIKAN_API}/seasons/{year}/{season}")
        data = response.json()

        animes = data.get('data', [])[:10]  # Top 10
        
        if not animes:
            await update.message.reply_text("🚫 Aucun anime trouvé pour cette saison.")
            return

        text = f"📅 *Animes de {season.capitalize()} {year}* :\n\n"
        for i, anime in enumerate(animes, 1):
            title = translate_text(anime.get('title', 'Inconnu'))
            score = anime.get('score', '?')
            text += f"{i}. *{title}* (⭐ {score})\n"
        
        await update.message.reply_text(text, parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text("❌ Erreur lors de la recherche par saison.")

async def personnage_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = ' '.join(context.args)
    if not query:
        await update.message.reply_text("👤 Veuillez entrer un nom de personnage à rechercher.\nExemple : /personnage Naruto")
        return

    try:
        response = requests.get(f"{JIKAN_API}/characters", params={"q": query})
        data = response.json()

        if not data.get("data"):
            await update.message.reply_text("🚫 Aucun personnage trouvé.")
            return

        character = data["data"][0]
        await send_character_card(update, context, character)
    except Exception as e:
        await update.message.reply_text("❌ Erreur lors de la recherche de personnage.")

async def top_animes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        response = requests.get(f"{JIKAN_API}/top/anime")
        data = response.json()
        animes = data.get('data', [])[:10]
        
        if not animes:
            await update.message.reply_text("🚫 Impossible de récupérer le top des animes.")
            return

        text = "🏆 *Top 10 des Animes* :\n\n"
        for i, anime in enumerate(animes, 1):
            title = translate_text(anime.get('title', 'Inconnu'))
            score = anime.get('score', '?')
            text += f"{i}. *{title}* (⭐ {score})\n"
        
        await update.message.reply_text(text, parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text("❌ Erreur lors de la récupération du top.")

async def random_anime(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        response = requests.get(f"{JIKAN_API}/random/anime")
        data = response.json()
        anime = data.get('data', {})
        if not anime:
            await update.message.reply_text("❌ Erreur lors de la sélection aléatoire.")
            return
        await send_anime_card(update, context, anime)
    except Exception as e:
        await update.message.reply_text("❌ Erreur lors de la sélection aléatoire.")

# === Planning Journalier ===

async def planing_sorties(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        # Récupérer les sorties de la semaine
        response = requests.get(f"{JIKAN_API}/schedules")
        data = response.json()
        schedules = data.get('data', [])

        # Organiser par jour de la semaine
        days = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]
        day_map = {
            "Monday": "Lundi",
            "Tuesday": "Mardi",
            "Wednesday": "Mercredi",
            "Thursday": "Jeudi",
            "Friday": "Vendredi",
            "Saturday": "Samedi",
            "Sunday": "Dimanche"
        }

        daily_animes = {day: [] for day in days}
        for schedule in schedules:
            day_name = schedule.get('broadcast', {}).get('day', 'Unknown')
            day_fr = day_map.get(day_name, "Inconnu")
            if day_fr != "Inconnu":
                daily_animes[day_fr].append(schedule)

        # Boutons pour chaque jour
        buttons = []
        for day in days:
            if daily_animes[day]:
                buttons.append([InlineKeyboardButton(day, callback_data=f"day_{day}")])
            else:
                buttons.append([InlineKeyboardButton(day, callback_data="none")])

        keyboard = InlineKeyboardMarkup(buttons)
        await update.message.reply_text("📅 *Sorties de la semaine*\n\nCliquez sur un jour pour voir les animes du jour.", reply_markup=keyboard)
    except Exception as e:
        print(f"❌ Erreur lors de la récupération du planning : {e}")
        await update.message.reply_text("❌ Erreur lors de la récupération du planning.")

async def day_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    day_name = query.data.split('_')[1]

    try:
        response = requests.get(f"{JIKAN_API}/schedules")
        data = response.json()
        schedules = data.get('data', [])
        
        # Filtrer les animes du jour
        day_map = {
            "Monday": "Lundi",
            "Tuesday": "Mardi",
            "Wednesday": "Mercredi",
            "Thursday": "Jeudi",
            "Friday": "Vendredi",
            "Saturday": "Samedi",
            "Sunday": "Dimanche"
        }
        reverse_map = {v: k for k, v in day_map.items()}
        day_en = reverse_map.get(day_name, "Unknown")

        animes_day = []
        for schedule in schedules:
            broadcast_day = schedule.get('broadcast', {}).get('day', 'Unknown')
            if broadcast_day == day_en:
                title = translate_text(schedule.get('title', 'Inconnu'))
                time = schedule.get('broadcast', {}).get('time', 'Heure inconnue')
                animes_day.append(f"• *{title}* ⏰ {time}")

        if animes_day:
            text = f"📅 *Sorties du {day_name}*\n\n" + "\n".join(animes_day)
            await query.edit_message_text(text, parse_mode="Markdown")
        else:
            await query.edit_message_text(f"📅 Aucune sortie prévue pour le {day_name}.")
    except Exception as e:
        await query.edit_message_text("❌ Erreur lors de la récupération des sorties.")

# === Profil utilisateur ===

async def profil_utilisateur(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    user_data = load_user_data()
    user = user_data.get(user_id, {})
    
    favorites = user.get('favorites', [])
    watchlist = user.get('watchlist', [])
    completed = user.get('completed', [])
    dropped = user.get('dropped', [])
    
    text = "👤 *Votre Profil*\n\n"
    text += f"❤️ *Favoris* ({len(favorites)}):\n"
    for fav in favorites[:5]:
        text += f"• {fav}\n"
    if len(favorites) > 5:
        text += f"... et {len(favorites) - 5} de plus\n\n"
    else:
        text += "\n"

    text += f"📋 *À regarder* ({len(watchlist)}):\n"
    for item in watchlist[:5]:
        text += f"• {item}\n"
    if len(watchlist) > 5:
        text += f"... et {len(watchlist) - 5} de plus\n\n"
    else:
        text += "\n"

    text += f"✅ *Terminés* ({len(completed)}):\n"
    for item in completed[:5]:
        text += f"• {item}\n"
    if len(completed) > 5:
        text += f"... et {len(completed) - 5} de plus\n\n"
    else:
        text += "\n"

    text += f"❌ *Abandonnés* ({len(dropped)}):\n"
    for item in dropped[:5]:
        text += f"• {item}\n"
    if len(dropped) > 5:
        text += f"... et {len(dropped) - 5} de plus"
    else:
        text += ""

    await update.message.reply_text(text, parse_mode="Markdown")

# === Callbacks ===

async def anime_detail(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    anime_id = query.data.split('_')[1]

    try:
        response = requests.get(f"{JIKAN_API}/anime/{anime_id}")
        data = response.json()
        anime = data.get('data', {})
        if not anime:
            await query.edit_message_text("🚫 Anime introuvable.")
            return
        await send_anime_card(query, context, anime)
    except Exception as e:
        await query.edit_message_text("❌ Erreur lors de la récupération de l'anime.")

async def synopsis_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    anime_id = query.data.split('_')[1]
    try:
        response = requests.get(f"{JIKAN_API}/anime/{anime_id}")
        data = response.json()
        anime = data.get('data', {})
        if not anime:
            await query.edit_message_text("🚫 Anime introuvable.")
            return
        synopsis = translate_text(anime.get('synopsis', 'Aucun synopsis disponible.'))
        text = f"📖 *Synopsis de {anime['title']}* :\n\n{synopsis}"
        await query.edit_message_text(text, parse_mode="Markdown")
    except Exception as e:
        await query.edit_message_text("❌ Erreur lors de la récupération du synopsis.")

async def trailer_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    anime_id = query.data.split('_')[1]
    try:
        response = requests.get(f"{JIKAN_API}/anime/{anime_id}")
        data = response.json()
        anime = data.get('data', {})
        if not anime:
            await query.edit_message_text("🚫 Anime introuvable.")
            return
        trailer = anime.get('trailer', {}).get('url', '#')
        if trailer != '#':
            await query.edit_message_text(f"🎥 [Trailer officiel]({trailer})", parse_mode="Markdown")
        else:
            await query.edit_message_text("⚠️ Aucun trailer disponible.")
    except Exception as e:
        await query.edit_message_text("❌ Erreur lors de la récupération du trailer.")

# === Main ===

def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()

    # Commandes
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("anime", anime_search))
    app.add_handler(CommandHandler("recherche", anime_search))
    app.add_handler(CommandHandler("saison", saison_search))
    app.add_handler(CommandHandler("personnage", personnage_search))
    app.add_handler(CommandHandler("top", top_animes))
    app.add_handler(CommandHandler("random", random_anime))
    app.add_handler(CommandHandler("planing", planing_sorties))
    app.add_handler(CommandHandler("profil", profil_utilisateur))

    # Callbacks
    app.add_handler(CallbackQueryHandler(anime_detail, pattern="^anime_"))
    app.add_handler(CallbackQueryHandler(synopsis_handler, pattern="^synopsis_"))
    app.add_handler(CallbackQueryHandler(trailer_handler, pattern="^trailer_"))
    app.add_handler(CallbackQueryHandler(add_favorite_callback, pattern="^fav_"))
    app.add_handler(CallbackQueryHandler(planing_sorties, pattern="^planing$"))
    app.add_handler(CallbackQueryHandler(day_handler, pattern="^day_"))

    print("🤖 Bot démarré...")
    app.run_polling()

if __name__ == '__main__':
    main()