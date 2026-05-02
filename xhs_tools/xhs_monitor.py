"""
小红书评论监控 — 一键打开已登录浏览器，手动查看评论
用法:
  python xhs_monitor.py          打开个人主页
  python xhs_monitor.py noti     打开通知页
  python xhs_monitor.py explore  打开发现页
  python xhs_monitor.py reload   重新登录
"""
import asyncio
import json
import sys
from pathlib import Path
from playwright.async_api import async_playwright

AUTH_FILE = Path(__file__).parent.parent / "secrets" / "xhs_auth.json"
PROFILE_FILE = Path(__file__).parent.parent / "secrets" / "xhs_profile.json"

MY_USER_ID = None
if PROFILE_FILE.exists():
    data = json.loads(PROFILE_FILE.read_text(encoding="utf-8"))
    MY_USER_ID = data.get("user_id")


async def open_browser(url: str, title: str):
    """打开已登录的可见浏览器，让用户手动操作"""
    if not AUTH_FILE.exists():
        print("❌ 请先运行 python xhs_login.py 登录")
        return

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-features=IsolateOrigins,site-per-process",
            ],
        )
        context = await browser.new_context(
            storage_state=str(AUTH_FILE),
            viewport={"width": 1280, "height": 900},
            locale="zh-CN",
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/131.0.0.0 Safari/537.36"
            ),
        )
        page = await context.new_page()
        await page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => false });
        """)

        print(f"🌐 {title}")
        print(f"   链接: {url}")
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=60000)
            await page.wait_for_timeout(3000)
        except Exception as e:
            print(f"⚠️  加载超时: {e}")

        print(f"\n✅ 浏览器已打开，当前页面: {page.url}")
        print("📌 你可以在浏览器中自由操作：查看评论、回复、浏览通知等")
        print("📌 操作完成后关闭浏览器窗口，或回到这里按回车退出")
        print()

        # 等待：浏览器关闭 或 用户按 Ctrl+C
        stop_event = asyncio.Event()
        try:
            # 监听 Ctrl+C
            import signal
            loop = asyncio.get_event_loop()
            loop.add_signal_handler(signal.SIGINT, stop_event.set)
            loop.add_signal_handler(signal.SIGTERM, stop_event.set)
        except NotImplementedError:
            pass  # Windows 不支持 add_signal_handler

        print("按 Ctrl+C 关闭浏览器...")
        try:
            await stop_event.wait()
        except KeyboardInterrupt:
            pass

        await browser.close()
        print("浏览器已关闭")


async def main():
    if len(sys.argv) > 1 and sys.argv[1] == "reload":
        print("请运行: python xhs_login.py")
        return

    target = sys.argv[1] if len(sys.argv) > 1 else "profile"

    urls = {
        "profile": (
            f"https://www.xiaohongshu.com/user/profile/{MY_USER_ID}"
            if MY_USER_ID
            else "https://www.xiaohongshu.com/explore",
            "个人主页 — 点击笔记查看评论",
        ),
        "noti": (
            "https://www.xiaohongshu.com/explore",
            "通知页 — 打开后请手动点击左侧「通知」按钮",
        ),
        "explore": (
            "https://www.xiaohongshu.com/explore",
            "发现页",
        ),
    }

    if target not in urls:
        print(f"未知目标: {target}")
        print("可用: profile, noti, explore, reload")
        return

    url, title = urls[target]
    await open_browser(url, title)


if __name__ == "__main__":
    asyncio.run(main())
