#!/usr/bin/env python3
"""抓取 RSS → DeepSeek 总结 → Buttondown 发送/草稿。"""

from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

import feedparser
import requests
import yaml
from openai import OpenAI

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "config" / "sources.yaml"
OUTPUT_DIR = ROOT / "output"
sys.path.insert(0, str(ROOT / "scripts"))
from publish_site import publish_site_pages  # noqa: E402

DIGEST_TITLE = "全球物流每日动态"

SYSTEM_PROMPT = f"""你是全球物流行业编辑。根据给定英文/中文资讯，写一份中文「{DIGEST_TITLE}」邮件正文。

行业范围（必须遵守）：
1. 国际货代行业：货运代理、海运/空运/铁路/多式联运、报关清关、港口与航线、运价与舱位、3PL 等
2. 国际工程物流(EPC)行业：海外工程项目物流、重大件/超限运输、项目供应链、EPC 承包商物流、能源/基建项目运输等

要求：
1. 使用 Markdown
2. 开头一级标题：# {DIGEST_TITLE} | YYYY-MM-DD
3. 「## 今日要点」3 条 bullet（跨货代与 EPC 的高价值信息）
4. 「## 国际货代动态」：相关条目，每条含标题、1-2 句中文摘要、原文链接
5. 「## 国际工程物流(EPC)动态」：相关条目；若当日无 EPC 新闻，写「今日暂无显著 EPC 相关报道」
6. 优先选用与跨境运输、货代、工程项目物流相关的资讯；忽略与主题无关的 AI/科技/消费类内容
7. 去重、合并同类话题，不编造链接或事实
8. 语气简洁专业，面向货代与 EPC 物流从业者
9. 结尾一行：---\\n由 DeepSeek 自动整理
"""


def load_config() -> dict:
    with CONFIG_PATH.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


def parse_entry_time(entry: feedparser.FeedParserDict) -> datetime | None:
    for key in ("published_parsed", "updated_parsed"):
        parsed = entry.get(key)
        if parsed:
            return datetime(*parsed[:6], tzinfo=timezone.utc)
    for key in ("published", "updated"):
        raw = entry.get(key)
        if raw:
            try:
                dt = parsedate_to_datetime(raw)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt.astimezone(timezone.utc)
            except (TypeError, ValueError):
                continue
    return None


def fetch_items(config: dict) -> list[dict]:
    cutoff = datetime.now(timezone.utc) - timedelta(hours=config.get("max_age_hours", 48))
    per_feed = config.get("max_items_per_feed", 8)
    items: list[dict] = []

    for feed in config.get("feeds", []):
        name = feed.get("name", "Unknown")
        url = feed["url"]
        parsed = feedparser.parse(url)
        count = 0
        for entry in parsed.entries:
            if count >= per_feed:
                break
            published = parse_entry_time(entry)
            if published and published < cutoff:
                continue
            link = entry.get("link", "")
            title = (entry.get("title") or "").strip()
            if not title or not link:
                continue
            summary = (entry.get("summary") or entry.get("description") or "").strip()
            if len(summary) > 500:
                summary = summary[:500] + "..."
            items.append(
                {
                    "source": name,
                    "title": title,
                    "link": link,
                    "summary": summary,
                    "published": published.isoformat() if published else "",
                }
            )
            count += 1

    return items


def build_raw_digest(items: list[dict]) -> str:
    lines = []
    for i, item in enumerate(items, 1):
        lines.append(f"[{i}] 来源: {item['source']}")
        lines.append(f"标题: {item['title']}")
        lines.append(f"链接: {item['link']}")
        if item["summary"]:
            lines.append(f"摘要: {item['summary']}")
        if item["published"]:
            lines.append(f"时间: {item['published']}")
        lines.append("")
    return "\n".join(lines)


def summarize_with_deepseek(raw_text: str, today: str) -> str:
    api_key = os.environ.get("DEEPSEEK_API_KEY")
    if not api_key:
        raise RuntimeError("缺少环境变量 DEEPSEEK_API_KEY")

    client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
    response = client.chat.completions.create(
        model=os.environ.get("DEEPSEEK_MODEL", "deepseek-chat"),
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f"今天是 {today}。请根据以下资讯生成邮件正文：\n\n{raw_text}",
            },
        ],
        temperature=0.3,
    )
    return response.choices[0].message.content.strip()


def send_to_buttondown(subject: str, body: str, send_mode: str) -> dict:
    api_key = os.environ.get("BUTTONDOWN_API_KEY")
    if not api_key:
        raise RuntimeError("缺少环境变量 BUTTONDOWN_API_KEY")

    status = "about_to_send" if send_mode == "send" else "draft"
    headers = {
        "Authorization": f"Token {api_key}",
        "Content-Type": "application/json",
    }
    if send_mode == "send":
        headers["X-Buttondown-Live-Dangerously"] = "true"
    payload = {
        "subject": subject,
        "body": body,
        "status": status,
    }

    resp = requests.post(
        "https://api.buttondown.com/v1/emails",
        headers=headers,
        json=payload,
        timeout=60,
    )
    if resp.status_code >= 400:
        raise RuntimeError(f"Buttondown API 失败 ({resp.status_code}): {resp.text}")
    return resp.json()


def validate_secrets() -> None:
    missing = []
    for name in ("DEEPSEEK_API_KEY", "BUTTONDOWN_API_KEY"):
        value = os.environ.get(name, "").strip()
        if not value or "你的" in value or value.startswith("sk-你的"):
            missing.append(name)
    if missing:
        raise RuntimeError(
            "以下 Secret 未配置或仍是占位符，请到 GitHub Settings → Secrets 填写真实 Key："
            + ", ".join(missing)
        )


def main() -> int:
    validate_secrets()
    config = load_config()
    items = fetch_items(config)
    today = datetime.now().strftime("%Y-%m-%d")

    if not items:
        print("最近没有抓到新资讯，跳过发送。")
        return 0

    raw_text = build_raw_digest(items)
    print(f"已抓取 {len(items)} 条资讯，正在调用 DeepSeek...")

    body = summarize_with_deepseek(raw_text, today)
    subject = f"{DIGEST_TITLE} · {today}"

    OUTPUT_DIR.mkdir(exist_ok=True)
    out_file = OUTPUT_DIR / f"digest-{today}.md"
    out_file.write_text(body, encoding="utf-8")
    print(f"已保存本地副本: {out_file}")

    index_file = publish_site_pages(today, subject, body)
    print(f"已生成落地页: {index_file}")

    send_mode = os.environ.get("SEND_MODE", "draft").lower()
    result = send_to_buttondown(subject, body, send_mode)
    print(f"Buttondown 状态: {result.get('status')} | ID: {result.get('id')}")
    if result.get("absolute_url"):
        print(f"预览/归档: {result['absolute_url']}")

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"错误: {exc}", file=sys.stderr)
        raise SystemExit(1)
