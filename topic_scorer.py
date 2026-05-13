#!/usr/bin/env python3
"""
立信小狐选题评分工具 v2
用法：python topic_scorer.py
"""

import json
import csv
import os
from datetime import datetime

# 数据文件路径（跟脚本同目录）
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(SCRIPT_DIR, "topic_scores.json")

# 评分维度定义
DIMENSIONS = [
    ("search", "搜索需求", "1=没人搜 2=偶尔搜 3=很多人搜"),
    ("interaction", "互动潜力", "1=看完就走 2=可能点赞 3=想评论转发"),
    ("relevance", "立信关联", "1=通用内容 2=跟立信沾边 3=只有立信人懂"),
    ("material", "素材获取", "1=很难找 2=需花时间 3=手边就有"),
]

# 平台选项
PLATFORMS = ["小红书", "微信", "双平台"]

# 默认标签
DEFAULT_TAGS = ["攻略", "互动", "争议", "日常", "热点", "合集", "人设"]


def load_data():
    """加载已有数据（兼容旧格式）"""
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            topics = json.load(f)
        # 兼容旧数据：补充缺失字段
        changed = False
        for t in topics:
            if "platform" not in t:
                t["platform"] = "双平台"
                changed = True
            if "tags" not in t:
                t["tags"] = []
                changed = True
            if "created" not in t:
                t["created"] = ""
                changed = True
        if changed:
            save_data(topics)
        return topics
    return []


def save_data(topics):
    """保存数据到 JSON"""
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(topics, f, ensure_ascii=False, indent=2)


def get_suggestion(total):
    """根据总分给出建议"""
    if total >= 10:
        return "优先"
    elif total >= 7:
        return "值得"
    else:
        return "放弃/改良"


def get_valid_score(prompt_text):
    """获取 1-3 的有效分数"""
    while True:
        try:
            score = int(input(prompt_text))
            if 1 <= score <= 3:
                return score
            print("  ⚠️  请输入 1-3 之间的数字")
        except ValueError:
            print("  ⚠️  请输入数字")


def select_platform():
    """选择平台"""
    print("  平台选择：1=小红书  2=微信  3=双平台")
    while True:
        choice = input("  平台：").strip()
        if choice in ("1", "2", "3"):
            return PLATFORMS[int(choice) - 1]
        if choice in PLATFORMS:
            return choice
        print("  ⚠️  请输入 1-3")


def select_tags():
    """选择标签（可多选）"""
    print(f"  可选标签：{', '.join(f'{i+1}={t}' for i, t in enumerate(DEFAULT_TAGS))}")
    raw = input("  标签（逗号分隔序号，如 1,3 或直接回车跳过）：").strip()
    if not raw:
        return []
    tags = []
    for part in raw.replace("，", ",").split(","):
        part = part.strip()
        if part.isdigit() and 1 <= int(part) <= len(DEFAULT_TAGS):
            tag = DEFAULT_TAGS[int(part) - 1]
            if tag not in tags:
                tags.append(tag)
        elif part in DEFAULT_TAGS and part not in tags:
            tags.append(part)
    return tags


# ─── 添加选题 ───

def add_topic(topics):
    print("\n── 添加选题 ──")
    name = input("选题名称：").strip()
    if not name:
        print("名称不能为空")
        return

    if any(t["name"] == name for t in topics):
        print(f"「{name}」已存在，跳过")
        return

    scores = {}
    for key, label, desc in DIMENSIONS:
        scores[key] = get_valid_score(f"  {label}（{desc}）：")

    platform = select_platform()
    tags = select_tags()

    total = sum(scores.values())
    topics.append({
        "name": name,
        **scores,
        "total": total,
        "platform": platform,
        "tags": tags,
        "created": datetime.now().strftime("%Y-%m-%d"),
    })
    save_data(topics)
    tags_str = " ".join(f"#{t}" for t in tags) if tags else ""
    print(f"\n  ✅ 「{name}」已添加，总分 {total}/12 — {get_suggestion(total)}  [{platform}] {tags_str}")


# ─── 显示选题 ───

def pad_cn(s, width):
    """补全中文宽度"""
    display_len = sum(2 if ord(c) > 127 else 1 for c in s)
    return s + " " * max(0, width - display_len)


