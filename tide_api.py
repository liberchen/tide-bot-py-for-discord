# tide_api.py
import os
import requests
import logging


def get_tide_data(date_str: str, location_id: str) -> str:
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
                    date = daily_record.get("Date")
                    lunar_date = daily_record.get("LunarDate")
                    tide_range = daily_record.get("TideRange")
                    tide_times = daily_record.get("Time", [])

                    message = f"日期：{date}\n農曆：{lunar_date}\n潮汐範圍：{tide_range}\n\n"
                    message += "各時段潮汐資訊：\n"
                    for tide in tide_times:
                        tide_time = tide.get("DateTime")
                        tide_type = tide.get("Tide")
                        heights = tide.get("TideHeights", {})
                        message += f"  時間：{tide_time} - {tide_type}\n"
                        message += f"    相對台灣高程系統 (AboveTWVD): {heights.get('AboveTWVD')}\n"
                        message += f"    相對當地平均海平面 (AboveLocalMSL): {heights.get('AboveLocalMSL')}\n"
                        message += f"    相對海圖 (AboveChartDatum): {heights.get('AboveChartDatum')}\n"
                    logging.debug("潮汐資料解析完成。")
                    return message
                else:
                    logging.warning("查無當日潮汐資料。")
                    return "無法取得當日潮汐資料"
            else:
                logging.warning("查無潮汐預報資料。")
                return "無法取得潮汐預報資料"
        else:
            logging.error("API 回傳狀態失敗。")
            return "API 回傳狀態失敗"
    except Exception as e:
        logging.error(f"API 請求發生錯誤：{e}")
        return f"發生錯誤：{e}"
