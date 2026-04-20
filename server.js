import express from 'express';
import Anthropic from '@anthropic-ai/sdk';
import path from 'path';
import { fileURLToPath } from 'url';
import { config } from 'dotenv';

config();

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const app = express();
app.use(express.json());
app.use(express.static(__dirname));

const client = new Anthropic({ apiKey: process.env.ANTHROPIC_API_KEY });

const DAY_FRAMEWORKS = [
  {
    day: 1, type: '常識破壊',
    instruction: '「その常識、実は間違っています」という切り口で、既存の努力を否定し読者の足を止める。冒頭でターゲットが信じている「間違った常識」を直接引用または言及し、強い否定で始める。'
  },
  {
    day: 2, type: '教育',
    instruction: '従来のやり方が成果を出せない理由を3〜4個の具体的な問題点として論理的に解説する。「なぜ〇〇しても意味がないのか」という構成で、ターゲットに「そういうことか！」と気づかせる。'
  },
  {
    day: 3, type: '解決策の提示',
    instruction: '間違った常識を捨てた先に何があるかを示し、サービスを自然な流れで提示する。「頑張る」から「仕組みが動く」へのパラダイムシフトを具体的に描写する。'
  },
  {
    day: 4, type: '権威・実績',
    instruction: '実際のクライアントのBefore/Afterを具体的な数字を使って紹介する。変化した理由を「やる量ではなく構造の変化」として説明し、再現性を示す。'
  },
  {
    day: 5, type: '共感・寄り添い',
    instruction: 'ターゲットが感じている孤独感・取り残される感覚・自己否定を言語化する。「自分だけがうまくいかない」という感情に寄り添い、それは才能や努力の問題ではなく方向性の問題だと伝える。'
  },
  {
    day: 6, type: '希少性・緊急性',
    instruction: '限定枠（残り3名など）の案内と、なぜ少人数限定なのかの理由を明確に示す。「いつかやろう」と思っている人への問いかけで行動を促す。'
  },
  {
    day: 7, type: 'CTA・誘導',
    instruction: '7日間の締めくくりとして「知っている」と「できている」は違うというメッセージで始める。公式LINEへの具体的な誘導文と、登録特典（PDF等）を提示して強く背中を押す。'
  },
];

app.post('/api/generate', async (req, res) => {
  const { target, service, myth, dayIndex } = req.body;

  if (!target || !service || !myth || dayIndex === undefined) {
    return res.status(400).json({ error: '入力が不足しています' });
  }

  const day = DAY_FRAMEWORKS[dayIndex];

  res.setHeader('Content-Type', 'text/event-stream');
  res.setHeader('Cache-Control', 'no-cache');
  res.setHeader('Connection', 'keep-alive');

  try {
    const stream = client.messages.stream({
      model: 'claude-opus-4-7',
      max_tokens: 1200,
      system: `あなたはオンラインビジネスオーナー向けのSNSコピーライターです。
日本語で、InstagramやX(Twitter)で読まれる、感情に強く訴えるSNS投稿文を生成してください。

必須条件：
- 300〜500文字程度（改行込み）
- 冒頭の1〜2行で必ず読者の足を止める強いフックを作る
- 絵文字を3〜6個使用（冒頭・中間・末尾に配置）
- ハッシュタグを2〜4個末尾に付ける（スペースで区切る）
- 改行を多用してスマホで読みやすくする（1文ごとに改行推奨）
- 投稿文のみを出力し、タイトルや説明、前置きは一切不要`,
      messages: [
        {
          role: 'user',
          content: `以下の情報でDay ${day.day}「${day.type}」の投稿文を1つ生成してください。

【ターゲット】${target}
【サービス名・独自の強み（USP）】${service}
【ターゲットが抱えている間違った常識】${myth}

【この投稿の役割】
${day.instruction}

投稿文のみ出力してください。`,
        },
      ],
    });

    for await (const event of stream) {
      if (event.type === 'content_block_delta' && event.delta.type === 'text_delta') {
        res.write(`data: ${JSON.stringify({ text: event.delta.text })}\n\n`);
      }
    }

    res.write('data: [DONE]\n\n');
    res.end();
  } catch (err) {
    console.error('API Error:', err.message);
    res.write(`data: ${JSON.stringify({ error: err.message })}\n\n`);
    res.end();
  }
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
  console.log(`✦ CoreHook AI: http://localhost:${PORT}`);
});
