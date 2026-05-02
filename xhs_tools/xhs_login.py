"""
小红书登录脚本 — 手动扫码后自动保存浏览器状态+用户信息
"""
import asyncio
import json
import sys
from pathlib import Path
from playwright.async_api import async_playwright

AUTH_FILE = Path(__file__).parent.parent / "secrets" / "xhs_auth.json"
PROFILE_FILE = Path(__file__).parent.parent / "secrets" / "xhs_profile.json"


async def login():
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
            args=["--disable-blink-features=AutomationControlled"],
        )
        context = await browser.new_context(
            viewport={"width": 1280, "height": 800},
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

        # 打开小红书
        print("正在打开小红书...")
        await page.goto(
            "https://www.xiaohongshu.com/explore",
            wait_until="domcontentloaded",
            timeout=60000,
        )
        await page.wait_for_timeout(3000)

        # 尝试点击侧边栏"登录"或页面上的登录按钮
        login_selectors = [
            'text=登录',
            'span:has-text("登录")',
            '[class*="login"]',
        ]
        clicked = False
        for sel in login_selectors:
            btn = await page.query_selector(sel)
            if btn:
                text = (await btn.inner_text()).strip()
                if "登录" in text and "退出" not in text:
                    await btn.click()
                    print(f"点击了登录按钮: [{text}]")
                    clicked = True
                    break

        if not clicked:
            print("未找到登录按钮，可能已登录")

        print("\n" + "=" * 50)
        print("请用小红书 App 扫码登录")
        print("扫码完成后等待页面刷新...")
        print("=" * 50 + "\n")

        # 等待登录完成 — 检测多种可能的登录成功标志
        logged_in = False
        for i in range(60):  # 最多等 5 分钟
            await page.wait_for_timeout(5000)

            # 检查侧边栏是否从"登录"变成"我"
            sidebar = await page.query_selector('[class*="side"]')
            if sidebar:
                text = await sidebar.inner_text()
                if "我" in text and "登录" not in text.split("我")[0] if "我" in text else False:
                    logged_in = True
                    print("✅ 检测到侧边栏出现「我」")
                    break

            # 检查URL变化（有些登录方式会跳转）
            if "/login" not in page.url:
                # 不包含login说明可能已经跳出了登录页
                pass

            print(f"  等待登录中... ({i+1}/60)")

        if not logged_in:
            print("⚠️  超时未检测到登录成功，继续保存状态...")

        await page.wait_for_timeout(3000)

        # 提取用户信息
        profile_url = None
        nickname = None
        user_id = None

        try:
            # 方法1：从侧边栏的用户链接获取
            me_link = await page.query_selector('[class*="side"] a[href*="profile"]')
            if me_link:
                profile_url = await me_link.get_attribute("href")
                nickname = (await me_link.inner_text()).strip()

            # 方法2：点击"我"进入个人主页
            if not profile_url:
                # 点击侧边栏的"我"
                me_btns = await page.query_selector_all('[class*="side"] [class*="channel"]')
                for btn in me_btns:
                    text = (await btn.inner_text()).strip()
                    if text == "我":
                        await btn.click()
                        await page.wait_for_timeout(3000)
                        profile_url = page.url
                        break

            # 从URL提取用户ID
            if profile_url and "/user/profile/" in profile_url:
                user_id = profile_url.split("/user/profile/")[1].split("?")[0].split("/")[0]

            # 方法3：从cookie提取
            if not user_id:
                cookies = await context.cookies()
                for c in cookies:
                    if c["name"] == "id_token" and c["value"]:
                        parts = c["value"].split(".")
                        if len(parts) >= 2:
                            import base64
                            payload = parts[1]
                            payload += "=" * (4 - len(payload) % 4)
                            try:
                                data = json.loads(base64.b64decode(payload))
                                user_id = data.get("userId") or data.get("sub")
                                nickname = nickname or data.get("nickname") or data.get("name")
                            except Exception:
                                pass

            # 方法4：从 __INITIAL_STATE__ 提取
            if not user_id:
                user_info = await page.evaluate("""
                    () => {
                        const st = window.__INITIAL_STATE__;
                        if (!st || !st.user || !st.user.userInfo) return null;
                        const info = st.user.userInfo;
                        // Vue ref - try _value
                        const val = info._value || info;
                        if (val && typeof val === 'object') {
                            return {
                                id: val.id || val.userId || val.redId,
                                nickname: val.nickname || val.name || val.redId,
                            };
                        }
                        return null;
                    }
                """)
                if user_info:
                    user_id = user_info.get("id")
                    nickname = nickname or user_info.get("nickname")

        except Exception as e:
            print(f"⚠️  提取用户信息时出错: {e}")

        # 保存
        AUTH_FILE.parent.mkdir(parents=True, exist_ok=True)
        await context.storage_state(path=str(AUTH_FILE))

        profile_data = {
            "user_id": user_id,
            "nickname": nickname,
            "profile_url": f"https://www.xiaohongshu.com/user/profile/{user_id}" if user_id else None,
        }
        PROFILE_FILE.write_text(json.dumps(profile_data, ensure_ascii=False, indent=2), encoding="utf-8")

        print(f"\n✅ 登录状态已保存: {AUTH_FILE}")
        print(f"✅ 用户信息已保存: {PROFILE_FILE}")
        if nickname:
            print(f"   👤 {nickname} (ID: {user_id})")
        if profile_url:
            print(f"   🔗 {profile_url}")

        await browser.close()
        print("\n现在可以使用 python xhs_monitor.py 查看评论了")


async def check_login():
    """快速检查登录状态"""
    if not AUTH_FILE.exists():
        print("❌ 未找到登录状态，请先运行: python xhs_login.py")
        return False

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled"],
        )
        context = await browser.new_context(
            storage_state=str(AUTH_FILE),
            viewport={"width": 1280, "height": 800},
            locale="zh-CN",
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/131.0.0.0 Safari/537.36",
        )
        page = await context.new_page()
        await page.add_init_script(
            "Object.defineProperty(navigator, 'webdriver', { get: () => false });"
        )

        await page.goto(
            "https://www.xiaohongshu.com/explore",
            wait_until="domcontentloaded",
            timeout=60000,
        )
        await page.wait_for_timeout(3000)

        # 更可靠的检查：看侧边栏
        sidebar = await page.query_selector('[class*="side"]')
        is_logged_in = False
        if sidebar:
            text = await sidebar.inner_text()
            is_logged_in = "我" in text and "登录" not in text
            # 二次确认：找"退出登录"
            body_text = await page.inner_text("body")
            if "退出登录" in body_text:
                is_logged_in = True

        await browser.close()

        if is_logged_in:
            print("✅ 登录状态有效")
        else:
            print("❌ 登录已过期，请重新运行: python xhs_login.py")
        return is_logged_in


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--check":
        asyncio.run(check_login())
    else:
        asyncio.run(login())
