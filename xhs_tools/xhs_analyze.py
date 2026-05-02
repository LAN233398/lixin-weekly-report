"""
小红书数据分析脚本 — 提取立信小狐所有笔记数据并分析
"""
import asyncio
import json
import sys
from pathlib import Path
from datetime import datetime
from playwright.async_api import async_playwright

AUTH_FILE = Path(__file__).parent.parent / "secrets" / "xhs_auth.json"
DATA_DIR = Path(__file__).parent.parent / "运营数据"
DATA_DIR.mkdir(exist_ok=True)


async def fetch_all_notes():
    """获取所有笔记（翻页直到 has_more=false）"""
    if not AUTH_FILE.exists():
        print("❌ 请先运行 python xhs_login.py")
        return []

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True, args=["--disable-blink-features=AutomationControlled"]
        )
        context = await browser.new_context(
            storage_state=str(AUTH_FILE),
            viewport={"width": 1280, "height": 900},
            locale="zh-CN",
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
            ),
        )
        page = await context.new_page()
        await page.add_init_script(
            "Object.defineProperty(navigator, 'webdriver', { get: () => false });"
        )

        # 收集所有 user_posted 响应
        responses = []

        async def on_resp(resp):
            if "user_posted" in resp.url:
                try:
                    body = await resp.text()
                    responses.append(body)
                except Exception:
                    pass

        page.on("response", on_resp)

        # 打开个人主页
        await page.goto(
            "https://www.xiaohongshu.com/user/profile/67a485ca000000000500d396",
            wait_until="domcontentloaded",
            timeout=60000,
        )
        await page.wait_for_timeout(5000)

        # 滚动加载所有笔记
        for i in range(20):  # 最多翻20页
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await page.wait_for_timeout(2500)
            # 检查是否已经到底
            at_bottom = await page.evaluate(
                "window.scrollY + window.innerHeight >= document.body.scrollHeight - 100"
            )
            if at_bottom:
                await page.wait_for_timeout(3000)
                # 再检查一次
                at_bottom = await page.evaluate(
                    "window.scrollY + window.innerHeight >= document.body.scrollHeight - 100"
                )
                if at_bottom:
                    print(f"  滚动到底，共翻 {i+1} 页")
                    break

        await browser.close()

        # 解析所有响应，去重合并
        all_notes = []
        seen_ids = set()

        for resp_text in responses:
            try:
                data = json.loads(resp_text)
                if data.get("success") and data.get("data", {}).get("notes"):
                    for note in data["data"]["notes"]:
                        nid = note.get("note_id")
                        if nid and nid not in seen_ids:
                            seen_ids.add(nid)
                            all_notes.append(note)
            except json.JSONDecodeError:
                pass

        return all_notes


