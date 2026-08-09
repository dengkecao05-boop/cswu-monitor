import argparse
import hashlib
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from html import unescape
from pathlib import Path


DEFAULT_TIMEOUT = 25


def load_json(path):
    with Path(path).open("r", encoding="utf-8") as file:
        return json.load(file)


def save_json(path, data):
    target = Path(path)
    target.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def expand_env(value):
    if not isinstance(value, str):
        return value

    pattern = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)(?::-(.*?))?\}")

    def replace(match):
        name = match.group(1)
        default = match.group(2)
        current = os.environ.get(name)
        if current:
            return current
        if default is not None:
            return default
        return match.group(0)

    return pattern.sub(replace, value)


def request_text(url, timeout=DEFAULT_TIMEOUT):
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "CQC-New-Content-Monitor/1.0",
            "Accept": "application/rss+xml, application/atom+xml, application/xml, text/xml, */*",
        },
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        raw = response.read()
        encoding = response.headers.get_content_charset() or "utf-8"
        return raw.decode(encoding, errors="replace")


def strip_html(text):
    if not text:
        return ""
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.I)
    text = re.sub(r"<[^>]+>", "", text)
    text = unescape(text)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def child_text(element, names):
    for name in names:
        child = element.find(name)
        if child is not None and child.text:
            return child.text.strip()
    for child in list(element):
        local_name = child.tag.rsplit("}", 1)[-1]
        if local_name in names and child.text:
            return child.text.strip()
    return ""


def atom_link(entry):
    for child in list(entry):
        local_name = child.tag.rsplit("}", 1)[-1]
        if local_name == "link":
            href = child.attrib.get("href")
            if href:
                return href.strip()
    return ""


def parse_feed(xml_text, source):
    root = ET.fromstring(xml_text)
    root_name = root.tag.rsplit("}", 1)[-1].lower()
    items = []

    if root_name == "rss":
        candidates = root.findall("./channel/item")
        for item in candidates:
            title = child_text(item, ["title"])
            link = child_text(item, ["link"])
            guid = child_text(item, ["guid"]) or link
            published = child_text(item, ["pubDate", "date", "published", "updated"])
            summary = strip_html(child_text(item, ["description", "summary", "encoded"]))
            items.append(make_item(source, title, link, guid, published, summary))
        return items

    if root_name == "feed":
        candidates = [
            child
            for child in list(root)
            if child.tag.rsplit("}", 1)[-1].lower() == "entry"
        ]
        for entry in candidates:
            title = child_text(entry, ["title"])
            link = atom_link(entry) or child_text(entry, ["link"])
            guid = child_text(entry, ["id"]) or link
            published = child_text(entry, ["published", "updated"])
            summary = strip_html(child_text(entry, ["summary", "content"]))
            items.append(make_item(source, title, link, guid, published, summary))
        return items

    raise ValueError("不是可识别的 RSS/Atom 格式")


def make_item(source, title, link, guid, published, summary):
    raw_id = "|".join(
        [
            source.get("name", ""),
            source.get("platform", ""),
            guid or "",
            link or "",
            title or "",
            published or "",
        ]
    )
    stable_id = hashlib.sha256(raw_id.encode("utf-8")).hexdigest()
    return {
        "id": stable_id,
        "title": title or "(无标题)",
        "link": link,
        "published": published,
        "summary": summary,
        "source": source.get("name", "未命名来源"),
        "platform": source.get("platform", "未知平台"),
    }


def load_state(path):
    state_path = Path(path)
    if not state_path.exists():
        return {"seen": {}, "last_run": None}
    return load_json(state_path)


def trim_seen(seen, max_items=1000):
    if len(seen) <= max_items:
        return seen
    ordered = sorted(seen.items(), key=lambda pair: pair[1].get("seen_at", ""))
    return dict(ordered[-max_items:])


def collect_new_items(config, state):
    first_run = not bool(state.get("seen"))
    seen = state.setdefault("seen", {})
    new_items = []
    errors = []

    for source in config.get("sources", []):
        if not source.get("enabled", False):
            continue
        if source.get("type") != "rss":
            errors.append(f"{source.get('name', '未命名来源')}：暂不支持的类型 {source.get('type')}")
            continue

        url = expand_env(source.get("url", ""))
        if "${" in url or not url.startswith(("http://", "https://")):
            errors.append(f"{source.get('name', '未命名来源')}：RSS 地址未配置完整")
            continue

        try:
            feed_text = request_text(url)
            items = parse_feed(feed_text, source)
        except (urllib.error.URLError, TimeoutError, ET.ParseError, ValueError) as exc:
            errors.append(f"{source.get('name', '未命名来源')}：{exc}")
            continue

        limit = int(source.get("poll_limit", 10))
        for item in items[:limit]:
            if item["id"] not in seen:
                seen[item["id"]] = {
                    "title": item["title"],
                    "source": item["source"],
                    "platform": item["platform"],
                    "link": item["link"],
                    "seen_at": datetime.now(timezone.utc).isoformat(),
                }
                if config.get("first_run_notify", False) or not first_run:
                    new_items.append(item)

    state["seen"] = trim_seen(seen)
    state["last_run"] = datetime.now(timezone.utc).isoformat()
    return new_items, errors


