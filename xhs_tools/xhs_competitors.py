"""
小红书竞品分析 — 比较立信校园类账号数据
"""
import asyncio
import json
from pathlib import Path
from playwright.async_api import async_playwright

AUTH_FILE = Path(__file__).parent.parent / "secrets" / "xhs_auth.json"
DATA_DIR = Path(__file__).parent.parent / "运营数据"
DATA_DIR.mkdir(exist_ok=True)

# 竞品账号列表（从搜索结果中提取）
COMPETITORS = {
    "上海立信-小狐": "6693c6650000000003032688",
    "上海立信小狮哥": "68649cba000000001d00b3dc",
    "立信解忧铺": "61a34ad0000000000201f480",
    "在立信": "68494353000000001b01ab42",
    "Bibi在立信": "5edf9eef0000000001002fc4",
}

# 立信小狐作为参照
MYSELF = {"立信小狐": "67a485ca000000000500d396"}


async def fetch_profile(browser, context, uid: str):
    """访问一个用户主页，抓取API数据"""
    page = await context.new_page()
    await page.add_init_script(
        "Object.defineProperty(navigator, 'webdriver', { get: () => false });"
    )

    responses = {}

    async def on_resp(resp):
        url = resp.url
        if "user_posted" in url or "user/me" in url:
            try:
                body = await resp.text()
                key = "user_posted" if "user_posted" in url else "user_me"
                if key not in responses:
                    responses[key] = body
            except Exception:
                pass

    page.on("response", on_resp)

    try:
        await page.goto(
            f"https://www.xiaohongshu.com/user/profile/{uid}",
            wait_until="domcontentloaded",
            timeout=30000,
        )
        await page.wait_for_timeout(5000)

        # 滚动加载
        for _ in range(5):
            await page.evaluate("window.scrollBy(0, 800)")
            await page.wait_for_timeout(1500)

        # 从页面提取粉丝/笔记数
        body_text = await page.inner_text("body")
        lines = body_text.split("\n")

        follower_count = ""
        note_count = ""
        desc = ""
        nickname = ""

        for line in lines:
            s = line.strip()
            if not s:
                continue
            if "粉丝" in s and s != "粉丝":
                follower_count = s
            if "笔记" in s and s != "笔记":
                note_count = s
            if "小红书号" in line and not nickname:
                # 上一行可能是昵称
                idx = lines.index(line)
                for j in range(idx - 1, max(idx - 5, 0), -1):
                    candidate = lines[j].strip()
                    if candidate and len(candidate) > 1 and "粉丝" not in candidate:
                        nickname = candidate
                        break

        # 提取简介
        for i, line in enumerate(lines):
            if "小红书号" in line:
                for j in range(i + 1, min(i + 5, len(lines))):
                    s = lines[j].strip()
                    if s and len(s) > 5 and "IP" not in s and "粉丝" not in s and "笔记" not in s:
                        desc = s
                        break
                break

        # 解析 user_me 数据
        if "user_me" in responses:
            try:
                me_data = json.loads(responses["user_me"])
                user_info = me_data.get("data", {})
                if user_info.get("nickname"):
                    nickname = user_info["nickname"]
                if user_info.get("desc"):
                    desc = user_info["desc"]
            except Exception:
                pass

        # 解析笔记数据
        notes = []
        if "user_posted" in responses:
            try:
                data = json.loads(responses["user_posted"])
                if data.get("success") and data.get("data", {}).get("notes"):
                    notes = data["data"]["notes"]
            except Exception:
                pass

        total_likes = sum(
            int(n.get("interact_info", {}).get("liked_count", 0)) for n in notes
        )
        avg_likes = total_likes / len(notes) if notes else 0

        # 找TOP5笔记
        sorted_notes = sorted(
            notes,
            key=lambda n: int(n.get("interact_info", {}).get("liked_count", 0)),
            reverse=True,
        )
        top5 = [
            {
                "title": n.get("display_title", "")[:50],
                "likes": n.get("interact_info", {}).get("liked_count", "0"),
                "note_id": n.get("note_id", ""),
            }
            for n in sorted_notes[:5]
        ]

        await page.close()
        return {
            "nickname": nickname,
            "follower_info": follower_count,
            "note_info": note_count,
            "desc": desc[:200],
            "notes_captured": len(notes),
            "total_likes": total_likes,
            "avg_likes": round(avg_likes, 1),
            "top5": top5,
        }

    except Exception as e:
        await page.close()
        return {"error": str(e)}


