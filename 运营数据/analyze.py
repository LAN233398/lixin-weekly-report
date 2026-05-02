#!/usr/bin/env python3
"""运营数据分析脚本 — 读取 数据记录.csv，输出周报/月报/趋势分析。"""

import csv
from datetime import datetime, timedelta
from collections import Counter

DATA_FILE = "数据记录.csv"


def load_data(path=DATA_FILE):
    rows = []
    with open(path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            try:
                r["日期"] = r["日期"].strip()
                r["好友总数"] = int(r["好友总数"]) if r["好友总数"].strip() else None
                r["新增好友"] = int(r["新增好友"]) if r["新增好友"].strip() else None
                r["朋友圈条数"] = int(r["朋友圈条数"]) if r["朋友圈条数"].strip() else None
                r["小红书条数"] = int(r["小红书条数"]) if r["小红书条数"].strip() else None
                r["主要内容类型"] = r.get("主要内容类型", "").strip()
                r["互动评价"] = r.get("互动评价", "").strip()
                r["备注"] = r.get("备注", "").strip()
                rows.append(r)
            except (ValueError, KeyError):
                continue
    return rows


def week_range(data, weeks_back=1):
    """取最近 N 周的数据"""
    if not data:
        return []
    latest = datetime.strptime(data[-1]["日期"], "%Y-%m-%d")
    cutoff = latest - timedelta(weeks=weeks_back)
    return [r for r in data if datetime.strptime(r["日期"], "%Y-%m-%d") >= cutoff]


def month_range(data):
    """取本月数据"""
    if not data:
        return []
    latest = datetime.strptime(data[-1]["日期"], "%Y-%m-%d")
    cutoff = latest.replace(day=1)
    return [r for r in data if datetime.strptime(r["日期"], "%Y-%m-%d") >= cutoff]


def count_days(data):
    return len([r for r in data if r["朋友圈条数"] is not None])


def sum_field(data, field):
    return sum(r[field] for r in data if r[field] is not None)


def weekly_report(data):
    """快速周数据概览"""
    week_data = week_range(data, weeks_back=1)
    if not week_data:
        print("⚠️ 本周暂无数据")
        return

    days = count_days(week_data)
    total_new = sum_field(week_data, "新增好友")
    total_wx = sum_field(week_data, "朋友圈条数")
    total_xhs = sum_field(week_data, "小红书条数")
    latest_friends = next(
        (r["好友总数"] for r in reversed(week_data) if r["好友总数"] is not None), None
    )

    print("=" * 40)
    print("📊 本周数据速览")
    print("=" * 40)
    print(f"记录天数：{days} 天")
    print(f"当前好友：{latest_friends or '未记录'}")
    print(f"新增：{total_new} 人（日均 {total_new / max(days, 1):.1f}）")
    print(f"发圈：{total_wx} 条 | 小红书：{total_xhs} 条")
    # KPI 进度
    if total_new:
        print(f"月 KPI 进度：{total_new}/160（{total_new/160*100:.0f}%）")


def prev_week_range(data):
    """取上上周数据用于对比"""
    if not data or len(data) < 2:
        return []
    latest = datetime.strptime(data[-1]["日期"], "%Y-%m-%d")
    start = latest - timedelta(weeks=2)
    end = latest - timedelta(weeks=1)
    return [
        r for r in data
        if start <= datetime.strptime(r["日期"], "%Y-%m-%d") < end
    ]


def meeting_report(data):
    """周二例会专用 — 完整周报，可直接对着讲"""
    week_data = week_range(data, weeks_back=1)
    prev_data = prev_week_range(data)

    if not week_data:
        print("⚠️ 本周暂无数据，请先填写 数据记录.csv")
        return

    days = count_days(week_data)
    total_new = sum_field(week_data, "新增好友")
    total_wx = sum_field(week_data, "朋友圈条数")
    total_xhs = sum_field(week_data, "小红书条数")

    # 好友数
    first_friends = next((r["好友总数"] for r in week_data if r["好友总数"] is not None), None)
    last_friends = next((r["好友总数"] for r in reversed(week_data) if r["好友总数"] is not None), None)
    growth = (last_friends - first_friends) if (first_friends and last_friends) else None

    # 上周对比
    prev_new = sum_field(prev_data, "新增好友") if prev_data else 0
    prev_wx = sum_field(prev_data, "朋友圈条数") if prev_data else 0
    prev_xhs = sum_field(prev_data, "小红书条数") if prev_data else 0

    # 日期范围
    first_date = week_data[0]["日期"]
    last_date = week_data[-1]["日期"]

    # 互动
    interactions = [r["互动评价"] for r in week_data if r["互动评价"]]
    counter_i = Counter(interactions)

    # 内容类型
    content_types = [r["主要内容类型"] for r in week_data if r["主要内容类型"]]
    counter_ct = Counter(content_types)

    # 备注汇总
    notes = [r["备注"] for r in week_data if r["备注"]]

    # 互动评价与内容类型交叉
    type_interaction = {}
    for r in week_data:
        ct = r["主要内容类型"]
        ie = r["互动评价"]
        if ct and ie:
            if ct not in type_interaction:
                type_interaction[ct] = []
            type_interaction[ct].append(ie)

    print("═" * 46)
    print("   🦊 小狐运营周报 — 周二例会")
    print(f"   {first_date} ~ {last_date}")
    print("═" * 46)

    # ── 一、核心数据 ──
    print("\n── 一、核心数据 ──")
    print(f"当前好友：{last_friends or '未记录'} 人", end="")
    if growth is not None:
        print(f"（周净增 {growth:+d}）")
    else:
        print()
    print(f"本周新增：{total_new} 人（日均 {total_new / max(days, 1):.1f}）", end="")
    if prev_new:
        delta = total_new - prev_new
        arrow = "↑" if delta > 0 else "↓" if delta < 0 else "→"
        print(f"  {arrow} 上周 {prev_new}")
    else:
        print()
    print(f"发布内容：朋友圈 {total_wx} 条 + 小红书 {total_xhs} 条 = {total_wx + total_xhs} 条", end="")
    if prev_wx or prev_xhs:
        delta = (total_wx + total_xhs) - (prev_wx + prev_xhs)
        arrow = "↑" if delta > 0 else "↓" if delta < 0 else "→"
        print(f"  {arrow} 上周 {prev_wx + prev_xhs}")
    else:
        print()

    # ── 二、本周做了什么 ──
    print("\n── 二、本周做了什么 ──")
    if notes:
        for i, note in enumerate(notes, 1):
            print(f"  {i}. {note}")
    else:
        print("  （备注为空，建议每天花 30 秒在备注列随手记一笔）")

    # ── 三、内容表现 ──
    print("\n── 三、内容表现 ──")
    if interactions:
        high = counter_i.get("高", 0)
        mid = counter_i.get("中", 0)
        low = counter_i.get("低", 0)
        total_i = high + mid + low
        print(f"高互动 {high} 条 | 中互动 {mid} 条 | 低互动 {low} 条")
        if total_i:
            print(f"高互动占比：{high / total_i * 100:.0f}%")
    else:
        print("暂未记录互动评价，填了才有分析")

    # 内容类型 + 互动交叉
    if type_interaction:
        print("\n内容类型 × 互动交叉：")
        for ct, ies in sorted(type_interaction.items(), key=lambda x: -x[1].count("高")):
            ct_counter = Counter(ies)
            parts = []
            if ct_counter.get("高"):
                parts.append(f"高×{ct_counter['高']}")
            if ct_counter.get("中"):
                parts.append(f"中×{ct_counter['中']}")
            if ct_counter.get("低"):
                parts.append(f"低×{ct_counter['低']}")
            print(f"  {ct}：{' | '.join(parts)}")

    # ── 四、类型分布 ──
    if content_types:
        print("\n── 四、内容类型分布 ──")
        for ct, n in counter_ct.most_common():
            bar = "█" * n
            print(f"  {ct}：{n} 条 {bar}")

    # ── 五、下周方向 ──
    print("\n── 五、下周方向建议 ──")
    # 根据本周数据给建议
    suggestions = []

    # 如果内容少
    if total_wx + total_xhs < 7:
        suggestions.append("本周内容产出偏少（日均不到 1 条），下周目标每条至少 1 条朋友圈")
    # 如果高互动占比低
    if interactions:
        high = counter_i.get("高", 0)
        mid = counter_i.get("中", 0)
        low = counter_i.get("低", 0)
        total_i = high + mid + low
        if total_i > 0 and high / total_i < 0.3:
            suggestions.append("高互动内容占比不到 30%，下周试试多从朋友圈「刷到好内容私聊要授权」的方式挖掘素材")
    # 如果新增少
    if total_new < 10 and days >= 5:
        suggestions.append("新增好友偏低（日均 < 2），下周可以多发一条小红书引流到微信")
    # 如果某类内容表现好
    if type_interaction:
        best_type = None
        best_high = -1
        for ct, ies in type_interaction.items():
            hc = ies.count("高")
            if hc > best_high:
                best_high = hc
                best_type = ct
        if best_type and best_high > 0:
            suggestions.append(f"「{best_type}」类内容互动最高，下周加大这类内容的产出")
    # 毕业季提示（5-6月）
    now = datetime.now()
    if now.month in [5, 6]:
        suggestions.append("5-6 月是毕业季黄金窗口，大四学生的毕业照展示意愿最强，趁这段时间多收集毕业相关内容")

    if not suggestions:
        suggestions.append("数据量还不够，坚持记录，下周会有更精准的建议")

    for i, s in enumerate(suggestions, 1):
        print(f"  {i}. {s}")

    print("\n" + "═" * 46)


def monthly_report(data):
    """输出月报"""
    month_data = month_range(data)
    if not month_data:
        print("⚠️ 本月暂无数据")
        return

    days = count_days(month_data)
    total_new = sum_field(month_data, "新增好友")
    total_wx = sum_field(month_data, "朋友圈条数")
    total_xhs = sum_field(month_data, "小红书条数")

    # 好友增长
    first = next((r["好友总数"] for r in month_data if r["好友总数"] is not None), None)
    last = next(
        (r["好友总数"] for r in reversed(month_data) if r["好友总数"] is not None), None
    )
    growth = (last - first) if (first and last) else None

    print("=" * 40)
    print("📈 小狐运营月报")
    print("=" * 40)
    print(f"记录天数：{days} 天")
    print(f"月初好友：{first or '未记录'}  →  月末好友：{last or '未记录'}")
    if growth is not None:
        print(f"月净增：{growth} 人")
    print(f"月新增合计：{total_new} 人（日均 {total_new / max(days, 1):.1f} 人）")
    print(f"月发圈：{total_wx} 条（日均 {total_wx / max(days, 1):.1f} 条）")
    print(f"月小红书：{total_xhs} 条（日均 {total_xhs / max(days, 1):.1f} 条）")

    # KPI 进度（领导要求月增 160）
    if total_new:
        pct = total_new / 160 * 100
        bar = "█" * int(pct / 10) + "░" * (10 - int(pct / 10))
        print(f"\n🎯 KPI 进度（月增 160）：{total_new}/160 [{bar}] {pct:.0f}%")

    interactions = [r["互动评价"] for r in month_data if r["互动评价"]]
    if interactions:
        counter = Counter(interactions)
        print(f"\n互动分布：高 {counter.get('高',0)} | 中 {counter.get('中',0)} | 低 {counter.get('低',0)}")

    content_types = [
        r["主要内容类型"] for r in month_data if r["主要内容类型"]
    ]
    if content_types:
        print(f"\n内容类型 TOP 3：")
        for ct, n in Counter(content_types).most_common(3):
            print(f"  {ct}: {n} 条")


def trend(data):
    """输出好友增长趋势"""
    print("=" * 40)
    print("📉 好友增长趋势")
    print("=" * 40)

    valid = [r for r in data if r["好友总数"] is not None]
    if len(valid) < 2:
        print("至少需要 2 条记录才能看趋势")
        return

    for i in range(1, len(valid)):
        prev = valid[i - 1]
        curr = valid[i]
        diff = (curr["好友总数"] or 0) - (prev["好友总数"] or 0)
        sign = "+" if diff >= 0 else ""
        bar = "█" * min(abs(diff), 20) if diff > 0 else ""
        print(f"  {curr['日期']}  {sign}{diff}  {bar}")

    first = valid[0]["好友总数"]
    last = valid[-1]["好友总数"]
    days = (
        datetime.strptime(valid[-1]["日期"], "%Y-%m-%d")
        - datetime.strptime(valid[0]["日期"], "%Y-%m-%d")
    ).days
    if first and last and days > 0:
        print(f"\n总计增长：{last - first:+d} 人 / {days} 天")
        print(f"日均增长：{(last - first) / days:.1f} 人")


def main():
    import sys

    data = load_data()
    if not data:
        print("还没有数据，先从 数据记录.csv 开始记录吧！")
        return

    cmd = sys.argv[1] if len(sys.argv) > 1 else "meeting"

    if cmd == "meeting":
        meeting_report(data)
    elif cmd == "week":
        weekly_report(data)
    elif cmd == "month":
        monthly_report(data)
    elif cmd == "trend":
        trend(data)
    elif cmd == "all":
        trend(data)
        print()
        meeting_report(data)
        print()
        monthly_report(data)
    else:
        print("用法: python analyze.py [meeting|week|month|trend|all]")
        print("  meeting  周二例会完整报告（默认）")
        print("  week     快速数据速览")
        print("  month    月报 + KPI 进度")
        print("  trend    好友增长趋势")
        print("  all      全部报告")


if __name__ == "__main__":
    main()
