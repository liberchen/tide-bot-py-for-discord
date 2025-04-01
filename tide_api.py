# tide_api.py
import os
import requests
import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import discord


def get_tide_data_by_date(date_str: str, location_id: str) -> tuple:
    """
    呼叫指定日期的潮汐資料 API，並回傳 tuple(field_name, table_string)
    若發生錯誤，則回傳 (error_message, None)
    """
    TIDE_API_KEY = os.environ.get("TIDE_API_KEY")
    if not TIDE_API_KEY:
        logging.error("TIDE_API_KEY 尚未設定！")
        return ("錯誤：API 金鑰未設定", None)

    url = "https://opendata.cwa.gov.tw/api/v1/rest/datastore/F-A0021-001"
    params = {
        "Authorization": TIDE_API_KEY,
        "format": "JSON",
        "LocationId": location_id,
        "Date": date_str  # 指定日期，回傳該日資料
    }
    logging.debug(f"呼叫 API（指定日期 {date_str}），參數：{params}")
    try:
        response = requests.get(url, params=params)
        logging.debug(f"HTTP 狀態碼：{response.status_code}")
        response.raise_for_status()
        data = response.json()
        logging.debug("成功取得 JSON 資料。")

        if data.get("success") != "true":
            logging.error("API 回傳狀態失敗。")
            return (f"{date_str} API 回傳狀態失敗", None)

        tide_forecasts = data.get("records", {}).get("TideForecasts", [])
        if not tide_forecasts:
            logging.warning("查無潮汐預報資料。")
            return (f"{date_str} 查無潮汐預報資料", None)

        location_info = tide_forecasts[0].get("Location", {})
        daily_list = location_info.get("TimePeriods", {}).get("Daily", [])
        if not daily_list:
            logging.warning(f"{date_str} 無當日資料。")
            return (f"{date_str} 無當日資料", None)

        daily_record = daily_list[0]
        lunar_date = daily_record.get("LunarDate", "未知")
        tide_range = daily_record.get("TideRange", "未知")
        tide_times = daily_record.get("Time", [])

        # 建立表格字串，欄位以直線 | 分隔，並調整分隔線長度
        header = "時間|狀態|高程|海平|海圖\n"
        separator = "----|---|---|---|----\n"
        rows = ""
        for tide in tide_times:
            dt_str = tide.get("DateTime")
            try:
                dt = datetime.fromisoformat(dt_str)
                time_formatted = dt.strftime("%H:%M")
            except Exception as e:
                logging.error(f"時間格式轉換失敗：{e}")
                time_formatted = dt_str
            tide_status = tide.get("Tide", "未知")
            heights = tide.get("TideHeights", {})
            val_twvd = heights.get("AboveTWVD", "N/A")
            val_local = heights.get("AboveLocalMSL", "N/A")
            val_chart = heights.get("AboveChartDatum", "N/A")
            row = f"{time_formatted}|{tide_status}|{val_twvd}|{val_local}|{val_chart}\n"
            rows += row

        table = "```" + header + separator + rows + "```"
        field_name = f"{date_str} (農曆 {lunar_date}) - 潮汐：{tide_range}"
        return (field_name, table)
    except Exception as e:
        logging.error(f"API 請求發生錯誤：{e}")
        return (f"{date_str} 發生錯誤：{e}", None)


def get_tide_data(location_id: str) -> discord.Embed:
    """
    呼叫 API 取得今天與明天的潮汐資料，並回傳一個 Discord Embed 物件。
    """
    taiwan_now = datetime.now(ZoneInfo("Asia/Taipei"))
    today_str = taiwan_now.strftime("%Y-%m-%d")
    tomorrow_str = (taiwan_now + timedelta(days=1)).strftime("%Y-%m-%d")

    # 分別取得今天與明天的潮汐資料
    field_today, table_today = get_tide_data_by_date(today_str, location_id)
    field_tomorrow, table_tomorrow = get_tide_data_by_date(tomorrow_str, location_id)

    embed_title = "潮汐預報"
    embed_desc = f"資料來源：中央氣象署\n顯示日期：{today_str} 與 {tomorrow_str}"
    embed = discord.Embed(title=embed_title, description=embed_desc, color=0x3498DB)

    if table_today:
        embed.add_field(name=field_today, value=table_today, inline=False)
    else:
        embed.add_field(name=field_today, value="查無資料或發生錯誤", inline=False)

    if table_tomorrow:
        embed.add_field(name=field_tomorrow, value=table_tomorrow, inline=False)
    else:
        embed.add_field(name=field_tomorrow, value="查無資料或發生錯誤", inline=False)

    return embed
