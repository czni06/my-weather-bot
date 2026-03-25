import requests, json, os
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, LocationMessage, TextSendMessage, ImageSendMessage
from datetime import datetime

# --- 1. 圖片網址設定 (請更換為你上傳後的真實網址) ---
IMG_URL_UNDERSTAND = "https://raw.githubusercontent.com/czni06/my-weather-bot/main/IMG_9805.jpeg"
IMG_URL_RAIN = "https://raw.githubusercontent.com/czni06/my-weather-bot/main/IMG_9803.jpeg"
IMG_URL_SUN = "https://raw.githubusercontent.com/czni06/my-weather-bot/main/IMG_9804.jpeg"
IMG_URL_FIGHT = "https://raw.githubusercontent.com/czni06/my-weather-bot/main/IMG_9806.jpeg"

# --- 2. 從環境變數讀取 Token (安全性更高) ---
CWA_TOKEN = os.getenv('CWA_TOKEN')
LINE_ACCESS_TOKEN = os.getenv('LINE_ACCESS_TOKEN')
LINE_SECRET = os.getenv('LINE_SECRET')
USER_ID = os.getenv('USER_ID')

line_bot_api = LineBotApi(LINE_ACCESS_TOKEN)
handler = WebhookHandler(LINE_SECRET)

app = Flask(__name__)
CONFIG_FILE = "user_config.json"

def save_config(city=None, alarm_time=None):
    config = load_config()
    if city: config['city'] = city
    if alarm_time: config['alarm_time'] = alarm_time
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False)

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except: pass
    return {"city": "臺北市", "alarm_time": "08:00"}

def get_weather_report(city):
    try:
        url = f"https://opendata.cwa.gov.tw/api/v1/rest/datastore/F-D0047-091?Authorization={CWA_TOKEN}&locationName={city}&elementName=PoP12h,T,ApparentT,UVI"
        res = requests.get(url).json()
        location_data = res['records']['locations'][0]['location'][0]
        elements = location_data['weatherElement']
        data = {e['elementName']: e['time'][0]['elementValue'][0]['value'] for e in elements}
        
        res_aqi = requests.get("https://data.moenv.gov.tw/api/v2/aqx_p_432?api_key=e8dd42e6-9b8b-43f8-991e-b3dee723a52d&limit=100&format=JSON").json()
        aqi_val, aqi_status = "--", "無資料"
        for item in res_aqi['records']:
            if item['county'] in city:
                aqi_val, aqi_status = item['aqi'], item['status']
                break

        pop = int(data.get('PoP12h', 0)) if data.get('PoP12h', '--') != '--' else 0
        uvi = float(data.get('UVI', 0)) if data.get('UVI', '--') != '--' else 0
        
        img_url = IMG_URL_FIGHT
        footer = "\n\n今天也要一起加油.ᐟ.ᐟ"
        
        if pop >= 40:
            img_url = IMG_URL_RAIN
            footer = ""
        elif uvi >= 7:
            img_url = IMG_URL_SUN
            footer = ""

        msg = (f"꩜早ㄢ 今日{city}預報꩜\n"
               f"氣溫｜{data.get('T', '--')} °C\n"
               f"紫外線｜{data.get('UVI', '--')}\n"
               f"體感溫度｜{data.get('ApparentT', '--')} °C\n"
               f"降雨機率｜{data.get('PoP12h', '--')}%\n"
               f"空氣品質｜{aqi_status} (AQI {aqi_val}){footer}")
        
        return msg, img_url
    except Exception as e:
        return f"解析出錯: {e}", IMG_URL_FIGHT

@app.route("/", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'

@handler.add(MessageEvent, message=LocationMessage)
def handle_location(event):
    city = event.message.address.replace('台', '臺')[0:3]
    save_config(city=city)
    msg, _ = get_weather_report(city)
    line_bot_api.reply_message(event.reply_token, [
        ImageSendMessage(original_content_url=IMG_URL_UNDERSTAND, preview_image_url=IMG_URL_UNDERSTAND),
        TextSendMessage(text=msg)
    ])

@handler.add(MessageEvent, message=TextMessage)
def handle_text(event):
    text = event.message.text.strip()
    if ":" in text and len(text) == 5:
        save_config(alarm_time=text)
        line_bot_api.reply_message(event.reply_token, [
            ImageSendMessage(original_content_url=IMG_URL_UNDERSTAND, preview_image_url=IMG_URL_UNDERSTAND),
            TextSendMessage(text=f"⏰ 已將每天通知時間設為：{text}")
        ])

@app.route("/push")
def push_check():
    config = load_config()
    # 這裡要注意：Render 伺服器通常是 UTC 時間，需確認時區或直接由 Cron-job 決定
    msg, img = get_weather_report(config['city'])
    line_bot_api.push_message(USER_ID, [
        ImageSendMessage(original_content_url=img, preview_image_url=img),
        TextSendMessage(text=msg)
    ])
    return "Pushed"

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
