# bot.py
import os
import discord
from discord import app_commands
from datetime import datetime
from tide_api import get_tide_data

# 從環境變數讀取 Discord Token
DISCORD_TOKEN = os.environ.get("DISCORD_TOKEN")

class TideBot(discord.Client):
    def __init__(self):
        intents = discord.Intents.default()
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        # 註冊 slash command
        self.tree.add_command(get_tide)
        await self.tree.sync()

@discord.app_commands.command(name="getTide", description="取得台灣當日潮汐資訊")
async def get_tide(interaction: discord.Interaction):
    # 使用當日日期，格式為 YYYY-MM-DD
    today = datetime.now().strftime("%Y-%m-%d")
    tide_info = get_tide_data(today)
    await interaction.response.send_message(tide_info)

if __name__ == "__main__":
    client = TideBot()
    client.run(DISCORD_TOKEN)
