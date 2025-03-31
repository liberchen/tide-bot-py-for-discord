# bot.py
import os
import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime
import logging

from tide_api import get_tide_data
from locations import LOCATION_MAP

# 設定 logging（Heroku 可用 heroku logs --tail 查看）
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

# 讀取 Discord Token
DISCORD_TOKEN = os.environ.get("DISCORD_TOKEN")
if DISCORD_TOKEN:
    logging.debug("DISCORD_TOKEN 已成功載入。")
else:
    logging.error("DISCORD_TOKEN 尚未設定！")

# 建立 Bot (這裡使用 commands.Bot 方便後續擴充)
intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

# -------------------------------
# 互動選單實作
# -------------------------------

class CountySelect(discord.ui.Select):
    def __init__(self):
        # 從 LOCATION_MAP 取得所有縣市名稱
        options = [
            discord.SelectOption(label=county, value=county)
            for county in sorted(LOCATION_MAP.keys())
        ]
        super().__init__(placeholder="請選擇縣市", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        selected_county = self.values[0]
        logging.debug(f"使用者選擇縣市：{selected_county}")
        # 建立顯示地區的下拉選單
        view = RegionSelectView(selected_county)
        await interaction.response.edit_message(content=f"您選擇的縣市：**{selected_county}**\n請選擇地區：", view=view)

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
        # 由於 Option 的 label為地區名稱，可一併顯示給使用者
        selected_region = self.values[0]  # 不過 value 已是 location_id，因此要反查地區名稱
        # 反查選擇的地區名稱（在該縣市的 list 中搜尋）
        region_name = None
        for reg, loc in LOCATION_MAP[self.county]:
            if loc == location_id:
                region_name = reg
                break
        logging.debug(f"使用者在 {self.county} 選擇地區：{region_name} (Location ID: {location_id})")
        # 使用今日日期來查詢潮汐資訊
        today = datetime.now().strftime("%Y-%m-%d")
        tide_info = get_tide_data(today, location_id)
        # 回覆最終結果（可自行調整訊息格式）
        await interaction.response.edit_message(content=f"【{self.county} {region_name}】\n{tide_info}", view=None)

class RegionSelectView(discord.ui.View):
    def __init__(self, county: str):
        super().__init__(timeout=60)
        self.add_item(RegionSelect(county))

# -------------------------------
# Slash Command 註冊
# -------------------------------

@bot.tree.command(name="tide", description="取得台灣當日潮汐資訊")
async def tide(interaction: discord.Interaction):
    logging.debug("收到 /tide 指令，開始提示縣市選單。")
    await interaction.response.send_message("請選擇縣市：", view=CountySelectView(), ephemeral=True)

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
