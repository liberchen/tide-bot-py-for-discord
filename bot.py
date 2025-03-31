# bot.py
import os
import discord
from discord import app_commands
from datetime import datetime
from tide_api import get_tide_data
import logging

# 設定 logging 格式與等級 (Heroku 可透過 heroku logs --tail 查看)
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

# 讀取 Discord Token
DISCORD_TOKEN = os.environ.get("DISCORD_TOKEN")
if DISCORD_TOKEN:
    logging.debug("DISCORD_TOKEN 已成功載入。")
else:
    logging.error("DISCORD_TOKEN 尚未設定！")

class TideBot(discord.Client):
    def __init__(self):
        intents = discord.Intents.default()
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        logging.debug("開始設定 Slash Command ...")
        self.tree.add_command(tide)
        await self.tree.sync()
        logging.debug("Slash Command 同步完成。")

@discord.app_commands.command(name="tide", description="取得台灣當日潮汐資訊")
async def tide(interaction: discord.Interaction):
    logging.debug("收到 /tide 指令。")
    # 使用當日日期，格式為 YYYY-MM-DD
    today = datetime.now().strftime("%Y-%m-%d")
    logging.debug(f"查詢日期設定為：{today}")
    tide_info = get_tide_data(today)
    logging.debug("組成回覆訊息內容如下：")
    logging.debug(tide_info)
    await interaction.response.send_message(tide_info)
    logging.debug("回覆訊息已成功送出。")

if __name__ == "__main__":
    logging.debug("啟動 TideBot ...")
    client = TideBot()
    client.run(DISCORD_TOKEN)
