"""
小红书自动操作脚本 — 加载已保存的登录状态，执行各种操作
运行前请先执行 python xhs_login.py 完成登录
"""
import asyncio
import sys
from pathlib import Path
from playwright.async_api import async_playwright

AUTH_FILE = Path(__file__).parent.parent / "secrets" / "xhs_auth.json"


async def open_xhs(headless: bool = False):
    """打开已登录的小红书浏览器，返回 page 对象"""
    if not AUTH_FILE.exists():
        print("❌ 未找到登录状态，请先运行: python xhs_login.py")
        sys.exit(1)

    p = await async_playwright().start()
    browser = await p.chromium.launch(headless=headless)
    context = await browser.new_context(
        storage_state=str(AUTH_FILE),
        viewport={"width": 1280, "height": 800},
        locale="zh-CN",
    )
    page = await context.new_page()
    return p, browser, context, page


async def search_notes(keyword: str, count: int = 10):
    """搜索笔记"""
    p, browser, context, page = await open_xhs()
    try:
        print(f"🔍 搜索: {keyword}")
        await page.goto(f"https://www.xiaohongshu.com/search_result?keyword={keyword}", timeout=30000)
        await page.wait_for_timeout(3000)

        # 获取笔记卡片
        cards = await page.query_selector_all(".note-item")
        print(f"找到 {len(cards)} 条笔记\n")

        for i, card in enumerate(cards[:count]):
            title_el = await card.query_selector(".title")
            author_el = await card.query_selector(".author .name")
            like_el = await card.query_selector(".like-wrapper .count")

            title = await title_el.inner_text() if title_el else "无标题"
            author = await author_el.inner_text() if author_el else "未知作者"
            likes = await like_el.inner_text() if like_el else "0"

            print(f"{i+1}. {title}")
            print(f"   作者: {author} | 点赞: {likes}")
            print()
    finally:
        await browser.close()
        await p.stop()


async def check_messages():
    """查看消息/通知"""
    p, browser, context, page = await open_xhs()
    try:
        print("📬 查看消息...")
        await page.goto("https://www.xiaohongshu.com/notification", timeout=30000)
        await page.wait_for_timeout(3000)

        # 截图保存
        screenshot_dir = Path(__file__).parent.parent / "screenshots"
        screenshot_dir.mkdir(exist_ok=True)
        await page.screenshot(path=str(screenshot_dir / "xhs_messages.png"), full_page=False)
        print(f"截图已保存: {screenshot_dir / 'xhs_messages.png'}")
    finally:
        await browser.close()
        await p.stop()


async def check_login_valid():
    """静默检查登录是否有效"""
    p, browser, context, page = await open_xhs(headless=True)
    try:
        await page.goto("https://www.xiaohongshu.com/explore", timeout=30000)
        await page.wait_for_timeout(2000)
        login_btn = await page.query_selector('text=登录')
        if login_btn:
            print("❌ 登录已过期")
            return False
        else:
            print("✅ 登录有效")
            return True
    finally:
        await browser.close()
        await p.stop()


# ========== 在这里添加你的自定义操作 ==========
async def main():
    # 示例：搜索"立信"相关笔记
    await search_notes("上海立信会计金融学院 毕业照", count=10)

    # 更多用法示例（取消注释即可使用）：
    # await check_messages()
    # await check_login_valid()


if __name__ == "__main__":
    asyncio.run(main())
