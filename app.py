import os
import requests
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage

app = Flask(__name__)

# --- 設定區 ---
LINE_ACCESS_TOKEN = 'dODJN7rT6vZsVIcOFoG+ooevsrr50JZOlGIwaKEWsyyeIPltrF7LM/KzMaeHIRLuSVJV6wxhTeJ6+aSCJg0pdCzIyleE0HcMFZ00STCq5cs10+VbGPAPdLfSv9anbBoz9cG+ukKJ+Zu/0OJJIQAl9AdB04t89/1O/w1cDnyilFU='
LINE_CHANNEL_SECRET = '4df9b926d23fa388779a2df241e6eae5'
CWA_TOKEN = 'CWA-2FB735BD-9317-4210-A408-459EC9D86CDB'
USER_ID = 'Uda5b906e9c742d49258df979d1f849ca' # 推播必備
line_bot_api = LineBotApi(LINE_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)

@app.route("/", methods=['POST'])
def callback():
    # 取得 X-Line-Signature 標頭
    signature = request.headers.get('X-Line-Signature')

    # 如果沒簽章，代表這不是 LINE 傳來的，直接不理它
    if not signature:
        return 'OK', 200

    # 取得請求內容
    body = request.get_data(as_text=True)
    
    try:
        handler.handle(body, signature)
    except Exception as e:
        print(e)
        return 'Error', 400

    return 'OK', 200

# 氣象推播路由 (給 Cron-job 呼叫用)
@app.route("/alarm")
def morning_alarm():
    city = "臺北市" # 改成你的縣市
    url = f"https://opendata.cwa.gov.tw/api/v1/rest/datastore/F-C0032-001?Authorization={CWA_TOKEN}&locationName={city}"
    res = requests.get(url, verify=False).json()
    data = res['records']['location'][0]['weatherElement']
    wx = data[0]['time'][0]['parameter']['parameterName']
    pop = data[1]['time'][0]['parameter']['parameterName']
    min_t = data[2]['time'][0]['parameter']['parameterName']
    max_t = data[4]['time'][0]['parameter']['parameterName']
    
    msg = f"🔔 今日 {city} 預報\n☁️ 天氣：{wx}\n🌡️ 氣溫：{min_t}~{max_t}°C\n☔ 降雨：{pop}%"
    line_bot_api.push_message(USER_ID, TextSendMessage(text=msg))
    return "Sent!"

if __name__ == "__main__":
    app.run()
