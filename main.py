import requests
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from datetime import datetime
import os
from dotenv import load_dotenv

# بارگذاری .env
load_dotenv()

CMC_API_KEY = os.getenv("CMC_API_KEY")
CRYPTO_RANK_API_KEY = os.getenv("CRYPTO_RANK_API_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
APIFY_API_KEY = os.getenv("APIFY_API_KEY")

WELCOME_MESSAGE = """
سلام! 🤖 به ربات تحلیل هوشمند کوین خوش اومدی!

این ربات با استفاده از داده‌های معتبر از منابع زیر بهت کمک می‌کنه تا:
🔍 توکن‌هایی رو پیدا کنی که:
  • هنوز لیست نشده‌اند
  • وایت‌پیپر و رودمپ دارند
  • قیمت اولیه و ریسک پایین دارند
  • پتانسیل سود بالایی در آینده دارند

📊 منابع داده ما:
1️⃣ CoinMarketCap
2️⃣ CryptoRank
3️⃣ ICO Drops (تحلیل ویژه)
4️⃣ Token Unlocks
5️⃣ Dextools

📌 دستورات:
/start – معرفی ربات
/smart – تحلیل حرفه‌ای و پیشنهاد کوین‌های با پتانسیل
/check <نام کوین> – بررسی دقیق یک کوین خاص
"""

def get_cmc_data():
    url = 'https://pro-api.coinmarketcap.com/v1/cryptocurrency/listings/latest'
    headers = {'Accepts': 'application/json', 'X-CMC_PRO_API_KEY': CMC_API_KEY}
    params = {'start': '1', 'limit': '100', 'convert': 'USD'}
    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        return response.json()['data']
    except:
        return None

def get_cryptorank_data():
    url = 'https://api.cryptorank.io/v1/icos'
    headers = {'Authorization': f'Bearer {CRYPTO_RANK_API_KEY}'}
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.json()['data']
    except:
        return []

def analyze_with_gemini(project_name):
    url = 'https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-latest:generateContent'
    headers = {'Content-Type': 'application/json', 'x-goog-api-key': GEMINI_API_KEY}
    prompt = (
        f"Collect detailed information about the cryptocurrency project {project_name} from ICO Drops, Token Unlocks, Dextools. "
        f"Include whitepaper, roadmap, presale details, ROI, risk, exchanges, unlock schedule."
    )
    data = {'contents': [{'parts': [{'text': prompt}]}]}
    try:
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        result = response.json().get('candidates', [{}])[0].get('content', {}).get('parts', [{}])[0].get('text', '')
        return result[:1000]
    except:
        return "اطلاعاتی در دسترس نیست."

def filter_coins(coins, cryptorank_data):
    filtered_coins = []
    for coin in coins:
        price = coin.get('quote', {}).get('USD', {}).get('price', 0)
        volume_24h = coin.get('quote', {}).get('USD', {}).get('volume_24h', 0)
        percent_change_7d = coin.get('quote', {}).get('USD', {}).get('percent_change_7d', 0)
        if price < 1.0 and volume_24h > 100000 and abs(percent_change_7d) < 5:
            match = next((ico for ico in cryptorank_data if ico.get('name') == coin.get('name')), None)
            if match:
                gemini_analysis = analyze_with_gemini(coin.get('name'))
                filtered_coins.append({
                    'name': coin.get('name'),
                    'symbol': coin.get('symbol'),
                    'price': price,
                    'ico_start': match.get('startDate', 'Unknown'),
                    'ico_end': match.get('endDate', 'Unknown'),
                    'description': match.get('description', 'Unknown'),
                    'gemini_analysis': gemini_analysis
                })
    return filtered_coins

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(WELCOME_MESSAGE)

async def smart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cmc_coins = get_cmc_data()
    cryptorank_data = get_cryptorank_data()
    if not cmc_coins:
        await update.message.reply_text("خطا در اتصال به CoinMarketCap.")
        return
    filtered_coins = filter_coins(cmc_coins, cryptorank_data)
    if not filtered_coins:
        await update.message.reply_text("هیچ کوینی با شرایط مناسب پیدا نشد.")
        return

    msg = "📈 گزارش تحلیل کوین‌ها

"
    for coin in filtered_coins[:3]:
        msg += f"""📅 {datetime.now().strftime('%Y-%m-%d')}
🪙 {coin['name']} ({coin['symbol']})
💬 توضیح: {coin['description']}
💸 قیمت Presale: ${coin['price']:.4f}
📆 ICO: {coin['ico_start']} تا {coin['ico_end']}
🧠 تحلیل Gemini:
{coin['gemini_analysis']}

"""
    await update.message.reply_text(msg)

async def check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = ' '.join(context.args)
    if not name:
        await update.message.reply_text("لطفاً نام کوین را وارد کنید: /check <نام>")
        return
    result = analyze_with_gemini(name)
    await update.message.reply_text(f"📈 تحلیل برای {name}:

{result}")

def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("smart", smart))
    app.add_handler(CommandHandler("check", check))
    app.run_polling()

if __name__ == "__main__":
    main()