def show_topics(topics, filter_platform=None, filter_tag=None):
    """查看选题（按分数排序，支持筛选）"""
    if not topics:
        print("\n  暂无选题，先添加一个吧")
        return

    filtered = topics
    if filter_platform:
        filtered = [t for t in filtered if t["platform"] == filter_platform]
    if filter_tag:
        filtered = [t for t in filtered if filter_tag in t.get("tags", [])]

    if not filtered:
        print("\n  没有符合条件的选题")
        return

    sorted_topics = sorted(filtered, key=lambda t: t["total"], reverse=True)

    name_width = max(len(t["name"]) for t in sorted_topics)
    name_width = max(name_width, 8)

    filter_desc = ""
    if filter_platform:
        filter_desc += f" [平台={filter_platform}]"
    if filter_tag:
        filter_desc += f" [标签={filter_tag}]"

    print(f"\n{'─' * 60}")
    print(f"  共 {len(sorted_topics)} 个选题{filter_desc}")
    print(f"{'─' * 60}")

    header = f"{'选题':<{name_width}}  搜索  互动  关联  素材  总分  建议    平台    标签"
    print(header)
    print("─" * (len(header) + 10))

    for t in sorted_topics:
        name_str = pad_cn(t["name"], name_width)
        suggestion = get_suggestion(t["total"])
        platform = t.get("platform", "双平台")
        tags_str = " ".join(f"#{tag}" for tag in t.get("tags", []))
        print(
            f"{name_str}  {t['search']}     {t['interaction']}     "
            f"{t['relevance']}     {t['material']}     {t['total']:<4}  {suggestion:<4}  {platform:<6}  {tags_str}"
        )

    print()


def show_topics_menu(topics):
    """查看选题子菜单"""
    print("\n═══ 查看选题 ═══")
    print("1. 全部（按分数排序）")
    print("2. 按平台筛选")
    print("3. 按标签筛选")
    print("4. 返回主菜单")
    choice = input("选择：").strip()

    if choice == "1":
        show_topics(topics)
    elif choice == "2":
        print("  1=小红书  2=微信  3=双平台")
        p = input("  选择平台：").strip()
        if p in ("1", "2", "3"):
            show_topics(topics, filter_platform=PLATFORMS[int(p) - 1])
        else:
            print("  ⚠️  无效选择")
    elif choice == "3":
        # 收集已有标签
        all_tags = set()
        for t in topics:
            all_tags.update(t.get("tags", []))
        if not all_tags:
            print("  暂无标签数据")
            return
        tag_list = sorted(all_tags)
        print(f"  可选标签：{', '.join(f'{i+1}={t}' for i, t in enumerate(tag_list))}")
        tc = input("  选择标签序号：").strip()
        if tc.isdigit() and 1 <= int(tc) <= len(tag_list):
            show_topics(topics, filter_tag=tag_list[int(tc) - 1])
        else:
            print("  ⚠️  无效选择")


# ─── 编辑选题 ───

def edit_topic(topics):
    if not topics:
        print("\n  暂无选题可编辑")
        return

    show_topics(topics)
    name = input("输入要编辑的选题名称：").strip()
    topic = None
    for t in topics:
        if t["name"] == name:
            topic = t
            break
    if not topic:
        print(f"  未找到「{name}」")
        return

    print(f"\n── 编辑「{name}」──")
    print("1. 修改名称")
    print("2. 修改分数")
    print("3. 修改平台")
    print("4. 修改标签")
    print("5. 返回")
    choice = input("选择：").strip()

    if choice == "1":
        new_name = input(f"  新名称（当前：{name}）：").strip()
        if new_name and new_name != name:
            if any(t["name"] == new_name for t in topics):
                print(f"  「{new_name}」已存在")
                return
            topic["name"] = new_name
            save_data(topics)
            print(f"  ✅ 名称已改为「{new_name}」")

    elif choice == "2":
        print("  重新评分：")
        scores = {}
        for key, label, desc in DIMENSIONS:
            old = topic[key]
            scores[key] = get_valid_score(f"  {label}（{desc}）[当前{old}]：")
        topic.update(scores)
        topic["total"] = sum(scores.values())
        save_data(topics)
        print(f"  ✅ 分数已更新，总分 {topic['total']}/12 — {get_suggestion(topic['total'])}")

    elif choice == "3":
        print(f"  当前平台：{topic.get('platform', '双平台')}")
        topic["platform"] = select_platform()
        save_data(topics)
        print(f"  ✅ 平台已改为「{topic['platform']}」")

    elif choice == "4":
        current = ", ".join(topic.get("tags", [])) or "无"
        print(f"  当前标签：{current}")
        topic["tags"] = select_tags()
        save_data(topics)
        tags_str = ", ".join(topic["tags"]) or "无"
        print(f"  ✅ 标签已改为「{tags_str}」")


# ─── 删除选题 ───

def delete_topic(topics):
    if not topics:
        print("\n  暂无选题可删")
        return

    show_topics(topics)
    name = input("输入要删除的选题名称：").strip()
    for i, t in enumerate(topics):
        if t["name"] == name:
            confirm = input(f"  确认删除「{name}」？(y/n)：").strip().lower()
            if confirm == "y":
                topics.pop(i)
                save_data(topics)
                print(f"  🗑️  已删除「{name}」")
            else:
                print("  已取消")
            return
    print(f"  未找到「{name}」")


# ─── 统计概览 ───

