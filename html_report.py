"""
HTML 周报模板生成器
生成带仪表盘、图表、KPI 卡片的独立 HTML 文件
"""
from datetime import datetime


def generate_html_report(
    week_start: str,
    week_end: str,
    generated_at: str,
    # KPI 数据
    kpi: dict,
    # 笔记排行榜: [(title, likes, url), ...]
    top_notes: list,
    # 点赞分布: {label: count}
    like_dist: dict,
    # 内容类型表现: {type: (count, avg_likes)}
    content_types: dict,
    # 竞品数据: [(name, notes, avg_likes, prev_avg, trend, status), ...]
    competitors: list,
    # 微信数据
    wechat_rows: list,
    wechat_empty: bool = True,
    # Logo: data URI 字符串，如 "data:image/jpeg;base64,..."
    logo_base64: str = "",
    # AI 诊断: [str, ...]
    insights: list = None,
    # 策略建议: [str, ...]
    strategies: list = None,
    # 待办: [str, ...]
    todos: list = None,
) -> str:
    """生成完整的 HTML 周报"""

    # ====== 生成 KPI 卡片 HTML ======
    kpi_cards_html = ""
    for item in kpi.get("cards", []):
        change_html = ""
        if item.get("change"):
            cls = "up" if "📈" in item["change"] else ("down" if "📉" in item["change"] else "")
            change_html = f'<span class="change {cls}">{item["change"]}</span>'
        kpi_cards_html += f"""
        <div class="kpi-card">
            <div class="kpi-icon">{item.get('icon', '📊')}</div>
            <div class="kpi-value">{item['value']}</div>
            <div class="kpi-label">{item['label']}</div>
            {change_html}
        </div>"""

    # ====== 笔记排行榜表格 ======
    notes_rows = ""
    for i, (title, likes, url) in enumerate(top_notes):
        likes_int = int(likes) if likes else 0
        badge = "🔥" if likes_int >= 20 else ("⭐" if likes_int >= 10 else "")
        url_html = f'<a href="{url}" target="_blank" class="note-link">🔗</a>' if url else ""
        notes_rows += f"""
        <tr>
            <td class="rank">{i+1}</td>
            <td class="title">{badge} {title}</td>
            <td class="likes">{likes} 👍</td>
            <td>{url_html}</td>
        </tr>"""

    # ====== 竞品表格 ======
    comp_rows = ""
    for name, notes, avg, prev_avg, trend, status in competitors:
        status_cls = "active" if "🟢" in status else ("normal" if "🟡" in status else "inactive")
        comp_rows += f"""
        <tr>
            <td>{name}</td>
            <td>{notes}</td>
            <td><strong>{avg}</strong></td>
            <td>{prev_avg}</td>
            <td>{trend}</td>
            <td><span class="status {status_cls}">{status}</span></td>
        </tr>"""

    # ====== 微信数据 ======
    if not wechat_empty and wechat_rows:
        wx_rows_html = ""
        for row in wechat_rows:
            wx_rows_html += f"""
            <tr>
                <td>{row.get('date', '-')}</td>
                <td>{row.get('type', '-')}</td>
                <td>{row.get('eval', '-')}</td>
                <td>{row.get('note', '-')}</td>
            </tr>"""
        wechat_section = f"""
        <div class="section">
            <h2>💚 微信朋友圈回顾</h2>
            <div class="table-wrap">
            <table>
                <thead><tr><th>日期</th><th>内容类型</th><th>互动</th><th>备注</th></tr></thead>
                <tbody>{wx_rows_html}</tbody>
            </table>
            </div>
        </div>"""
    else:
        wechat_section = """
        <div class="section">
            <h2>💚 微信朋友圈回顾</h2>
            <div class="empty-state">⚠️ 本周微信数据未记录，请在 <code>运营数据/数据记录.csv</code> 中按日填写</div>
        </div>"""

    # ====== 图表数据 (JSON) ======
    like_dist_json = str(like_dist).replace("'", '"') if like_dist else "{}"
    content_type_labels = [c for c in content_types] if content_types else []
    content_type_avgs = [content_types[c][1] for c in content_type_labels] if content_types else []
    content_type_counts = [content_types[c][0] for c in content_type_labels] if content_types else []

    # ====== AI 诊断 ======
    insights_html = ""
    if insights:
        for s in insights:
            cls = "warn" if "⚠️" in s else ("good" if "✅" in s else ("tip" if "💡" in s else ""))
            insights_html += f'<li class="insight-item {cls}">{s}</li>'

    # ====== 策略建议 ======
    strategies_html = ""
    if strategies:
        for i, s in enumerate(strategies, 1):
            strategies_html += f'<li class="strategy-item">{s}</li>'

    # ====== 待办清单 ======
    todos_html = ""
    if todos:
        for t in todos:
            checked = 'checked' if t.startswith('[x]') else ''
            text = t.replace('[x] ', '').replace('[ ] ', '')
            todos_html += f"""
            <label class="todo-item">
                <input type="checkbox" {checked} disabled>
                <span>{text}</span>
            </label>"""

    # ====== 完整 HTML ======
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>立信小狐 运营周报 | {week_start} - {week_end}</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<style>
:root {{
  --bg: #f5f6fa;
  --card-bg: #ffffff;
  --text: #2d3436;
  --text-secondary: #636e72;
  --accent: #6c5ce7;
  --accent2: #a29bfe;
  --gradient: linear-gradient(135deg, #6c5ce7 0%, #a29bfe 50%, #fd79a8 100%);
  --green: #00b894;
  --red: #e17055;
  --yellow: #fdcb6e;
  --shadow: 0 2px 12px rgba(0,0,0,0.06);
  --radius: 14px;
}}
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", sans-serif;
  background: var(--bg);
  color: var(--text);
  line-height: 1.6;
  -webkit-font-smoothing: antialiased;
}}