def analyze(notes: list):
    """分析笔记数据"""
    if not notes:
        print("无数据")
        return

    now = datetime.now()

    print("=" * 60)
    print("  立信小狐 小红书账号分析报告")
    print(f"  生成时间：{now.strftime('%Y年%m月%d日 %H:%M')}")
    print("=" * 60)

    # 基本信息
    print(f"\n📊 基本信息")
    print(f"  账号昵称：立信小狐")
    print(f"  Red ID：Xiaohu_Lixin")
    print(f"  笔记总数：{len(notes)} 篇")

    # 互动数据
    total_likes = sum(int(n.get("interact_info", {}).get("liked_count", 0)) for n in notes)
    avg_likes = total_likes / len(notes) if notes else 0

    print(f"\n❤️ 点赞数据")
    print(f"  总点赞数：{total_likes}")
    print(f"  平均点赞：{avg_likes:.1f}")
    print(f"  最高点赞：{max(int(n.get('interact_info', {}).get('liked_count', 0)) for n in notes)}")
    print(f"  最低点赞：{min(int(n.get('interact_info', {}).get('liked_count', 0)) for n in notes)}")

    # 点赞分布
    like_ranges = {"0": 0, "1-5": 0, "6-10": 0, "11-20": 0, "20+": 0}
    for n in notes:
        lc = int(n.get("interact_info", {}).get("liked_count", 0))
        if lc == 0:
            like_ranges["0"] += 1
        elif lc <= 5:
            like_ranges["1-5"] += 1
        elif lc <= 10:
            like_ranges["6-10"] += 1
        elif lc <= 20:
            like_ranges["11-20"] += 1
        else:
            like_ranges["20+"] += 1

    print(f"\n📈 点赞分布")
    for r, c in like_ranges.items():
        bar = "█" * c
        print(f"  {r:>5}赞: {c:>3}篇 {bar}")

    # 笔记类型
    types = {}
    for n in notes:
        t = n.get("type", "unknown")
        types[t] = types.get(t, 0) + 1
    print(f"\n🏷️ 笔记类型")
    for t, c in sorted(types.items()):
        print(f"  {t}: {c}篇")

    # 笔记标题列表（按点赞排序）
    sorted_notes = sorted(
        notes,
        key=lambda n: int(n.get("interact_info", {}).get("liked_count", 0)),
        reverse=True,
    )

    print(f"\n📝 笔记排行榜（按点赞数）")
    print("-" * 60)
    for i, n in enumerate(sorted_notes):
        title = n.get("display_title", "(无标题)")[:50]
        likes = n.get("interact_info", {}).get("liked_count", "0")
        nid = n.get("note_id", "")
        url = f"https://www.xiaohongshu.com/explore/{nid}"
        print(f"  {i+1:>2}. [{likes:>3}👍] {title}")
        print(f"      {url}")

    # 内容策略分析
    print(f"\n💡 内容策略分析")
    print("-" * 60)
    titles = [n.get("display_title", "") for n in notes]

    # 分类
    categories = {
        "新生指南": [],
        "校园攻略": [],
        "答疑互动": [],
        "录取/毕业": [],
        "其他": [],
    }

    for n in sorted_notes:
        title = n.get("display_title", "")
        if "新生" in title or "指南" in title:
            categories["新生指南"].append(n)
        elif "攻略" in title or "地图" in title or "校历" in title:
            categories["校园攻略"].append(n)
        elif "答疑" in title or "求" in title or "爆料" in title or "?" in title or "？" in title:
            categories["答疑互动"].append(n)
        elif "录取" in title or "毕业" in title:
            categories["录取/毕业"].append(n)
        else:
            categories["其他"].append(n)

    for cat, items in categories.items():
        if items:
            total_l = sum(int(n.get("interact_info", {}).get("liked_count", 0)) for n in items)
            avg_l = total_l / len(items) if items else 0
            print(f"  📂 {cat}：{len(items)}篇，平均{avg_l:.0f}👍")
            for n in items[:5]:
                title = n.get("display_title", "")[:40]
                likes = n.get("interact_info", {}).get("liked_count", "0")
                print(f"      [{likes}👍] {title}")
            if len(items) > 5:
                print(f"      ... 还有 {len(items)-5} 篇")
            print()

    # 建议
    print("🎯 运营建议")
    print("-" * 60)
    if avg_likes < 10:
        print("  1. 当前点赞偏低，建议增加互动型内容（投票、提问、征集）")
    if len(notes) < 30:
        print("  2. 笔记数量偏少，建议保持每周2-3篇的发布频率")
    print("  3. 选题建议：考试季攻略、校园美食/周边、实习经验分享")
    print("  4. 互动建议：在笔记结尾加引导语（「你怎么看？」「评论区聊聊」）")
    print()

    # 保存原始数据
    data_file = DATA_DIR / f"xhs_notes_{now.strftime('%Y%m%d_%H%M')}.json"
    data_file.write_text(json.dumps(notes, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"📁 原始数据已保存：{data_file}")


async def main():
    print("🔍 正在抓取立信小狐的所有笔记...")
    notes = await fetch_all_notes()
    print(f"✅ 共获取 {len(notes)} 篇笔记\n")
    analyze(notes)


if __name__ == "__main__":
    asyncio.run(main())
