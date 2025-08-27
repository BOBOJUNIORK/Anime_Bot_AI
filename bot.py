# bot.py
import json
import os
import random
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from jikanpy import Jikan
from deep_translator import GoogleTranslator
from config import TELEGRAM_TOKEN, JIKAN_API, SUPPORTED_LANGUAGES, DEFAULT_LANGUAGE

# Initialisation de Jikan
jikan = Jikan()

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
        # Ne pas traduire si c'est déjà en français
        translated = translator.translate(text)
        return translated
    except Exception as e:
        print(f"❌ Erreur de traduction : {e}")
        return text  # Retourne le texte original si erreur

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
        [InlineKeyboardButton("❤️ Favoris", callback_data=f"fav_{anime['mal_id']}")]
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

# === Commandes ===

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
        "• 📅 Planning des sorties\n"
        "• 👥 Fonctionne dans les groupes et en privé\n\n"
        "📜 Utilise /help pour voir toutes les commandes !"
    )
    await update.message.reply_text(text)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "🤖 <b>Aide - Bot Anime</b>\n\n"
        "🔍 <b>Recherche d'animes :</b>\n"
        "• <code>/anime <nom></code>\n\n"
        "📅 <b>Recherche par saison :</b>\n"
        "• <code>/saison <année> <saison></code> (spring, summer, fall, winter)\n"
        "• ex : <code>/saison 2023 fall</code>\n\n"
        "👤 <b>Recherche de personnages :</b>\n"
        "• <code>/personnage <nom></code>\n"
        "• ex : <code>/personnage Naruto</code>\n\n"
        "🏆 <b>Top animes :</b>\n"
        "• <code>/top</code> - Liste des meilleurs animes du moments\n\n"
        "🎲 <b>Anime aléatoire :</b>\n"
        "• <code>/random</code> - Découvrir un anime au hasard\n\n"
        "📅 <b>Planning des sorties :</b>\n"
        "• <code>/planing</code> - Voir les sorties de la semaine\n\n"
        "👤 <b>Profil utilisateur :</b>\n"
        "• <code>/profil</code> - Gérer vos listes et voir vos stats\n\n"
        "🎯 <b>Navigation interactive :</b>\n"
        "• Synopsis, Détails, Studio, Trailer, Personnages, Similaires, Streaming\n"
        "👥 <b>Groupes :</b>\n"
        "• Mentionne-moi puis écris le nom de l'anime"
    )
    await update.message.reply_text(help_text, parse_mode="HTML")

async def recherche(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = ' '.join(context.args)
    if not query:
        await update.message.reply_text("🔎 Veuillez entrer un nom d'anime à rechercher.")
        return

    try:
        response = jikan.search('anime', query)
        if not response['results']:
            await update.message.reply_text("🚫 Aucun anime trouvé.")
            return

        anime = response['results'][0]
        await send_anime_card(update, context, anime)
    except Exception as e:
        await update.message.reply_text("❌ Erreur lors de la recherche.")

async def anime_detail(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    anime_id = query.data.split('_')[1]

    try:
        anime = jikan.anime(anime_id)
        await send_anime_card(query, context, anime)
    except Exception as e:
        await query.edit_message_text("🚫 Anime introuvable.")

async def synopsis_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    anime_id = query.data.split('_')[1]
    try:
        anime = jikan.anime(anime_id)
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
        anime = jikan.anime(anime_id)
        trailer = anime.get('trailer', {}).get('url', '#')
        if trailer != '#':
            await query.edit_message_text(f"🎥 [Trailer officiel]({trailer})", parse_mode="Markdown")
        else:
            await query.edit_message_text("⚠️ Aucun trailer disponible.")
    except Exception as e:
        await query.edit_message_text("❌ Erreur lors de la récupération du trailer.")

# === Commandes manquantes (à implémenter) ===

async def top_animes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🏆 Top animes - Fonction en cours de développement...")

async def random_anime(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🎲 Anime aléatoire - Fonction en cours de développement...")

# === Main ===

def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()

    # Commandes
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("anime", recherche))
    app.add_handler(CommandHandler("recherche", recherche))
    app.add_handler(CommandHandler("top", top_animes))
    app.add_handler(CommandHandler("random", random_anime))

    # Callbacks
    app.add_handler(CallbackQueryHandler(anime_detail, pattern="^anime_"))
    app.add_handler(CallbackQueryHandler(synopsis_handler, pattern="^synopsis_"))
    app.add_handler(CallbackQueryHandler(trailer_handler, pattern="^trailer_"))

    print("🤖 Bot démarré...")
    app.run_polling()

if __name__ == '__main__':
    main()
