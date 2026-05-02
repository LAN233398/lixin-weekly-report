"""
立信小狐 运营周报生成器
用法:
  python weekly_report.py           仅生成本地周报
  python weekly_report.py --push    生成周报 + 自动推送到 GitHub Pages
每周二自动运行，整合小红书数据 + 微信数据 + 竞品对比，生成完整周报
"""
import asyncio
import base64
import json
import csv
import sys
from pathlib import Path
from datetime import datetime, timedelta

PROJECT_DIR = Path(__file__).parent
DATA_DIR = PROJECT_DIR / "运营数据"
REPORT_DIR = DATA_DIR / "周报"
SECRETS_DIR = PROJECT_DIR / "secrets"
XHS_TOOLS = PROJECT_DIR / "xhs_tools"

REPORT_DIR.mkdir(parents=True, exist_ok=True)
DOCS_DIR = PROJECT_DIR / "docs"
DOCS_DIR.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(XHS_TOOLS))
sys.path.insert(0, str(PROJECT_DIR))

from html_report import generate_html_report, build_kpi_cards


def get_week_range():
    """获取本周一至周日日期"""
    today = datetime.now()
    monday = today - timedelta(days=today.weekday())
    sunday = monday + timedelta(days=6)
    return monday, sunday


def read_wechat_csv():
    """读取微信数据 CSV"""
    csv_path = DATA_DIR / "数据记录.csv"
    if not csv_path.exists():
        return []
    with open(csv_path, "r", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def load_previous_xhs_notes():
    """加载上一次保存的小红书笔记数据，用于环比"""
    files = sorted(DATA_DIR.glob("xhs_notes_*.json"))
    if len(files) >= 2:
        return json.loads(files[-2].read_text(encoding="utf-8"))
    elif len(files) == 1:
        return json.loads(files[0].read_text(encoding="utf-8"))
    return None


def load_previous_competitor_data():
    """加载上一次竞品数据"""
    comp_file = DATA_DIR / "competitors_data.json"
    if comp_file.exists():
        return json.loads(comp_file.read_text(encoding="utf-8"))
    return {}


def calc_change(current, previous, label="", inverse=False):
    """计算环比变化，返回格式化的变化字符串"""
    if previous is None or previous == 0:
        return "-"
    diff = current - previous
    pct = round(diff / previous * 100, 1)
    sign = "+" if diff > 0 else ""
    arrow = "📈" if diff > 0 else ("📉" if diff < 0 else "➡️")
    if inverse:
        arrow = "📉" if diff > 0 else ("📈" if diff < 0 else "➡️")
    return f"{arrow} {sign}{pct}%"


def classify_note(title: str) -> str:
    """自动分类笔记"""
    title = title or ""
    keywords_map = {
        "话题讨论": ["最", "离谱", "凭什么", "吐槽", "雷", "真的", "居然", "什么", "怎么", "谁"],
        "实用攻略": ["攻略", "预约", "查", "怎么", "如何", "教程", "申请", "流程"],
        "新生指南": ["新生", "指南", "开学", "班委", "试点班", "VPN", "导生", "导师", "辅修", "插班生", "饮水", "辅导员", "课外活动", "课表"],
        "校园生活": ["好吃", "咖啡", "食堂", "图书馆", "校园", "立信", "松江", "浦东", "宿舍"],
        "征集互动": ["征集", "投稿", "评论区", "晒", "分享", "聊聊"],
        "情绪表达": ["讨厌", "喜欢", "爱", "想", "感觉", "emo"],
    }
    for cat, keywords in keywords_map.items():
        if any(kw in title for kw in keywords):
            return cat
    return "其他"


def generate_report(xhs_notes: list, prev_xhs_notes: list, wechat_data: list,
                     competitor_data: dict, prev_competitor: dict) -> str:
    """生成完整周报"""
    now = datetime.now()
    monday, sunday = get_week_range()

    # ===== 计算指标 =====
    total_likes = sum(int(n.get("interact_info", {}).get("liked_count", 0)) for n in xhs_notes)
    avg_likes = round(total_likes / len(xhs_notes), 1) if xhs_notes else 0
    max_likes = max((int(n.get("interact_info", {}).get("liked_count", 0)) for n in xhs_notes), default=0)
    note_count = len(xhs_notes)

    # 上期指标
    prev_total = sum(int(n.get("interact_info", {}).get("liked_count", 0)) for n in prev_xhs_notes) if prev_xhs_notes else 0
    prev_avg = round(prev_total / len(prev_xhs_notes), 1) if prev_xhs_notes else 0
    prev_count = len(prev_xhs_notes) if prev_xhs_notes else 0

    # 新的笔记数（本周新增）
    if prev_xhs_notes:
        prev_ids = {n.get("note_id") for n in prev_xhs_notes}
        new_notes = [n for n in xhs_notes if n.get("note_id") not in prev_ids]
    else:
        new_notes = []

    # 微信数据
    wx_friends = "-"
    wx_new = "-"
    wx_posts = "-"
    if wechat_data:
        latest = wechat_data[-1]
        wx_friends = latest.get("好友总数", "-")
        wx_new = latest.get("新增好友", "-")
        wx_posts = latest.get("朋友圈条数", "-")

    # ===== 构建报告 =====
    L = []  # lines

    L.append("# 📋 立信小狐 运营周报")
    L.append(f"> 📅 {monday.strftime('%m/%d')}（周一）— {sunday.strftime('%m/%d')}（周日）")
    L.append(f"> 🕐 生成时间：{now.strftime('%Y年%m月%d日 %H:%M')}（北京时间）")
    L.append("")

    # ─── 一、核心指标仪表盘 ───
    L.append("## 一、核心指标仪表盘")
    L.append("")
    L.append("| 平台 | 指标 | 本周 | 上周 | 环比 |")
    L.append("|------|------|------|------|------|")
    L.append(f"| 📕 小红书 | 笔记总数 | {note_count} | {prev_count if prev_count else '-'} | {calc_change(note_count, prev_count)} |")
    L.append(f"| 📕 小红书 | 总点赞 | {total_likes} | {prev_total if prev_total else '-'} | {calc_change(total_likes, prev_total)} |")
    L.append(f"| 📕 小红书 | 平均点赞 | {avg_likes} | {prev_avg if prev_avg else '-'} | {calc_change(avg_likes, prev_avg)} |")
    L.append(f"| 📕 小红书 | 最高单篇 | {max_likes} | - | - |")
    L.append(f"| 📕 小红书 | 本周新发 | {len(new_notes)} 篇 | - | - |")
    L.append(f"| 💚 微信 | 好友总数 | {wx_friends} | - | - |")
    L.append(f"| 💚 微信 | 本周新增好友 | {wx_new} | - | - |")
    L.append(f"| 💚 微信 | 本周发圈 | {wx_posts} | - | - |")
    L.append("")

    # ─── 二、小红书数据详情 ───
    L.append("## 二、小红书数据详情")
    L.append("")

    # 笔记排行榜
    sorted_notes = sorted(xhs_notes,
                          key=lambda n: int(n.get("interact_info", {}).get("liked_count", 0)),
                          reverse=True)
    L.append("### 📝 笔记排行榜（按点赞）")
    L.append("")
    L.append("| # | 标题 | 点赞 | 类型 |")
    L.append("|---|------|------|------|")
    for i, n in enumerate(sorted_notes):
        title = (n.get("display_title") or "(无标题)")[:45]
        likes = n.get("interact_info", {}).get("liked_count", "0")
        ntype = n.get("type", "图文")
        L.append(f"| {i+1} | {title} | {likes} | {ntype} |")
    L.append("")

    # 点赞分布
    like_ranges = {"0赞": 0, "1-5赞": 0, "6-10赞": 0, "11-20赞": 0, "20+赞": 0}
    for n in xhs_notes:
        lc = int(n.get("interact_info", {}).get("liked_count", 0))
        if lc == 0: like_ranges["0赞"] += 1
        elif lc <= 5: like_ranges["1-5赞"] += 1
        elif lc <= 10: like_ranges["6-10赞"] += 1
        elif lc <= 20: like_ranges["11-20赞"] += 1
        else: like_ranges["20+赞"] += 1

    L.append("### 📈 点赞分布")
    L.append("")
    for label, count in like_ranges.items():
        pct = round(count / len(xhs_notes) * 100, 1) if xhs_notes else 0
        bar = "█" * min(count, 30)
        L.append(f"- **{label}**：{count} 篇（{pct}%）{bar}")
    L.append("")

    # 内容类型分析
    L.append("### 🏷️ 内容类型表现")
    L.append("")
    cats = {}
    for n in xhs_notes:
        title = n.get("display_title") or ""
        cat = classify_note(title)
        if cat not in cats:
            cats[cat] = {"count": 0, "likes": 0, "titles": []}
        lc = int(n.get("interact_info", {}).get("liked_count", 0))
        cats[cat]["count"] += 1
        cats[cat]["likes"] += lc
        cats[cat]["titles"].append((title[:30], lc))

    L.append("| 类型 | 篇数 | 总赞 | 均赞 | 占比 |")
    L.append("|------|------|------|------|------|")
    for cat in sorted(cats, key=lambda c: cats[c]["likes"] / cats[c]["count"], reverse=True):
        d = cats[cat]
        avg_cat = round(d["likes"] / d["count"], 1)
        pct = round(d["count"] / len(xhs_notes) * 100, 1)
        L.append(f"| {cat} | {d['count']} | {d['likes']} | {avg_cat} | {pct}% |")
    L.append("")

    # 本周新发笔记
    if new_notes:
        L.append("### 🆕 本周新发笔记")
        L.append("")
        for n in new_notes:
            title = (n.get("display_title") or "(无标题)")[:50]
            likes = n.get("interact_info", {}).get("liked_count", "0")
            nid = n.get("note_id", "")
            L.append(f"- [{likes}👍] {title}")
            L.append(f"  https://www.xiaohongshu.com/explore/{nid}")
        L.append("")

    # ─── 三、竞品动态 ───
    L.append("## 三、竞品动态")
    L.append("")
    L.append("| 账号 | 笔记数 | 均赞 | 上周均赞 | 趋势 | 状态 |")
    L.append("|------|--------|------|----------|------|------|")
    for name, data in competitor_data.items():
        if not isinstance(data, dict) or "error" in data:
            L.append(f"| {name} | ❌ 获取失败 | - | - | - | - |")
            continue
        notes_c = data.get("notes_captured", 0)
        avg_c = data.get("avg_likes", 0)

        prev_avg_c = "-"
        trend = "-"
        if name in prev_competitor:
            prev_d = prev_competitor[name]
            if isinstance(prev_d, dict) and "error" not in prev_d:
                prev_avg_c = prev_d.get("avg_likes", 0)
                if isinstance(avg_c, (int, float)) and isinstance(prev_avg_c, (int, float)) and prev_avg_c > 0:
                    trend = calc_change(avg_c, prev_avg_c)

        status = "🟢 活跃" if notes_c > 30 else ("🟡 一般" if notes_c > 10 else "🔴 低活跃")
        L.append(f"| {name} | {notes_c} | {avg_c} | {prev_avg_c} | {trend} | {status} |")
    L.append("")

    # ─── 四、微信朋友圈回顾 ───
    L.append("## 四、微信朋友圈回顾")
    L.append("")
    this_week_data = []
    if wechat_data and monday:
        for row in wechat_data:
            try:
                d = datetime.strptime(row.get("日期", ""), "%Y-%m-%d")
                if monday <= d <= sunday:
                    this_week_data.append(row)
            except ValueError:
                pass

    if this_week_data:
        L.append("### 本周发布记录")
        L.append("")
        L.append("| 日期 | 内容类型 | 互动评价 | 备注 |")
        L.append("|------|----------|----------|------|")
        for row in this_week_data:
            date = row.get("日期", "")[-5:]  # MM-DD
            ctype = row.get("主要内容类型", "-")
            ev = row.get("互动评价", "-")
            note = row.get("备注", "-")
            L.append(f"| {date} | {ctype} | {ev} | {note} |")
    else:
        L.append("> ⚠️ 本周微信数据未记录。请在 `运营数据/数据记录.csv` 中按日填写。")
    L.append("")

    # ─── 五、AI 策略分析 ───
    L.append("## 五、AI 策略分析 & 下周建议")
    L.append("")

    # 诊断
    low_count = like_ranges.get("0赞", 0) + like_ranges.get("1-5赞", 0)
    low_pct = round(low_count / note_count * 100, 1) if note_count else 0
    high_count = like_ranges.get("20+赞", 0)

    L.append("### 📊 本周诊断")
    L.append("")

    insights = []
    if avg_likes < 8:
        insights.append(f"- ⚠️ **均赞偏低**（{avg_likes}），低于 10 的健康线。建议减少纯信息型内容，增加情绪钩子。")
    elif avg_likes >= 15:
        insights.append(f"- ✅ **均赞良好**（{avg_likes}），内容策略方向正确，继续保持。")

    if low_pct > 70:
        insights.append(f"- ⚠️ **低效内容占比过高**：{low_count}/{note_count} 篇（{low_pct}%）点赞 ≤5。这些内容消耗精力但产出低，应大幅缩减。")
    if high_count >= 2:
        insights.append(f"- ✅ **爆款产出稳定**：{high_count} 篇笔记超过 20 赞，可作为内容方向的验证信号。")

    # 内容类型分析
    best_cat = max(cats, key=lambda c: cats[c]["likes"] / cats[c]["count"], default=None) if cats else None
    worst_cat = min(cats, key=lambda c: cats[c]["likes"] / cats[c]["count"], default=None) if cats else None
    if best_cat and worst_cat and best_cat != worst_cat:
        insights.append(f"- 💡 **表现最好**：「{best_cat}」类（均赞 {round(cats[best_cat]['likes']/cats[best_cat]['count'], 1)}）；**表现最差**：「{worst_cat}」类（均赞 {round(cats[worst_cat]['likes']/cats[worst_cat]['count'], 1)}）。建议将 {worst_cat} 类内容减少或融入 {best_cat} 类的表达方式。")

    # 竞品洞察
    for name, data in competitor_data.items():
        if name == "立信小狐" or not isinstance(data, dict):
            continue
        comp_avg = data.get("avg_likes", 0)
        if isinstance(comp_avg, (int, float)) and isinstance(avg_likes, (int, float)) and comp_avg > avg_likes * 1.5:
            insights.append(f"- 👀 **竞品警惕**：「{name}」均赞 {comp_avg}，是我们的 {round(comp_avg/avg_likes, 1)} 倍。建议研究其最近热门笔记的选题和标题套路。")

    if not insights:
        insights.append("- 数据量较少，暂无法生成有意义的诊断。建议持续记录 2-3 周后再做趋势分析。")

    for line in insights:
        L.append(line)
    L.append("")

    # 策略建议
    L.append("### 🎯 下周策略建议")
    L.append("")

    strategy_count = 1
    L.append(f"{strategy_count}. **选题方向**：增加话题讨论类和实用攻略类内容，这类在过去数据中互动最高。")
    strategy_count += 1
    if low_pct > 50:
        L.append(f"{strategy_count}. **精简低效内容**：{worst_cat}类内容均赞最低，建议从每周发布计划中缩减或暂停。")
        strategy_count += 1
    L.append(f"{strategy_count}. **标题优化**：使用情绪词+悬念结构，而非平铺直叙的「XX指南——XX篇」格式。")
    strategy_count += 1
    L.append(f"{strategy_count}. **发布节奏**：保持每周 4-6 篇，重点覆盖周一/三/五/六/日晚间。")
    strategy_count += 1
    L.append(f"{strategy_count}. **微信联动**：小红书爆款笔记可截图发朋友圈引流，朋友圈高质量内容可同步到小红书。")
    strategy_count += 1
    L.append(f"{strategy_count}. **评论区运营**：发笔记后用 xhs_monitor.py 监控评论，及时回复互动，必要时用小号暖场。")
    L.append("")

    # ─── 六、下周待办清单 ───
    L.append("## 六、下周待办清单")
    L.append("")
    L.append("- [ ] 发布至少 4 篇小红书笔记（话题讨论 ×1 + 实用攻略 ×1 + 人设日常 ×2）")
    L.append("- [ ] 微信朋友圈保持日更（≥5 条/周）")
    L.append("- [ ] 每日在 `数据记录.csv` 中记录微信数据")
    L.append("- [ ] 用 `xhs_monitor.py` 检查评论 + 通知至少 2 次")
    L.append("- [ ] 关注竞品「上海立信-小狐」本周新发内容")
    L.append("")

    L.append("---")
    L.append(f"*🤖 本报告由 Claude Code 自动生成 | 下次更新：下周二*")
    L.append(f"*📁 历史周报：{REPORT_DIR}/*")

    return "\n".join(L)


async def collect_competitor_data():
    """收集竞品数据（复用 xhs_competitors 的逻辑）"""
    from playwright.async_api import async_playwright
    from xhs_competitors import COMPETITORS, MYSELF, fetch_profile

    AUTH_FILE = SECRETS_DIR / "xhs_auth.json"
    if not AUTH_FILE.exists():
        print("  ⚠️ 未找到登录状态，跳过竞品数据")
        return {}

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
        print("  📊 抓取立信小狐...")
        all_data["立信小狐"] = await fetch_profile(browser, context, MYSELF["立信小狐"])

        for name, uid in COMPETITORS.items():
            print(f"  📊 抓取 {name}...")
            all_data[name] = await fetch_profile(browser, context, uid)

        await browser.close()
        return all_data


async def main():
    print()
    print("=" * 55)
    print("   🦊 立信小狐 · 运营周报生成器")
    print("=" * 55)

    # ─── Step 1: 小红书笔记数据 ───
    print("\n📕 Step 1/4: 获取小红书笔记数据...")
    xhs_notes = []
    try:
        from xhs_analyze import fetch_all_notes
        xhs_notes = await fetch_all_notes()
        if xhs_notes:
            print(f"  ✅ 获取到 {len(xhs_notes)} 篇笔记")
        else:
            raise Exception("返回空数据")
    except Exception as e:
        print(f"  ⚠️ 实时获取失败 ({e})，加载最近缓存...")
        files = sorted(DATA_DIR.glob("xhs_notes_*.json"), reverse=True)
        if files:
            xhs_notes = json.loads(files[0].read_text(encoding="utf-8"))
            print(f"  ✅ 加载缓存: {files[0].name} ({len(xhs_notes)} 篇)")

    # 加载上期数据用于环比
    prev_xhs_notes = load_previous_xhs_notes()
    if prev_xhs_notes:
        print(f"  📎 上期数据: {len(prev_xhs_notes)} 篇笔记")

    # ─── Step 2: 微信数据 ───
    print("\n💚 Step 2/4: 读取微信数据...")
    wechat_data = read_wechat_csv()
    if wechat_data:
        print(f"  ✅ {len(wechat_data)} 条记录")
        latest = wechat_data[-1]
        print(f"  📎 最新: {latest.get('日期', '?')} | 好友 {latest.get('好友总数', '?')} | 新增 {latest.get('新增好友', '?')}")
    else:
        print("  ⚠️ 未找到微信数据，周报中微信部分将留空")

    # ─── Step 3: 竞品数据 ───
    print("\n🔍 Step 3/4: 收集竞品数据...")
    competitor_data = {}
    try:
        competitor_data = await collect_competitor_data()
        print(f"  ✅ {len(competitor_data)} 个账号")
    except Exception as e:
        print(f"  ⚠️ 获取失败 ({e})，加载缓存...")
        comp_file = DATA_DIR / "competitors_data.json"
        if comp_file.exists():
            competitor_data = json.loads(comp_file.read_text(encoding="utf-8"))
            print(f"  ✅ 加载缓存数据")

    # 上期竞品数据
    prev_competitor = load_previous_competitor_data()

    # ─── Step 4: 生成报告 ───
    print("\n📝 Step 4/4: 生成周报...")
    report = generate_report(
        xhs_notes, prev_xhs_notes,
        wechat_data, competitor_data, prev_competitor
    )

    now = datetime.now()
    monday, sunday = get_week_range()

    filename_base = f"周报_{now.strftime('%Y%m%d')}"

    # ─── 保存 Markdown 报告 ───
    md_path = REPORT_DIR / f"{filename_base}.md"
    md_path.write_text(report, encoding="utf-8")
    latest_md = REPORT_DIR / "最新周报.md"
    latest_md.write_text(report, encoding="utf-8")

    # ─── 生成 HTML 报告 ───
    print("\n🌐 生成 HTML 报告...")

    # 计算 HTML 所需数据（复用 generate_report 中的逻辑）
    total_likes = sum(int(n.get("interact_info", {}).get("liked_count", 0)) for n in xhs_notes)
    avg_likes = round(total_likes / len(xhs_notes), 1) if xhs_notes else 0
    max_likes = max((int(n.get("interact_info", {}).get("liked_count", 0)) for n in xhs_notes), default=0)

    prev_total = sum(int(n.get("interact_info", {}).get("liked_count", 0)) for n in prev_xhs_notes) if prev_xhs_notes else 0
    prev_avg = round(prev_total / len(prev_xhs_notes), 1) if prev_xhs_notes else 0
    prev_count = len(prev_xhs_notes) if prev_xhs_notes else 0

    if prev_xhs_notes:
        prev_ids = {n.get("note_id") for n in prev_xhs_notes}
        new_notes_count = len([n for n in xhs_notes if n.get("note_id") not in prev_ids])
    else:
        new_notes_count = 0

    wx_friends = "-"
    wx_new = "-"
    if wechat_data:
        latest_wx = wechat_data[-1]
        wx_friends = latest_wx.get("好友总数", "-")
        wx_new = latest_wx.get("新增好友", "-")

    # KPI 卡片
    kpi = build_kpi_cards(
        note_count=len(xhs_notes), total_likes=total_likes, avg_likes=avg_likes,
        max_likes=max_likes, new_notes_count=new_notes_count,
        prev_note_count=prev_count, prev_total=prev_total, prev_avg=prev_avg,
        wx_friends=wx_friends, wx_new=wx_new,
    )

    # 笔记排行榜
    sorted_notes = sorted(xhs_notes, key=lambda n: int(
        n.get("interact_info", {}).get("liked_count", 0)), reverse=True)
    top_notes = []
    for n in sorted_notes[:10]:
        title = (n.get("display_title") or "(无标题)")[:45]
        likes = n.get("interact_info", {}).get("liked_count", "0")
        nid = n.get("note_id", "")
        url = f"https://www.xiaohongshu.com/explore/{nid}" if nid else ""
        top_notes.append((title, likes, url))

    # 点赞分布
    like_dist = {"0赞": 0, "1-5赞": 0, "6-10赞": 0, "11-20赞": 0, "20+赞": 0}
    for n in xhs_notes:
        lc = int(n.get("interact_info", {}).get("liked_count", 0))
        if lc == 0: like_dist["0赞"] += 1
        elif lc <= 5: like_dist["1-5赞"] += 1
        elif lc <= 10: like_dist["6-10赞"] += 1
        elif lc <= 20: like_dist["11-20赞"] += 1
        else: like_dist["20+赞"] += 1

    # 内容类型表现
    cats = {}
    for n in xhs_notes:
        title = n.get("display_title") or ""
        cat = classify_note(title)
        if cat not in cats:
            cats[cat] = {"count": 0, "likes": 0}
        cats[cat]["count"] += 1
        cats[cat]["likes"] += int(n.get("interact_info", {}).get("liked_count", 0))
    content_types = {}
    for cat, d in sorted(cats.items(), key=lambda x: x[1]["likes"] / x[1]["count"], reverse=True):
        content_types[cat] = (d["count"], round(d["likes"] / d["count"], 1))

    # 竞品数据
    competitors = []
    for name, data in competitor_data.items():
        if not isinstance(data, dict) or "error" in data:
            continue
        notes_c = data.get("notes_captured", 0)
        avg_c = data.get("avg_likes", 0)
        prev_avg_c = "-"
        trend = "-"
        if name in prev_competitor:
            prev_d = prev_competitor[name]
            if isinstance(prev_d, dict) and "error" not in prev_d:
                prev_avg_c_val = prev_d.get("avg_likes", 0)
                prev_avg_c = str(prev_avg_c_val)
                if isinstance(avg_c, (int, float)) and isinstance(prev_avg_c_val, (int, float)) and prev_avg_c_val > 0:
                    trend = calc_change(avg_c, prev_avg_c_val)
        status = "🟢 活跃" if notes_c > 30 else ("🟡 一般" if notes_c > 10 else "🔴 低活跃")
        competitors.append((name, notes_c, avg_c, prev_avg_c, trend, status))

    # 微信数据
    this_week_wx = []
    if wechat_data:
        for row in wechat_data:
            try:
                d = datetime.strptime(row.get("日期", ""), "%Y-%m-%d")
                if monday <= d <= sunday:
                    this_week_wx.append({
                        "date": row.get("日期", "")[-5:],
                        "type": row.get("主要内容类型", "-"),
                        "eval": row.get("互动评价", "-"),
                        "note": row.get("备注", "-"),
                    })
            except ValueError:
                pass

    # AI 诊断
    low_count = like_dist.get("0赞", 0) + like_dist.get("1-5赞", 0)
    low_pct = round(low_count / len(xhs_notes) * 100, 1) if xhs_notes else 0
    high_count = like_dist.get("20+赞", 0)
    insights = []
    if avg_likes < 8:
        insights.append(f"- ⚠️ 均赞偏低（{avg_likes}），低于 10 的健康线。建议减少纯信息型内容，增加情绪钩子。")
    elif avg_likes >= 15:
        insights.append(f"- ✅ 均赞良好（{avg_likes}），内容策略方向正确，继续保持。")
    if low_pct > 70:
        insights.append(f"- ⚠️ 低效内容占比过高：{low_count}/{len(xhs_notes)} 篇（{low_pct}%）点赞 ≤5。这些内容消耗精力但产出低，应大幅缩减。")
    if high_count >= 2:
        insights.append(f"- ✅ 爆款产出稳定：{high_count} 篇笔记超过 20 赞，可作为内容方向的验证信号。")
    best_cat = max(cats, key=lambda c: cats[c]["likes"] / cats[c]["count"], default=None) if cats else None
    worst_cat = min(cats, key=lambda c: cats[c]["likes"] / cats[c]["count"], default=None) if cats else None
    if best_cat and worst_cat and best_cat != worst_cat:
        insights.append(f"- 💡 表现最好：「{best_cat}」类（均赞 {round(cats[best_cat]['likes']/cats[best_cat]['count'], 1)}）；表现最差：「{worst_cat}」类（均赞 {round(cats[worst_cat]['likes']/cats[worst_cat]['count'], 1)}）。建议将 {worst_cat} 类内容减少或融入 {best_cat} 类的表达方式。")
    for name, data in competitor_data.items():
        if name == "立信小狐" or not isinstance(data, dict):
            continue
        comp_avg = data.get("avg_likes", 0)
        if isinstance(comp_avg, (int, float)) and isinstance(avg_likes, (int, float)) and comp_avg > avg_likes * 1.5:
            insights.append(f"- 👀 竞品警惕：「{name}」均赞 {comp_avg}，是我们的 {round(comp_avg/avg_likes, 1)} 倍。建议研究其最近热门笔记的选题和标题套路。")
    if not insights:
        insights.append("- 数据量较少，暂无法生成有意义的诊断。建议持续记录 2-3 周后再做趋势分析。")

    # 策略建议
    worst_cat_name = worst_cat if worst_cat else "低效"
    strategies = [
        "选题方向：增加话题讨论类和实用攻略类内容，这类在过去数据中互动最高。",
        f"精简低效内容：{worst_cat_name}类内容均赞最低，建议从每周发布计划中缩减或暂停。" if low_pct > 50 else "保持现有内容类型比例，持续观察数据变化。",
        "标题优化：使用情绪词+悬念结构，而非平铺直叙的「XX指南——XX篇」格式。",
        "发布节奏：保持每周 4-6 篇，重点覆盖周一/三/五/六/日晚间。",
        "微信联动：小红书爆款笔记可截图发朋友圈引流，朋友圈高质量内容可同步到小红书。",
        "评论区运营：发笔记后用 xhs_monitor.py 监控评论，及时回复互动，必要时用小号暖场。",
    ]

    # 待办
    todos = [
        "[ ] 发布至少 4 篇小红书笔记（话题讨论 ×1 + 实用攻略 ×1 + 人设日常 ×2）",
        "[ ] 微信朋友圈保持日更（≥5 条/周）",
        "[ ] 每日在数据记录.csv 中记录微信数据",
        "[ ] 用 xhs_monitor.py 检查评论 + 通知至少 2 次",
        "[ ] 关注竞品「上海立信-小狐」本周新发内容",
    ]

    # 读取 Logo 图片
    logo_base64 = ""
    logo_path = Path("/Users/lanyijun/Pictures/work picture/小狐logo.jpg")
    if logo_path.exists():
        logo_base64 = "data:image/jpeg;base64," + base64.b64encode(
            logo_path.read_bytes()
        ).decode()
        print(f"  🖼️ Logo 已加载: {logo_path.name}")

    html = generate_html_report(
        week_start=monday.strftime("%m/%d"),
        week_end=sunday.strftime("%m/%d"),
        generated_at=now.strftime("%Y年%m月%d日 %H:%M"),
        logo_base64=logo_base64,
        kpi=kpi,
        top_notes=top_notes,
        like_dist=like_dist,
        content_types=content_types,
        competitors=competitors,
        wechat_rows=this_week_wx,
        wechat_empty=len(this_week_wx) == 0,
        insights=insights,
        strategies=strategies,
        todos=todos,
    )

    html_path = REPORT_DIR / f"{filename_base}.html"
    html_path.write_text(html, encoding="utf-8")
    latest_html = REPORT_DIR / "最新周报.html"
    latest_html.write_text(html, encoding="utf-8")

    # GitHub Pages: docs/index.html
    docs_index = DOCS_DIR / "index.html"
    docs_index.write_text(html, encoding="utf-8")

    print(f"  ✅ Markdown: {md_path}")
    print(f"  ✅ HTML:     {html_path}")
    print(f"  ✅ 最新:     {latest_html}")
    print(f"  ✅ GitHub Pages: {docs_index}")

    # ─── 自动推送 ───
    if "--push" in sys.argv:
        print("\n🚀 推送到 GitHub Pages...")
        import subprocess
        try:
            subprocess.run(["git", "add", "docs/index.html",
                            "运营数据/周报/"], check=True)
            subprocess.run(["git", "commit", "-m",
                            f"📋 周报更新 {now.strftime('%Y%m%d')}"], check=True)
            subprocess.run(["git", "push", "origin", "main"], check=True)
            print(f"  ✅ 已推送！访问 https://lan233398.github.io/lixin-weekly-report/")
        except subprocess.CalledProcessError as e:
            print(f"  ⚠️ 推送失败: {e}（可手动 git push）")


if __name__ == "__main__":
    asyncio.run(main())