def show_stats(topics):
    if not topics:
        print("\n  暂无数据可统计")
        return

    n = len(topics)
    totals = [t["total"] for t in topics]

    # 等级分布
    priority = sum(1 for t in totals if t >= 10)
    worth = sum(1 for t in totals if 7 <= t < 10)
    skip = sum(1 for t in totals if t < 7)

    # 各维度均分
    dim_avgs = {}
    for key, label, _ in DIMENSIONS:
        dim_avgs[label] = sum(t[key] for t in topics) / n

    # 平台分布
    platform_count = {}
    for t in topics:
        p = t.get("platform", "双平台")
        platform_count[p] = platform_count.get(p, 0) + 1

    # 标签统计
    tag_count = {}
    for t in topics:
        for tag in t.get("tags", []):
            tag_count[tag] = tag_count.get(tag, 0) + 1
    top_tags = sorted(tag_count.items(), key=lambda x: x[1], reverse=True)[:5]

    print(f"""
{'═' * 40}
  选题统计概览
{'═' * 40}

  总选题数：{n}
  平均总分：{sum(totals)/n:.1f}/12
  最高分：{max(totals)}    最低分：{min(totals)}

  等级分布
  ├─ 优先（10-12）：{priority} 个  {'█' * priority * 3}
  ├─ 值得（7-9）  ：{worth} 个  {'█' * worth * 3}
  └─ 放弃（1-6）  ：{skip} 个  {'█' * skip * 3}

  各维度均分""")

    for label, avg in dim_avgs.items():
        bar = "█" * int(avg * 5)
        print(f"  {label}：{avg:.1f}  {bar}")

    print(f"\n  平台分布")
    for p, c in platform_count.items():
        print(f"  {p}：{c} 个")

    if top_tags:
        print(f"\n  热门标签")
        for tag, c in top_tags:
            print(f"  #{tag}：{c} 次")

    # 最佳选题
    best = max(topics, key=lambda t: t["total"])
    print(f"\n  最佳选题：「{best['name']}」({best['total']}分)")

    print(f"\n{'═' * 40}\n")


# ─── 导出 CSV ───

def export_csv(topics):
    if not topics:
        print("\n  暂无选题可导出")
        return

    csv_path = os.path.join(SCRIPT_DIR, "topic_scores.csv")
    sorted_topics = sorted(topics, key=lambda t: t["total"], reverse=True)

    with open(csv_path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["选题", "搜索需求", "互动潜力", "立信关联", "素材获取", "总分", "建议", "平台", "标签"])
        for t in sorted_topics:
            writer.writerow([
                t["name"],
                t["search"],
                t["interaction"],
                t["relevance"],
                t["material"],
                t["total"],
                get_suggestion(t["total"]),
                t.get("platform", "双平台"),
                " ".join(t.get("tags", [])),
            ])

    print(f"\n  ✅ 已导出到 {csv_path}")


# ─── 批量添加 ───

def batch_add(topics):
    """批量添加选题（快速录入模式）"""
    print("\n── 批量添加 ──")
    print("  输入选题名称（每行一个，空行结束）：")
    names = []
    while True:
        name = input("  ").strip()
        if not name:
            break
        if any(t["name"] == name for t in topics):
            print(f"  ⚠️ 「{name}」已存在，跳过")
            continue
        names.append(name)

    if not names:
        print("  没有新选题")
        return

    print(f"\n  共 {len(names)} 个选题，统一设置平台和标签：")
    platform = select_platform()
    tags = select_tags()

    print(f"\n  开始逐个评分：")
    for name in names:
        print(f"\n  ── {name} ──")
        scores = {}
        for key, label, desc in DIMENSIONS:
            scores[key] = get_valid_score(f"  {label}（{desc}）：")
        total = sum(scores.values())
        topics.append({
            "name": name,
            **scores,
            "total": total,
            "platform": platform,
            "tags": tags,
            "created": datetime.now().strftime("%Y-%m-%d"),
        })
        print(f"  ✅ {total}分 — {get_suggestion(total)}")

    save_data(topics)
    print(f"\n  ✅ 批量添加完成，共 {len(names)} 个")


# ─── 主菜单 ───

def main():
    topics = load_data()

    print("\n🦊 立信小狐选题评分工具 v2\n")

    while True:
        n = len(topics)
        print(f"═══ 菜单（当前 {n} 个选题）═══")
        print("1. 添加选题")
        print("2. 查看选题（按分数排序 + 筛选）")
        print("3. 编辑选题")
        print("4. 删除选题")
        print("5. 统计概览")
        print("6. 批量添加")
        print("7. 导出 CSV")
        print("8. 退出\n")

        choice = input("选择（1-8）：").strip()

        if choice == "1":
            add_topic(topics)
        elif choice == "2":
            show_topics_menu(topics)
        elif choice == "3":
            edit_topic(topics)
        elif choice == "4":
            delete_topic(topics)
        elif choice == "5":
            show_stats(topics)
        elif choice == "6":
            batch_add(topics)
        elif choice == "7":
            export_csv(topics)
        elif choice == "8":
            print("👋 再见！")
            break
        else:
            print("  ⚠️  请输入 1-8")


if __name__ == "__main__":
    main()