/* ── Header ── */
.header {{
  background: var(--gradient);
  color: white;
  padding: 32px 32px 24px;
  text-align: center;
}}
.header-inner {{
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 20px;
  max-width: 600px;
  margin: 0 auto;
}}
.logo {{
  width: 64px;
  height: 64px;
  border-radius: 16px;
  object-fit: cover;
  background: white;
  padding: 3px;
  box-shadow: 0 4px 16px rgba(0,0,0,0.15);
  flex-shrink: 0;
}}
.header-text {{ text-align: left; }}
.header-text h1 {{ font-size: 24px; font-weight: 700; margin-bottom: 2px; }}
.header-text .subtitle {{ opacity: 0.85; font-size: 13px; }}
.header-text .generated {{ opacity: 0.6; font-size: 11px; margin-top: 2px; }}
@media (max-width: 480px) {{
  .header-inner {{ flex-direction: column; gap: 10px; }}
  .header-text {{ text-align: center; }}
  .logo {{ width: 48px; height: 48px; border-radius: 12px; }}
}}

/* ── Container ── */
.container {{ max-width: 960px; margin: 0 auto; padding: 24px 20px 48px; }}

/* ── KPI Cards ── */
.kpi-grid {{
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
  gap: 14px;
  margin-bottom: 28px;
}}
.kpi-card {{
  background: var(--card-bg);
  border-radius: var(--radius);
  padding: 20px 16px;
  text-align: center;
  box-shadow: var(--shadow);
  transition: transform 0.15s;
}}
.kpi-card:hover {{ transform: translateY(-2px); }}
.kpi-icon {{ font-size: 26px; margin-bottom: 6px; }}
.kpi-value {{ font-size: 28px; font-weight: 700; color: var(--accent); }}
.kpi-label {{ font-size: 13px; color: var(--text-secondary); margin-top: 2px; }}
.kpi-card .change {{ font-size: 13px; margin-top: 4px; display: inline-block; padding: 1px 8px; border-radius: 10px; }}
.kpi-card .change.up {{ color: #00b894; background: #e6fff8; }}
.kpi-card .change.down {{ color: #e17055; background: #fff0ed; }}

/* ── Section ── */
.section {{
  background: var(--card-bg);
  border-radius: var(--radius);
  box-shadow: var(--shadow);
  padding: 24px;
  margin-bottom: 20px;
}}
.section h2 {{ font-size: 18px; margin-bottom: 16px; display: flex; align-items: center; gap: 8px; }}

/* ── Charts Row ── */
.charts-row {{
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
  margin-bottom: 20px;
}}
@media (max-width: 600px) {{ .charts-row {{ grid-template-columns: 1fr; }} }}
.chart-box {{
  background: var(--card-bg);
  border-radius: var(--radius);
  box-shadow: var(--shadow);
  padding: 20px;
}}
.chart-box h3 {{ font-size: 15px; margin-bottom: 12px; color: var(--text-secondary); }}
.chart-box canvas {{ max-height: 260px; }}

/* ── Tables ── */
.table-wrap {{ overflow-x: auto; }}
table {{ width: 100%; border-collapse: collapse; font-size: 14px; }}
thead th {{
  background: #f8f9fd;
  color: var(--text-secondary);
  font-weight: 600;
  padding: 10px 12px;
  text-align: left;
  border-bottom: 2px solid #eee;
  font-size: 13px;
  white-space: nowrap;
}}
tbody td {{
  padding: 10px 12px;
  border-bottom: 1px solid #f1f2f6;
}}
tbody tr:hover {{ background: #fafafe; }}
td.rank {{ font-weight: 700; color: var(--accent); width: 30px; }}
td.title {{ max-width: 300px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }}
td.likes {{ font-weight: 600; white-space: nowrap; }}
.note-link {{ text-decoration: none; font-size: 14px; }}

/* ── Status badges ── */
.status {{ font-size: 12px; padding: 2px 8px; border-radius: 8px; }}
.status.active {{ background: #e6fff8; color: #00b894; }}
.status.normal {{ background: #fff8e6; color: #e17055; }}
.status.inactive {{ background: #f1f2f6; color: #b2bec3; }}

/* ── Insights ── */
.insight-list {{ list-style: none; padding: 0; }}
.insight-item {{
  padding: 10px 16px;
  margin: 6px 0;
  border-radius: 10px;
  font-size: 14px;
  line-height: 1.6;
}}
.insight-item.warn {{ background: #fff8f0; border-left: 4px solid #e17055; }}
.insight-item.good {{ background: #f0fff6; border-left: 4px solid #00b894; }}
.insight-item.tip {{ background: #f8f0ff; border-left: 4px solid #6c5ce7; }}

.strategy-list {{ padding-left: 20px; }}
.strategy-item {{ margin: 8px 0; font-size: 14px; line-height: 1.7; }}

/* ── Todo ── */
.todo-list {{ display: flex; flex-direction: column; gap: 8px; }}
.todo-item {{
  display: flex; align-items: center; gap: 10px;
  padding: 10px 14px;
  background: #fafafe;
  border-radius: 10px;
  font-size: 14px;
  cursor: default;
}}
.todo-item input[type="checkbox"] {{ width: 18px; height: 18px; accent-color: var(--accent); }}

/* ── Empty State ── */
.empty-state {{
  text-align: center;
  padding: 28px;
  color: var(--text-secondary);
  font-size: 14px;
  background: #fafafe;
  border-radius: 10px;
}}
.empty-state code {{ background: #eee; padding: 2px 6px; border-radius: 4px; font-size: 12px; }}

/* ── Footer ── */
.footer {{
  text-align: center;
  color: var(--text-secondary);
  font-size: 12px;
  padding: 24px;
  opacity: 0.7;
}}

/* ── Print ── */
@media print {{
  body {{ background: white; }}
  .header {{ background: var(--accent) !important; -webkit-print-color-adjust: exact; }}
  .section, .chart-box, .kpi-card {{ box-shadow: none; break-inside: avoid; }}
}}
</style>
</head>
<body>

<div class="header">
    <div class="header-inner">
        <img class="logo" src="{logo_base64 or ''}" alt="小狐" onerror="this.style.display='none'">
        <div class="header-text">
            <h1>立信小狐 · 运营周报</h1>
            <div class="subtitle">📅 {week_start}（周一）— {week_end}（周日）</div>
            <div class="generated">生成时间：{generated_at}（北京时间）</div>
        </div>
    </div>
</div>

<div class="container">

    <!-- KPI 仪表盘 -->
    <div class="kpi-grid">{kpi_cards_html}
    </div>

    <!-- 图表区 -->
    <div class="charts-row">
        <div class="chart-box">
            <h3>📈 点赞分布</h3>
            <canvas id="likeChart"></canvas>
        </div>
        <div class="chart-box">
            <h3>🏷️ 内容类型均赞对比</h3>
            <canvas id="typeChart"></canvas>
        </div>
    </div>

    <!-- 笔记排行榜 -->
    <div class="section">
        <h2>📝 笔记排行榜 TOP 10</h2>
        <div class="table-wrap">
        <table>
            <thead><tr><th>#</th><th>标题</th><th>点赞</th><th>链接</th></tr></thead>
            <tbody>{notes_rows}
            </tbody>
        </table>
        </div>
    </div>

    <!-- 竞品动态 -->
    <div class="section">
        <h2>🔍 竞品动态</h2>
        <div class="table-wrap">
        <table>
            <thead><tr><th>账号</th><th>笔记数</th><th>均赞</th><th>上周均赞</th><th>趋势</th><th>状态</th></tr></thead>
            <tbody>{comp_rows}
            </tbody>
        </table>
        </div>
    </div>

    {wechat_section}

    <!-- AI 分析 -->
    <div class="section">
        <h2>🤖 AI 策略分析</h2>
        <h3 style="font-size:15px;color:var(--text-secondary);margin-bottom:10px;">📊 本周诊断</h3>
        <ul class="insight-list">{insights_html}
        </ul>
        <h3 style="font-size:15px;color:var(--text-secondary);margin:18px 0 10px;">🎯 下周策略建议</h3>
        <ol class="strategy-list">{strategies_html}
        </ol>
    </div>

    <!-- 下周待办 -->
    <div class="section">
        <h2>✅ 下周待办清单</h2>
        <div class="todo-list">{todos_html}
        </div>
    </div>

</div>

<div class="footer">
    🤖 由 Claude Code 自动生成 · 每周二更新 · 立信小狐运营数据追踪系统
</div>

<script>
// 点赞分布饼图
new Chart(document.getElementById('likeChart'), {{
    type: 'doughnut',
    data: {{
        labels: {list(like_dist.keys()) if like_dist else []},
        datasets: [{{
            data: {list(like_dist.values()) if like_dist else []},
            backgroundColor: ['#dfe6e9', '#a29bfe', '#6c5ce7', '#fd79a8', '#00b894'],
            borderWidth: 2,
            borderColor: '#fff'
        }}]
    }},
    options: {{
        responsive: true,
        plugins: {{ legend: {{ position: 'bottom', labels: {{ padding: 16, font: {{ size: 12 }} }} }} }}
    }}
}});

// 内容类型柱状图
new Chart(document.getElementById('typeChart'), {{
    type: 'bar',
    data: {{
        labels: {content_type_labels},
        datasets: [{{
            label: '均赞',
            data: {content_type_avgs},
            backgroundColor: ['#6c5ce7', '#a29bfe', '#fd79a8', '#00b894', '#fdcb6e', '#74b9ff'],
            borderRadius: 8,
            borderWidth: 0
        }}]
    }},
    options: {{
        responsive: true,
        plugins: {{ legend: {{ display: false }} }},
        scales: {{ y: {{ beginAtZero: true, grid: {{ color: '#f1f2f6' }} }}, x: {{ grid: {{ display: false }} }} }}
    }}
}});
</script>

</body>
</html>"""


def build_kpi_cards(
    note_count, total_likes, avg_likes, max_likes, new_notes_count,
    prev_note_count=0, prev_total=0, prev_avg=0,
    wx_friends="-", wx_new="-", wx_posts="-"
) -> dict:
    """构建 KPI 卡片数据"""

    def _chg(cur, prev):
        if not prev:
            return ""
        diff = cur - prev
        pct = round(diff / prev * 100, 1)
        sign = "+" if diff > 0 else ""
        arrow = "📈" if diff > 0 else ("📉" if diff < 0 else "➡️")
        return f"{arrow} {sign}{pct}%"

    cards = [
        {"icon": "📝", "value": str(note_count), "label": "笔记总数",
         "change": _chg(note_count, prev_note_count) if prev_note_count else ""},
        {"icon": "❤️", "value": str(total_likes), "label": "总点赞",
         "change": _chg(total_likes, prev_total) if prev_total else ""},
        {"icon": "📊", "value": str(avg_likes), "label": "平均点赞",
         "change": _chg(avg_likes, prev_avg) if prev_avg else ""},
        {"icon": "🔥", "value": str(max_likes), "label": "最高单篇", "change": ""},
        {"icon": "🆕", "value": str(new_notes_count), "label": "本周新发", "change": ""},
        {"icon": "💚", "value": str(wx_friends), "label": "微信好友",
         "change": f"新增 {wx_new}" if wx_new and wx_new != "-" else ""},
    ]
    return {"cards": cards}