def format_message(items, errors):
    lines = []
    if items:
        lines.append(f"发现 {len(items)} 条新内容：")
        lines.append("")
        for index, item in enumerate(items, start=1):
            lines.append(f"{index}. [{item['platform']}] {item['title']}")
            lines.append(f"来源：{item['source']}")
            if item.get("published"):
                lines.append(f"时间：{item['published']}")
            if item.get("link"):
                lines.append(f"链接：{item['link']}")
            if item.get("summary"):
                summary = item["summary"].replace("\r", "").strip()
                if len(summary) > 220:
                    summary = summary[:220].rstrip() + "..."
                lines.append(f"摘要：{summary}")
            lines.append("")
    if errors:
        lines.append("检查时有这些来源暂时失败：")
        for error in errors:
            lines.append(f"- {error}")
    return "\n".join(lines).strip()


def send_serverchan(title, content):
    sendkey = os.environ.get("SERVERCHAN_SENDKEY")
    if not sendkey:
        raise RuntimeError("未设置 SERVERCHAN_SENDKEY")

    if sendkey.startswith("sctp"):
        match = re.match(r"sctp(\d+)t", sendkey)
        if not match:
            raise RuntimeError("Server酱³ SendKey 格式无法识别")
        url = f"https://{match.group(1)}.push.ft07.com/send/{sendkey}.send"
    else:
        url = f"https://sctapi.ftqq.com/{sendkey}.send"

    data = urllib.parse.urlencode({"title": title, "desp": content}).encode("utf-8")
    request = urllib.request.Request(url, data=data, method="POST")
    with urllib.request.urlopen(request, timeout=DEFAULT_TIMEOUT) as response:
        return response.read().decode("utf-8", errors="replace")


def send_pushplus(title, content):
    token = os.environ.get("PUSHPLUS_TOKEN")
    if not token:
        raise RuntimeError("未设置 PUSHPLUS_TOKEN")
    body = json.dumps(
        {
            "token": token,
            "title": title,
            "content": content,
            "template": "markdown",
        },
        ensure_ascii=False,
    ).encode("utf-8")
    request = urllib.request.Request(
        "https://www.pushplus.plus/send",
        data=body,
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=DEFAULT_TIMEOUT) as response:
        return response.read().decode("utf-8", errors="replace")


def send_notification(config, title, content):
    provider = config.get("notify", {}).get("provider", "serverchan").lower()
    if provider == "serverchan":
        return send_serverchan(title, content)
    if provider == "pushplus":
        return send_pushplus(title, content)
    raise RuntimeError(f"未知推送方式：{provider}")


def run(config_path, test_push=False):
    config = load_json(config_path)
    state_file = Path(config_path).parent / config.get("state_file", "state.json")
    state = load_state(state_file)

    if test_push:
        title = f"{config.get('notify', {}).get('title_prefix', '新内容监控')}：测试"
        content = "这是一条测试消息。收到它，说明微信推送已经连通。"
        send_notification(config, title, content)
        print("测试推送已发送")
        return 0

    new_items, errors = collect_new_items(config, state)
    save_json(state_file, state)

    if not new_items and not errors:
        print("没有发现新内容")
        return 0

    if new_items:
        title = f"{config.get('notify', {}).get('title_prefix', '新内容监控')}：{len(new_items)} 条更新"
        send_notification(config, title, format_message(new_items, errors))
        print(f"已推送 {len(new_items)} 条新内容")
        return 0

    print(format_message([], errors), file=sys.stderr)
    return 1


def main():
    parser = argparse.ArgumentParser(description="监控官方新内容并微信推送")
    parser.add_argument("--config", default="config.json", help="配置文件路径")
    parser.add_argument("--test-push", action="store_true", help="发送测试推送")
    args = parser.parse_args()
    return run(args.config, args.test_push)


if __name__ == "__main__":
    raise SystemExit(main())
