#!/usr/bin/env python3
"""CoreHook AI — Claude API streaming server"""
import json
import os
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

# ── Dependency check ──────────────────────────────────────────────────────────
try:
    import anthropic
except ImportError:
    print("anthropic パッケージが見つかりません。インストール中...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "anthropic"])
    import anthropic

# ── API Key ───────────────────────────────────────────────────────────────────
API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
if not API_KEY:
    env_path = Path(__file__).parent / ".env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            if line.startswith("ANTHROPIC_API_KEY="):
                API_KEY = line.split("=", 1)[1].strip().strip('"').strip("'")
                break

client = anthropic.Anthropic(api_key=API_KEY) if API_KEY else None

# ── Day frameworks ────────────────────────────────────────────────────────────
DAY_FRAMEWORKS = [
    {"day": 1, "type": "常識破壊",
     "instruction": "「その常識、実は間違っています」という切り口で、既存の努力を否定し読者の足を止める。冒頭でターゲットが信じている「間違った常識」を直接引用または言及し、強い否定で始める。"},
    {"day": 2, "type": "教育",
     "instruction": "従来のやり方が成果を出せない理由を3〜4個の具体的な問題点として論理的に解説する。「なぜ〇〇しても意味がないのか」という構成で、ターゲットに「そういうことか！」と気づかせる。"},
    {"day": 3, "type": "解決策の提示",
     "instruction": "間違った常識を捨てた先に何があるかを示し、サービスを自然な流れで提示する。「頑張る」から「仕組みが動く」へのパラダイムシフトを具体的に描写する。"},
    {"day": 4, "type": "権威・実績",
     "instruction": "実際のクライアントのBefore/Afterを具体的な数字を使って紹介する。変化した理由を「やる量ではなく構造の変化」として説明し、再現性を示す。"},
    {"day": 5, "type": "共感・寄り添い",
     "instruction": "ターゲットが感じている孤独感・取り残される感覚・自己否定を言語化する。「自分だけがうまくいかない」という感情に寄り添い、それは才能や努力の問題ではなく方向性の問題だと伝える。"},
    {"day": 6, "type": "希少性・緊急性",
     "instruction": "限定枠（残り3名など）の案内と、なぜ少人数限定なのかの理由を明確に示す。「いつかやろう」と思っている人への問いかけで行動を促す。"},
    {"day": 7, "type": "CTA・誘導",
     "instruction": "7日間の締めくくりとして「知っている」と「できている」は違うというメッセージで始める。公式LINEへの具体的な誘導文と、登録特典（PDF等）を提示して強く背中を押す。"},
]

SYSTEM_PROMPT = """あなたはオンラインビジネスオーナー向けのSNSコピーライターです。
日本語で、InstagramやX(Twitter)で読まれる、感情に強く訴えるSNS投稿文を生成してください。

必須条件：
- 300〜500文字程度（改行込み）
- 冒頭の1〜2行で必ず読者の足を止める強いフックを作る
- 絵文字を3〜6個使用（冒頭・中間・末尾に配置）
- ハッシュタグを2〜4個末尾に付ける（スペースで区切る）
- 改行を多用してスマホで読みやすくする（1文ごとに改行推奨）
- 投稿文のみを出力し、タイトルや説明、前置きは一切不要"""

# ── HTTP Handler ──────────────────────────────────────────────────────────────
class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass  # suppress default logging

    def do_GET(self):
        path = self.path.split("?")[0]
        if path in ("/", "/index.html"):
            self._serve_file("index.html", "text/html; charset=utf-8")
        else:
            self.send_error(404)

    def do_POST(self):
        if self.path != "/api/generate":
            self.send_error(404)
            return

        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length))
        target    = body.get("target", "").strip()
        service   = body.get("service", "").strip()
        myth      = body.get("myth", "").strip()
        day_index = body.get("dayIndex")

        if not all([target, service, myth]) or day_index is None:
            self._json_error(400, "入力が不足しています")
            return

        if not client:
            self._json_error(500, "ANTHROPIC_API_KEY が設定されていません")
            return

        day = DAY_FRAMEWORKS[int(day_index)]
        user_msg = (
            f"以下の情報でDay {day['day']}「{day['type']}」の投稿文を1つ生成してください。\n\n"
            f"【ターゲット】{target}\n"
            f"【サービス名・独自の強み（USP）】{service}\n"
            f"【ターゲットが抱えている間違った常識】{myth}\n\n"
            f"【この投稿の役割】\n{day['instruction']}\n\n"
            "投稿文のみ出力してください。"
        )

        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()

        try:
            with client.messages.stream(
                model="claude-opus-4-7",
                max_tokens=1200,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_msg}],
            ) as stream:
                for text in stream.text_stream:
                    data = json.dumps({"text": text}, ensure_ascii=False)
                    self.wfile.write(f"data: {data}\n\n".encode("utf-8"))
                    self.wfile.flush()
            self.wfile.write(b"data: [DONE]\n\n")
            self.wfile.flush()
        except Exception as e:
            err = json.dumps({"error": str(e)}, ensure_ascii=False)
            self.wfile.write(f"data: {err}\n\n".encode("utf-8"))
            self.wfile.flush()

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def _serve_file(self, filename, content_type):
        p = Path(__file__).parent / filename
        if not p.exists():
            self.send_error(404)
            return
        data = p.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _json_error(self, code, msg):
        body = json.dumps({"error": msg}, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


if __name__ == "__main__":
    PORT = int(os.environ.get("PORT", 3000))
    if not API_KEY:
        print("⚠️  ANTHROPIC_API_KEY が未設定です。")
        print("   .env ファイルに ANTHROPIC_API_KEY=sk-ant-... を記載するか、")
        print("   環境変数で設定してください。\n")
    server = HTTPServer(("0.0.0.0", PORT), Handler)
    print(f"✦ CoreHook AI: http://0.0.0.0:{PORT}")
    print("  停止: Ctrl+C\n")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nサーバーを停止しました。")
