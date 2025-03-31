# tide_api.py
import os
import requests
import logging


def get_tide_data(date_str: str):
    # 讀取環境變數中的 API 金鑰
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
        "LocationId": "65000260",
        "Date": date_str
    }
    logging.debug("即將發送 API 請求...")
    logging.debug(f"API URL: {url}")
    logging.debug(f"API 請求參數: {params}")

    try:
        response = requests.get(url, params=params)
        logging.debug(f"HTTP 回應狀態碼：{response.status_code}")
        response.raise_for_status()
        logging.debug("HTTP 請求成功。")
        data = response.json()
        logging.debug("成功解析 JSON 回應資料：")
        logging.debug(data)

        if data.get("success") == "true":
            records = data.get("records", {})
            tide_forecasts = records.get("TideForecasts", [])
            if tide_forecasts:
                logging.debug("取得潮汐預報資料。")
                location_info = tide_forecasts[0].get("Location", {})
                time_periods = location_info.get("TimePeriods", {})
                daily = time_periods.get("Daily", [])
                if daily:
                    logging.debug("取得當日潮汐資料。")
                    daily_record = daily[0]
                    date = daily_record.get("Date")
                    lunar_date = daily_record.get("LunarDate")
                    tide_range = daily_record.get("TideRange")
                    tide_times = daily_record.get("Time", [])

                    message = f"日期：{date}\n農曆：{lunar_date}\n潮汐範圍：{tide_range}\n各時段潮汐資訊：\n"
                    for tide in tide_times:
                        tide_time = tide.get("DateTime")
                        tide_type = tide.get("Tide")
                        heights = tide.get("TideHeights", {})
                        message += f"  時間：{tide_time} - {tide_type}\n"
                        message += f"    潮高資訊：{heights}\n"
                    logging.debug("潮汐資料解析成功。")
                    return message
                else:
                    logging.warning("無法取得當日潮汐資料。")
                    return "無法取得當日潮汐資料"
            else:
                logging.warning("無法取得潮汐預報資料。")
                return "無法取得潮汐預報資料"
        else:
            logging.error("API 回傳狀態失敗，success 欄位非 'true'。")
            return "API 回傳狀態失敗"
    except Exception as e:
        logging.error(f"API 請求或資料解析發生錯誤：{e}")
        return f"發生錯誤：{e}"
