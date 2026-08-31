"""联网搜索模块：让桌宠可以查询她不知道的内容（免费，无需 Key）。"""

import re

import requests

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Accept-Language": "zh-CN,zh;q=0.9",
}


def _clean(text):
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"&[a-z]+;", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def web_search(query, max_results=5):
    """用 Bing 免费搜索，返回 [{title, snippet, url}, ...]"""
    url = "https://www.bing.com/search"
    resp = requests.get(
        url,
        params={"q": query, "setlang": "zh-CN", "count": max_results + 5},
        headers=_HEADERS,
        timeout=15,
    )
    resp.raise_for_status()
    html = resp.text

    results = []
    blocks = re.findall(r'<li class="b_algo".*?</li>', html, re.S)

    for block in blocks[:max_results]:
        title_m = re.search(r'<h2[^>]*><a[^>]*href="([^"]+)"[^>]*>(.*?)</a></h2>', block, re.S)
        if not title_m:
            continue
        snippet_m = re.search(r'<p[^>]*>(.*?)</p>', block, re.S)
        results.append(
            {
                "title": _clean(title_m.group(2)),
                "snippet": _clean(snippet_m.group(1)) if snippet_m else "",
                "url": title_m.group(1),
            }
        )

    if not results:
        return [{"title": "未找到结果", "snippet": f"关于「{query}」没有搜到内容", "url": ""}]

    return results


def format_results(results):
    lines = []
    for i, r in enumerate(results, 1):
        lines.append(f"{i}. {r['title']}\n   {r['snippet']}\n   {r['url']}")
    return "\n".join(lines)
