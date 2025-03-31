# tide_api.py
import os
import requests
import logging
from datetime import datetime
from zoneinfo import ZoneInfo
import discord


def get_tide_data(date_str: str, location_id: str) -> discord.Embed:
    TIDE_API_KEY = os.environ.get("TIDE_API_KEY")
    if TIDE_API_KEY:
        logging.debug("TIDE_API_KEY 已成功載入。")
    else:
        logging.error("TIDE_API_KEY 尚未設定！")

    url = "https://opendata.cwa.gov.tw/api/v1/rest/datastore/F-A0021-001"
    params = {
        "Authorization": TIDE_API_KEY,
        "limit": "1",
        "format": "JSON",
        "LocationId": location_id,
        "Date": date_str
    }
    logging.debug(f"發送 API 請求，參數：{params}")
    try:
        response = requests.get(url, params=params)
        logging.debug(f"HTTP 狀態碼：{response.status_code}")
        response.raise_for_status()
        data = response.json()
        logging.debug("成功取得並解析 JSON 資料。")

        if data.get("success") == "true":
            records = data.get("records", {})
            tide_forecasts = records.get("TideForecasts", [])
            if tide_forecasts:
                location_info = tide_forecasts[0].get("Location", {})
                time_periods = location_info.get("TimePeriods", {})
                daily = time_periods.get("Daily", [])
                if daily:
                    daily_record = daily[0]
                    date_api = daily_record.get("Date")
                    lunar_date = daily_record.get("LunarDate")
                    tide_range = daily_record.get("TideRange")
                    tide_times = daily_record.get("Time", [])

                    # 建立 Embed 物件，並設定標題、描述與顏色（藍色）
                    title = f"潮汐預報 {date_api}"
                    description = f"農曆：{lunar_date}\n潮汐範圍：{tide_range}"
                    embed = discord.Embed(title=title, description=description, color=0x3498DB)

                    # 建立表格字串（使用 code block 模擬）
                    header = f"{'時間':<6} {'狀態':<8} {'台灣高程':<10} {'當地海平':<10} {'海圖':<8}\n"
                    separator = "-" * 45 + "\n"
                    rows = ""
                    for tide in tide_times:
                        dt_str = tide.get("DateTime")
                        try:
                            dt = datetime.fromisoformat(dt_str)
                            # 轉換成僅顯示「幾點幾分」
                            time_formatted = dt.strftime("%H:%M")
                        except Exception as e:
                            logging.error(f"時間格式轉換失敗：{e}")
                            time_formatted = dt_str
                        tide_status = tide.get("Tide")
                        heights = tide.get("TideHeights", {})
                        # 取得各項潮高數據
                        above_twvd = heights.get("AboveTWVD", "N/A")
                        above_local = heights.get("AboveLocalMSL", "N/A")
                        above_chart = heights.get("AboveChartDatum", "N/A")

                        # 建立一行資料
                        row = f"{time_formatted:<6} {tide_status:<8} {above_twvd:<10} {above_local:<10} {above_chart:<8}\n"
                        rows += row
                    table = "```" + header + separator + rows + "```"
                    embed.add_field(name="潮汐資訊", value=table, inline=False)

                    logging.debug("潮汐資料解析完成並建立 Embed。")
                    return embed
                else:
                    logging.warning("查無當日潮汐資料。")
                    return discord.Embed(title="錯誤", description="無法取得當日潮汐資料", color=0xE74C3C)
            else:
                logging.warning("查無潮汐預報資料。")
                return discord.Embed(title="錯誤", description="無法取得潮汐預報資料", color=0xE74C3C)
        else:
            logging.error("API 回傳狀態失敗。")
            return discord.Embed(title="錯誤", description="API 回傳狀態失敗", color=0xE74C3C)
    except Exception as e:
        logging.error(f"API 請求發生錯誤：{e}")
        return discord.Embed(title="錯誤", description=f"發生錯誤：{e}", color=0xE74C3C)
