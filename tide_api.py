# tide_api.py
import os
import requests


def get_tide_data(date_str: str):
    # 從環境變數讀取 API 金鑰
    TIDE_API_KEY = os.environ.get("TIDE_API_KEY")
    url = "https://opendata.cwa.gov.tw/api/v1/rest/datastore/F-A0021-001"
    params = {
        "Authorization": TIDE_API_KEY,
        "limit": "1",
        "format": "JSON",
        # 設定地點 ID 與指定日期
        "LocationId": "65000260",
        "Date": date_str
    }
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
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

                    message = f"日期：{date}\n農曆：{lunar_date}\n潮汐範圍：{tide_range}\n各時段潮汐資訊：\n"
                    for tide in tide_times:
                        tide_time = tide.get("DateTime")
                        tide_type = tide.get("Tide")
                        heights = tide.get("TideHeights", {})
                        message += f"  時間：{tide_time} - {tide_type}\n"
                        message += f"    潮高資訊：{heights}\n"
                    return message
                else:
                    return "無法取得當日潮汐資料"
            else:
                return "無法取得潮汐預報資料"
        else:
            return "API 回傳狀態失敗"
    except Exception as e:
        return f"發生錯誤：{e}"
