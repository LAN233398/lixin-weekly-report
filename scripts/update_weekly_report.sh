#!/bin/bash
# 立信小狐 周报自动更新脚本
# 由 launchd 每周二调用

export PATH="/usr/bin:/bin:/usr/sbin:/sbin:/usr/local/bin:$HOME/bin:$PATH"
cd "/Users/lanyijun/Library/Mobile Documents/com~apple~CloudDocs/lyj+claude"
python3 weekly_report.py --push >> "运营数据/周报/cron_$(date +%Y%m%d).log" 2>&1
