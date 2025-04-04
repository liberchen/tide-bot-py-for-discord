import os
import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime
from zoneinfo import ZoneInfo
import logging
import asyncio

from tide_api import get_tide_data_for_county
from locations import LOCATION_MAP

# 設定 logging (Heroku 可用 heroku logs --tail 查看)
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

# 讀取環境變數
DISCORD_TOKEN = os.environ.get("DISCORD_TOKEN")
if DISCORD_TOKEN:
    logging.debug("DISCORD_TOKEN 已成功載入。")
else:
    logging.error("DISCORD_TOKEN 尚未設定！")

# 讀取自動提醒開關 (預設為 false)
AUTO_REMINDER_ENABLED = os.environ.get("AUTO_REMINDER_ENABLED", "false").lower() == "true"
logging.debug(f"AUTO_REMINDER_ENABLED 設定：{AUTO_REMINDER_ENABLED}")

# 讀取提醒頻道名稱 (為字串)
REMINDER_CHANNEL_NAME = os.environ.get("REMINDER_CHANNEL")
if REMINDER_CHANNEL_NAME:
    logging.debug(f"自動提醒頻道設定：{REMINDER_CHANNEL_NAME}")
else:
    logging.debug("未設定自動提醒頻道，將使用 DM 傳送提醒訊息。")

# 啟用 members 與 presences intents
intents = discord.Intents.default()
intents.members = True
intents.presences = True

# 建立 Bot (使用 commands.Bot 方便後續擴充)
bot = commands.Bot(command_prefix="!", intents=intents)

# 用來追蹤成員當天第一次上線
first_online_today = {}

# 定義縣市關鍵字對應 (若成員顯示名稱中包含關鍵字則視為該縣市)
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
# 互動選單：提供縣市選擇，選擇後顯示該縣市所有區的潮汐資訊
# -------------------------------
class CountySelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label=county, value=county)
            for county in sorted(LOCATION_MAP.keys())
        ]
        super().__init__(placeholder="請選擇縣市", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        selected_county = self.values[0]
        logging.debug(f"使用者選擇縣市：{selected_county}")
        tide_embed = get_tide_data_for_county(selected_county)
        await interaction.response.edit_message(
            content=f"【{selected_county}】的潮汐預報：", embed=tide_embed, view=None
        )

class CountySelectView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=60)
        self.add_item(CountySelect())

@bot.tree.command(name="tide", description="取得台灣今天與隔天所有區的潮汐資訊")
async def tide(interaction: discord.Interaction):
    logging.debug("收到 /tide 指令，開始提示縣市選單。")
    await interaction.response.send_message("請選擇縣市：", view=CountySelectView(), ephemeral=True)

# -------------------------------
# 新增 /mytide 指令：根據使用者顯示名稱自動取得所在縣市的潮汐預報
# -------------------------------
@bot.tree.command(name="mytide", description="取得您所在縣市的潮汐預報")
async def mytide(interaction: discord.Interaction):
    display_name = interaction.user.display_name
    logging.debug(f"檢查使用者 {interaction.user.id} 的顯示名稱：{display_name}")
    detected_county = None
    for keyword, county in COUNTY_KEYWORDS.items():
        if keyword in display_name:
            if county in LOCATION_MAP:
                detected_county = county
                break
    if detected_county:
        logging.debug(f"從顯示名稱中偵測到縣市：{detected_county}")
        tide_embed = get_tide_data_for_county(detected_county)
        try:
            if not interaction.response.is_done():
                await interaction.response.send_message(embed=tide_embed, ephemeral=True)
            else:
                await interaction.followup.send(embed=tide_embed, ephemeral=True)
        except discord.errors.NotFound as e:
            logging.error(f"Interaction not found, using followup: {e}")
            await interaction.followup.send(embed=tide_embed, ephemeral=True)
    else:
        msg = "未能根據您的顯示名稱偵測到所在縣市，請使用 /tide 指令手動選擇。"
        if not interaction.response.is_done():
            await interaction.response.send_message(msg, ephemeral=True)
        else:
            await interaction.followup.send(msg, ephemeral=True)

# -------------------------------
# 當成員首次上線時自動發送潮汐資訊（僅在 AUTO_REMINDER_ENABLED 為 true 時啟用）
# -------------------------------
@bot.event
async def on_presence_update(before: discord.Member, after: discord.Member):
    if not AUTO_REMINDER_ENABLED:
        return

    if before.status != discord.Status.online and after.status == discord.Status.online:
        member = after
        today_str = datetime.now(ZoneInfo("Asia/Taipei")).strftime("%Y-%m-%d")
        if first_online_today.get(member.id) == today_str:
            return
        first_online_today[member.id] = today_str

        display_name = member.display_name
        logging.debug(f"檢查成員 {member.id} 的顯示名稱：{display_name}")
        detected_county = None
        for keyword, county in COUNTY_KEYWORDS.items():
            if keyword in display_name:
                if county in LOCATION_MAP:
                    detected_county = county
                    break
        if detected_county:
            logging.debug(f"從顯示名稱中偵測到縣市：{detected_county}")
            try:
                # 嘗試依據 REMINDER_CHANNEL_NAME 在所有公會中尋找符合的文字頻道
                reminder_channel = None
                if REMINDER_CHANNEL_NAME:
                    for guild in bot.guilds:
                        channel = discord.utils.get(guild.text_channels, name=REMINDER_CHANNEL_NAME)
                        if channel:
                            reminder_channel = channel
                            break
                    if reminder_channel:
                        logging.debug(f"找到提醒頻道：{reminder_channel.name} (ID: {reminder_channel.id})")
                    else:
                        logging.error(f"找不到名稱為 '{REMINDER_CHANNEL_NAME}' 的提醒頻道。")
                # 若找到提醒頻道則在該頻道發送訊息，否則使用 DM 傳送
                if reminder_channel:
                    tide_embed = get_tide_data_for_county(detected_county)
                    await reminder_channel.send(
                        f"{member.mention} 嗨，根據您的顯示名稱，推測您位於 {detected_county}，以下是該縣所有區的潮汐預報：",
                        embed=tide_embed
                    )
                else:
                    dm_channel = await member.create_dm()
                    tide_embed = get_tide_data_for_county(detected_county)
                    await dm_channel.send(
                        f"嗨，根據您的顯示名稱，推測您位於 {detected_county}，以下是該縣所有區的潮汐預報：",
                        embed=tide_embed
                    )
                logging.debug(f"已向成員 {member.id} 發送自動潮汐資訊。")
            except Exception as e:
                logging.error(f"發送提醒訊息給成員 {member.id} 失敗：{e}")
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
