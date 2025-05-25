import os
import discord
from discord.ext import commands
from dotenv import load_dotenv
import requests
import datetime
from discord import app_commands
from collections import defaultdict

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
API_TOKEN = os.getenv("NYUTAI_API_TOKEN")
BASE_URL = "https://site1.nyutai.com/api/chief/v1"
HEADERS = {"Api-Token": API_TOKEN}

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="/", intents=intents)

# 日付の範囲を指定（直近1週間）
def get_date_range():
    today = datetime.date.today()
    date_from = (today - datetime.timedelta(days=7)).isoformat()
    date_to = today.isoformat()
    return date_from, date_to

# 生徒一覧を全取得
def fetch_students():
    student_map = {}
    page = 1
    while True:
        resp = requests.get(f"{BASE_URL}/students", headers=HEADERS, params={"page": page})
        if resp.status_code != 200:
            return None
        data = resp.json().get("data", [])
        if not data:
            break
        for student in data:
            student_map[student["id"]] = student["name"]
        page += 1
    return student_map

# 入退室ログを取得
def fetch_logs(date_from, date_to):
    logs_resp = requests.get(f"{BASE_URL}/entrance_and_exits", headers=HEADERS, params={
        "date_from": date_from,
        "date_to": date_to
    })
    if logs_resp.status_code != 200:
        return None
    return logs_resp.json().get("data", [])

# ログをEmbedに変換
def create_log_embed(student_id, student_name, logs):
    student_logs = [log for log in logs if int(log["user_id"]) == student_id]
    if not student_logs:
        return None

    sorted_logs = sorted(student_logs, key=lambda x: x["entrance_time"])
    grouped_logs = defaultdict(lambda: defaultdict(list))

    for record in sorted_logs:
        entrance_str = record.get("entrance_time")
        exit_str = record.get("exit_time")
        if not entrance_str:
            continue

        entrance_dt = datetime.datetime.fromisoformat(entrance_str)
        exit_dt = (
            datetime.datetime.fromisoformat(exit_str)
            if exit_str else None
        )

        grouped_logs[entrance_dt.year][entrance_dt.month].append({
            "day": entrance_dt.day,
            "start": entrance_dt.strftime("%H:%M"),
            "end": exit_dt.strftime("%H:%M") if exit_dt else "未退室",
            "duration": str(exit_dt - entrance_dt) if exit_dt else None
        })

    message_lines = []
    weekday_map = ["月", "火", "水", "木", "金", "土", "日"]
    total_minutes = 0

    for year in sorted(grouped_logs):
        for month in sorted(grouped_logs[year]):
            for log in grouped_logs[year][month]:
                if log["duration"]:
                    h, m = map(int, log["duration"].split(":")[:2])
                    total_minutes += h * 60 + m

    message_lines.append(f"**直近一週間の合計滞在時間: {total_minutes // 60}時間{total_minutes % 60}分**\n")

    for year in sorted(grouped_logs):
        message_lines.append(f"**{year}年**")
        for month in sorted(grouped_logs[year]):
            message_lines.append(f"**{month}月**")
            for log in grouped_logs[year][month]:
                dt = datetime.datetime(year, month, log["day"])
                weekday = weekday_map[dt.weekday()]
                dur_text = (
                    f"{int(log['duration'].split(':')[0])}時間{int(log['duration'].split(':')[1])}分"
                    if log["duration"] else "滞在中"
                )
                message_lines.append(
                    f"{log['day']}日（{weekday}） {dur_text} {log['start']} → {log['end']}"
                )

    embed = discord.Embed(
        title=f"{student_name} の入退室ログ",
        description="\n".join(message_lines),
        color=discord.Color.teal()
    )
    embed.set_footer(text="powered by 入退くん × Discord Bot")
    return embed

# 選択用 View（検索マッチ or ページ分割）
class StudentSelectView(discord.ui.View):
    def __init__(self, student_list, logs):
        super().__init__(timeout=60)
        self.logs = logs

        for i in range(0, len(student_list), 25):
            options = [
                discord.SelectOption(label=sname, value=str(sid))
                for sid, sname in student_list[i:i+25]
            ]
            self.add_item(StudentSelect(options, self.logs))

class StudentSelect(discord.ui.Select):
    def __init__(self, options, logs):
        super().__init__(placeholder="生徒を選んでください", min_values=1, max_values=1, options=options)
        self.logs = logs

    async def callback(self, interaction: discord.Interaction):
        sid = int(self.values[0])
        sname = next((opt.label for opt in self.options if int(opt.value) == sid), "Unknown")
        embed = create_log_embed(sid, sname, self.logs)
        if embed:
            await interaction.response.send_message(embed=embed, ephemeral=False)
        else:
            await interaction.response.send_message("該当ログがありません。", ephemeral=False)

# コマンド本体
@bot.tree.command(name="log", description="入退室ログを表示（名前検索 or 一覧から選択）")
@app_commands.describe(name="生徒名を入力してください（必須）")
async def log(interaction: discord.Interaction, name: str):
    await interaction.response.defer(thinking=True, ephemeral=False)

    student_map = fetch_students()
    if student_map is None:
        await interaction.followup.send("生徒一覧の取得に失敗しました。")
        return

    date_from, date_to = get_date_range()
    logs = fetch_logs(date_from, date_to)
    if logs is None:
        await interaction.followup.send("入退室ログの取得に失敗しました。")
        return

    if name:
        filtered = [(sid, sname) for sid, sname in student_map.items() if name in sname]
        if not filtered:
            await interaction.followup.send(f"「{name}」に一致する生徒が見つかりませんでした。")
            return
        if len(filtered) > 25:
            filtered = filtered[:25]
    else:
        filtered = sorted(student_map.items(), key=lambda x: x[1])

    view = StudentSelectView(filtered, logs)
    await interaction.followup.send("生徒を選んでください：", view=view)

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} commands.")
    except Exception as e:
        print(f"Failed to sync commands: {e}")

bot.run(TOKEN)