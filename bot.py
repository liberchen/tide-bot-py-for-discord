# bot.py
import os
import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime
from zoneinfo import ZoneInfo
import logging

from tide_api import get_tide_data
from locations import LOCATION_MAP

# 設定 logging (Heroku 可用 heroku logs --tail 查看)
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

# 讀取環境變數
DISCORD_TOKEN = os.environ.get("DISCORD_TOKEN")
if DISCORD_TOKEN:
    logging.debug("DISCORD_TOKEN 已成功載入。")
else:
    logging.error("DISCORD_TOKEN 尚未設定！")

# 啟用 members 與 presences intents
intents = discord.Intents.default()
intents.members = True
intents.presences = True

# 建立 Bot (使用 commands.Bot 方便後續擴充)
bot = commands.Bot(command_prefix="!", intents=intents)

# 用來追蹤成員當天第一次上線
first_online_today = {}

# 定義簡單的關鍵字對應 (若成員顯示名稱中含有關鍵字，則視為該縣市)
# 注意：請確認對應值存在於 LOCATION_MAP 中
COUNTY_KEYWORDS = {
    "台北": "台北市",
    "新北": "新北市",
    "基隆": "基隆市",
    "桃園": "桃園市",
    "新竹": "新竹縣",
    "苗栗": "苗栗縣",
    "台中": "臺中市",
    "彰化": "彰化縣",
    "雲林": "雲林縣",
    "嘉義": "嘉義縣",
    "台南": "臺南市",
    "高雄": "高雄市",
    "屏東": "屏東縣",
    "台東": "臺東縣",
    "花蓮": "花蓮縣",
    "宜蘭": "宜蘭縣",
    "澎湖": "澎湖縣",
    "金門": "金門縣",
    "連江": "連江縣"
}


# -------------------------------
# 互動選單實作
# -------------------------------

class CountySelect(discord.ui.Select):
    def __init__(self):
        # 從 LOCATION_MAP 取得所有縣市名稱，並建立選項
        options = [
            discord.SelectOption(label=county, value=county)
            for county in sorted(LOCATION_MAP.keys())
        ]
        super().__init__(placeholder="請選擇縣市", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        selected_county = self.values[0]
        logging.debug(f"使用者選擇縣市：{selected_county}")
        view = RegionSelectView(selected_county)
        await interaction.response.edit_message(
            content=f"您選擇的縣市：**{selected_county}**\n請選擇地區：", view=view
        )


class CountySelectView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=60)
        self.add_item(CountySelect())


class RegionSelect(discord.ui.Select):
    def __init__(self, county: str):
        self.county = county
        # 從 LOCATION_MAP 取得該縣市的所有地區與對應的 Location ID
        region_list = LOCATION_MAP.get(county, [])
        options = [
            discord.SelectOption(label=region, value=loc_id)
            for region, loc_id in region_list
        ]
        super().__init__(placeholder="請選擇地區", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        location_id = self.values[0]
        # 反查選擇的地區名稱
        region_name = None
        for reg, loc in LOCATION_MAP[self.county]:
            if loc == location_id:
                region_name = reg
                break
        logging.debug(f"使用者在 {self.county} 選擇地區：{region_name} (Location ID: {location_id})")
        tide_embed = get_tide_data(location_id)
        await interaction.response.edit_message(
            content=f"【{self.county} {region_name}】", embed=tide_embed, view=None
        )


class RegionSelectView(discord.ui.View):
    def __init__(self, county: str):
        super().__init__(timeout=60)
        self.add_item(RegionSelect(county))


@bot.tree.command(name="tide", description="取得台灣今天與隔天的潮汐資訊")
async def tide(interaction: discord.Interaction):
    logging.debug("收到 /tide 指令，開始提示縣市選單。")
    await interaction.response.send_message("請選擇縣市：", view=CountySelectView(), ephemeral=True)


# -------------------------------
# 當成員首次上線時自動發送潮汐資訊
# -------------------------------
@bot.event
async def on_presence_update(before: discord.Member, after: discord.Member):
    # 檢查如果成員從離線或隱身變成線上
    if before.status != discord.Status.online and after.status == discord.Status.online:
        member = after
        # 取得台灣日期字串
        today_str = datetime.now(ZoneInfo("Asia/Taipei")).strftime("%Y-%m-%d")
        # 若該成員今日已發送過，則略過
        if first_online_today.get(member.id) == today_str:
            return
        # 更新該成員上線日期
        first_online_today[member.id] = today_str
        # 檢查成員的顯示名稱中是否包含任何縣市關鍵字
        display_name = member.display_name
        logging.debug(f"檢查成員 {member.id} 的顯示名稱：{display_name}")
        detected_county = None
        for keyword, county in COUNTY_KEYWORDS.items():
            if keyword in display_name:
                # 如果該縣市存在於 LOCATION_MAP中則使用之
                if county in LOCATION_MAP and LOCATION_MAP[county]:
                    detected_county = county
                    break
        if detected_county:
            logging.debug(f"從顯示名稱中偵測到縣市：{detected_county}")
            # 取該縣市的第一個地區作為預設 (也可依需求調整)
            default_region = LOCATION_MAP[detected_county][0]  # tuple (region, location_id)
            location_id = default_region[1]
            try:
                dm_channel = await member.create_dm()
                tide_embed = get_tide_data(location_id)
                await dm_channel.send(f"嗨，根據您的顯示名稱，推測您位於 {detected_county}，以下是該地潮汐預報：",
                                      embed=tide_embed)
                logging.debug(f"已向成員 {member.id} 發送自動潮汐資訊。")
            except Exception as e:
                logging.error(f"發送 DM 給成員 {member.id} 失敗：{e}")
        else:
            logging.debug(f"未從成員 {member.id} 的顯示名稱中偵測到縣市資訊。")


# -------------------------------
# Bot 啟動
# -------------------------------
@bot.event
async def on_ready():
    logging.debug(f"Bot 已登入：{bot.user}")
    try:
        synced = await bot.tree.sync()
        logging.debug(f"Slash Commands 已同步，共 {len(synced)} 個。")
    except Exception as e:
        logging.error(f"同步 Slash Commands 發生錯誤：{e}")


bot.run(DISCORD_TOKEN)
