# ✅ Discord入退室Bot 実行マニュアル (Google Compute Engine 用)

この手順は GitHub にある `bot.py` と `requirements.txt` の2つのファイルから、  
GCE (Google Cloud Platform) 上に 24時間動作する Discord Bot を構築するための手順です。

---

## ▶ 前提条件

- Google Cloud Platform のアカウント
- Discord Bot Token を [Discord Developer Portal](https://discord.com/developers/applications) で登録済み
- NYUTAI API Token (入退くんAPI)

---

## ▶ ステップ 1: GCE VM インスタンス作成

1. [Google Cloud Console](https://console.cloud.google.com/) にログイン
2. 左メニュー「Compute Engine」→「VM インスタンス」
3. 「インスタンスを作成」:
   - 名前: `discord-bot` など
   - リージョン: `us-west1` (無料枠)
   - マシン: `e2-micro` (無料枠)
   - OS: Ubuntu 22.04 LTS
4. 「作成」ボタンを押す

---

## ▶ ステップ 2: SSH で接続して準備

```bash
sudo apt update && sudo apt install -y python3 python3-pip git nano tmux
cd ~
```

---

## ▶ ステップ 3: 必要ファイルの作成

### 📄 `bot.py` の作成

```bash
nano bot.py
```

→ GitHub の `bot.py` 内容を貼り付け、`Ctrl + O` → `Enter` → `Ctrl + X`

### 📄 `requirements.txt` の作成

```bash
nano requirements.txt
```

```txt
discord.py>=2.5.2
python-dotenv>=1.1.0
requests>=2.32.3
```

→ 保存して終了

---

## ▶ ステップ 4: `.env` ファイルの作成

```bash
nano .env
```

```
DISCORD_TOKEN=あなたのDiscordトークン
NYUTAI_API_TOKEN=あなたのAPIトークン
```

---

## ▶ ステップ 5: ライブラリのインストール

```bash
pip3 install -r requirements.txt
```

---

## ▶ ステップ 6: Bot を起動

```bash
python3 bot.py
```

---

## ▶ ステップ 7: tmux でバックグラウンド実行

```bash
tmux new -s discordbot
python3 bot.py
```

→ `Ctrl + B` → `D` で離脱  
→ 復帰は `tmux attach -t discordbot`

---

## ✅ 完了！

- Discord 上で `/log` コマンドを実行
- Bot が入退室ログを表示

これで他の校舎でも同じように構築できます。
