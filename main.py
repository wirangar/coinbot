import requests
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from datetime import datetime
import os
from dotenv import load_dotenv

# بارگذاری متغیرهای محیطی
load_dotenv()

CMC_API_KEY = os.getenv('CMC_API_KEY')
CRYPTO_RANK_API_KEY = os.getenv('CRYPTO_RANK_API_KEY')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
APIFY_API_KEY = os.getenv('APIFY_API_KEY')

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

def get_icodrops_data():
    url = 'https://api.apify.com/v2/acts/apify/web-scraper/run-sync-get-dataset-items'
    headers = {'Authorization': f'Bearer {APIFY_API_KEY}', 'Content-Type': 'application/json'}
    data = {
        "startUrls": [{"url": "https://icodrops.com/category/upcoming-ico/"}],
        "pageFunction": """
            async function pageFunction(context) {
                const { $ } = context;
                const data = [];
                $('.ico-card').each((index, element) => {
                    const name = $(element).find('.ico-name').text().trim();
                    const status = $(element).find('.ico-status').text().trim();
                    const startDate = $(element).find('.ico-start-date').text().trim();
                    const endDate = $(element).find('.ico-end-date').text().trim();
                    const description = $(element).find('.ico-description').text().trim();
                    data.push({ name, status, startDate, endDate, description });
                });
                return data;
            }
        """
    }
    try:
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        return response.json()
    except:
        return []

def analyze_with_gemini(project_name):
    url = 'https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-latest:generateContent'
    headers = {'Content-Type': 'application/json', 'x-goog-api-key': GEMINI_API_KEY}
    prompt = (
        f"Collect detailed information about the cryptocurrency project {project_name} from ICO Drops, Token Unlocks, Dextools."
"
        f"Provide:
"
        f"- Whitepaper link or summary
"
        f"- Roadmap details
"
        f"- Launchpad or presale details
"
        f"- Estimated ROI potential
"
        f"- Risk level (1-5) and reasons
"
        f"- Expected exchanges for listing
"
        f"- Token unlock schedule (if available)
"
        f"- Any relevant links"
    )
    data = {'contents': [{'parts': [{'text': prompt}]}]}
    try:
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        return response.json().get('candidates', [{}])[0].get('content', {}).get('parts', [{}])[0].get('text', '')
    except:
        return "اطلاعاتی یافت نشد."

def filter_coins(coins, cryptorank_data, icodrops_data):
    filtered_coins = []
    for coin in coins:
        price = coin.get('quote', {}).get('USD', {}).get('price', 0)
        volume_24h = coin.get('quote', {}).get('USD', {}).get('volume_24h', 0)
        percent_change_7d = coin.get('quote', {}).get('USD', {}).get('percent_change_7d', 0)

        if price < 1.0 and volume_24h > 100000 and abs(percent_change_7d) < 5:
            ico_match = next((ico for ico in cryptorank_data if ico.get('name') == coin.get('name')), None)
            icodrops_match = next((ico for ico in icodrops_data if ico.get('name') == coin.get('name')), None)
            if ico_match or icodrops_match:
                gemini_analysis = analyze_with_gemini(coin.get('name'))
                filtered_coins.append({
                    'name': coin['name'],
                    'symbol': coin['symbol'],
                    'price': price,
                    'ico_status': ico_match.get('status', icodrops_match.get('status', 'Unknown') if icodrops_match else 'Unknown'),
                    'ico_start': ico_match.get('startDate', icodrops_match.get('startDate', 'Unknown') if icodrops_match else 'Unknown'),
                    'ico_end': ico_match.get('endDate', icodrops_match.get('endDate', 'Unknown') if icodrops_match else 'Unknown'),
                    'description': icodrops_match.get('description', 'Unknown') if icodrops_match else 'Unknown',
                    'gemini_analysis': gemini_analysis
                })
    return filtered_coins

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(WELCOME_MESSAGE)

async def smart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cmc_data = get_cmc_data()
    cryptorank = get_cryptorank_data()
    icodrops = get_icodrops_data()

    if not cmc_data:
        await update.message.reply_text("❌ خطا در دریافت داده‌ها از CoinMarketCap.")
        return

    result = filter_coins(cmc_data, cryptorank, icodrops)
    if not result:
        await update.message.reply_text("هیچ کوینی با ویژگی‌های درخواستی پیدا نشد.")
        return

    for coin in result[:3]:
        lines = coin['gemini_analysis'].split('\n')
        msg = f"""📈 گزارش تحلیل کوین

📅 تاریخ تحلیل: {datetime.now().strftime('%Y-%m-%d')}
🪙 نام کوین: {coin['name']} ({coin['symbol']})
💬 توضیح: {coin['description']}
📄 Whitepaper: {next((l for l in lines if 'Whitepaper' in l), 'Unknown')}
🗺 Roadmap: {next((l for l in lines if 'Roadmap' in l), 'Unknown')}
🔐 Launchpad: {next((l for l in lines if 'Launchpad' in l), 'Unknown')}
📆 تاریخ ICO: {coin['ico_start']} تا {coin['ico_end']}
💸 قیمت Presale: ${coin['price']:.4f}
💰 سرمایه جذب‌شده: Unknown
🎯 ROI تخمینی: {next((l for l in lines if 'ROI' in l), 'Unknown')}
📉 سطح ریسک: {next((l for l in lines if 'Risk' in l), 'Unknown')}
🧠 توضیح ریسک: Unknown
🏷 صرافی‌های هدف: {next((l for l in lines if 'exchange' in l.lower()), 'Unknown')}
🔗 لینک منبع: {next((l for l in lines if 'link' in l.lower()), 'Unknown')}
📅 برنامه باز شدن توکن‌ها: {next((l for l in lines if 'unlock' in l.lower()), 'Unknown')}
"""
        await update.message.reply_text(msg)

async def check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    coin_name = ' '.join(context.args).strip()
    if not coin_name:
        await update.message.reply_text("لطفاً نام کوین رو وارد کن: /check <نام کوین>")
        return
    analysis = analyze_with_gemini(coin_name)
    await update.message.reply_text(f"📊 تحلیل برای {coin_name}:

{analysis}")

def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("smart", smart))
    app.add_handler(CommandHandler("check", check))
    app.run_webhook(
        listen="0.0.0.0",
        port=8080,
        url_path=TELEGRAM_TOKEN,
        webhook_url=f"https://wirangarcoinbot-406993416911.europe-west1.run.app/{TELEGRAM_TOKEN}"
    )

if __name__ == "__main__":
    main()