async def main():
    if not AUTH_FILE.exists():
        print("❌ 请先运行 python xhs_login.py")
        return

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

        all_data = {}

        # 分析立信小狐自己
        print("=" * 60)
        print("  分析: 立信小狐（自身参照）")
        myself_data = await fetch_profile(browser, context, MYSELF["立信小狐"])
        all_data["立信小狐"] = myself_data
        print(f"  粉丝: {myself_data.get('follower_info')}")
        print(f"  笔记: {myself_data.get('note_info')}")
        print(f"  抓取: {myself_data.get('notes_captured')}篇, 均赞{myself_data.get('avg_likes')}")

        # 分析竞品
        for name, uid in COMPETITORS.items():
            sep = "=" * 60
            print(f"\n{sep}")
            print(f"  分析: {name}")
            data = await fetch_profile(browser, context, uid)
            all_data[name] = data

            if "error" in data:
                print(f"  ❌ 失败: {data['error']}")
            else:
                print(f"  昵称: {data.get('nickname')}")
                print(f"  粉丝: {data.get('follower_info')}")
                print(f"  笔记: {data.get('note_info')}")
                print(f"  简介: {data.get('desc', '')[:100]}")
                print(f"  抓取笔记: {data.get('notes_captured')}篇")
                print(f"  总点赞: {data.get('total_likes')}")
                print(f"  均赞: {data.get('avg_likes')}")
                if data.get("top5"):
                    print(f"  TOP5笔记:")
                    for i, n in enumerate(data["top5"]):
                        print(f"    {i+1}. [{n['likes']}👍] {n['title']}")

        await browser.close()

        # 保存数据
        out_file = DATA_DIR / "competitors_data.json"
        out_file.write_text(json.dumps(all_data, ensure_ascii=False, indent=2))
        print(f"\n📁 数据已保存: {out_file}")

        # ===== 对比报告 =====
        print("\n\n" + "=" * 70)
        print("  立信校园类小红书账号 — 竞品分析报告")
        print("=" * 70)

        print(f"\n{'账号':<16} {'粉丝':<14} {'笔记数':<10} {'总赞':<8} {'均赞':<8} {'状态':<10}")
        print("-" * 70)

        for name, d in all_data.items():
            if "error" in d:
                print(f"{name:<16} {'(无法访问)':<14}")
                continue
            follower = d.get("follower_info", "?")
            note_info = d.get("note_info", "?")
            notes = d.get("notes_captured", 0)
            total = d.get("total_likes", 0)
            avg = d.get("avg_likes", 0)
            status = "🟢 活跃" if notes > 30 else ("🟡 一般" if notes > 10 else "🔴 低活跃")
            print(f"{name:<16} {follower:<14} {note_info:<10} {total:<8} {avg:<8} {status}")

        # 洞察
        print("\n📊 关键发现")
        print("-" * 70)

        xiaohu = all_data.get("立信小狐", {})
        xiaohu_likes = xiaohu.get("avg_likes", 0)
        xiaohu_notes = xiaohu.get("notes_captured", 0)

        print(f"  立信小狐：{xiaohu_notes}篇笔记，均赞{xiaohu_likes}")

        better_than = 0
        worse_than = 0
        for name, d in all_data.items():
            if name == "立信小狐" or "error" in d:
                continue
            avg = d.get("avg_likes", 0)
            notes = d.get("notes_captured", 0)
            if avg > xiaohu_likes:
                better_than += 1
                print(f"  ⚠️  {name} 均赞({avg}) 高于立信小狐({xiaohu_likes}) — 笔记{notes}篇")
            else:
                worse_than += 1

        if better_than == 0:
            print(f"  ✅ 立信小狐均赞({xiaohu_likes})高于所有竞品")

        print(f"\n  总竞品数: {len(COMPETITORS)}")
        print(f"  均赞高于小狐: {better_than}")
        print(f"  均赞低于小狐: {worse_than}")

        print("\n💡 竞品策略启示")
        print("-" * 70)
        print("  1. 关注「在立信」— 最新活跃的立信类账号，观察其选题方向")
        print("  2. 「上海立信小狮哥」— 男生视角的校园内容，差异化定位")
        print("  3. 立信小红书校园赛道竞争不激烈，是抢占心智的好时机")


if __name__ == "__main__":
    asyncio.run(main())
