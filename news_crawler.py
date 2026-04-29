import requests
import feedparser
from datetime import datetime
import time
import random
import re
import os
import json

# ===== 配置区（按需修改）=====
CATEGORIES = {
    "智能网联": ["智能网联", "V2X", "车联网", "5G车联", "智驾"],
    "自动驾驶": ["自动驾驶", "ADAS", "Robotaxi", "L4"],
    "客车/商用车": ["客车", "商用车", "重卡", "物流车", "宇通", "比亚迪客车"]
}
MAX_ITEMS_PER_CATEGORY = 3  # 每个领域最多抓3条
# ==========================

def get_36kr_news():
    """使用稳定公开API获取36氪热榜（经测试可用）"""
    url = "https://v2.xxapi.cn/api/hot36kr"  # 替换为有效接口
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://www.36kr.com/"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()  # 检查HTTP错误状态码
        
        # 关键修复：严格校验响应内容
        if not response.text.strip():
            print("❌ 36氪API返回空数据")
            return []
        
        data = response.json()
        
        # 关键修复：验证JSON结构
        if not isinstance(data, list) or len(data) == 0:
            print(f"❌ 36氪API返回异常结构: {type(data)}")
            return []
        
        news_list = []
        for item in data[:20]:  # 仅取前20条
            title = item.get("title", "")
            url = item.get("url", "")
            if title and url:  # 确保关键字段存在
                news_list.append({"title": title, "summary": "", "url": url})
        return news_list
    
    except requests.exceptions.RequestException as e:
        print(f"❌ 网络请求失败: {str(e)}")
    except json.JSONDecodeError:
        print(f"❌ JSON解析失败 | 响应内容: {response.text[:200]}")  # 打印前200字符辅助调试
    except Exception as e:
        print(f"❌ 未知错误: {str(e)}")
    return []

def get_the_paper_news():
    """从澎湃新闻RSS获取新闻（官方RSS源）"""
    feed = feedparser.parse("https://m.thepaper.cn/rss/news.xml")
    news_list = []
    for entry in feed.entries[:20]:  # 只取最新20条
        title = entry.title
        summary = re.sub('<[^<]+?>', '', entry.summary)  # 移除HTML标签
        news_list.append({"title": title, "summary": summary, "url": entry.link})
    return news_list

def filter_by_category(news_list):
    """按行业领域分类新闻"""
    categorized = {category: [] for category in CATEGORIES}
    
    for news in news_list:
        title = news["title"] + " " + news["summary"]
        for category, keywords in CATEGORIES.items():
            if any(kw in title for kw in keywords):
                categorized[category].append({
                    "title": news["title"],
                    "url": news["url"]
                })
                break  # 匹配到一个领域即停止
    
    # 限制每类新闻数量
    for category in categorized:
        categorized[category] = categorized[category][:MAX_ITEMS_PER_CATEGORY]
    return categorized

def generate_feishu_message(categorized_news):
    """生成飞书兼容的富文本消息"""
    today = datetime.now().strftime("%Y年%m月%d日")
    blocks = [
        {
            "tag": "div",
            "text": {
                "tag": "lark_md",
                "content": f"🚗 **{today} 行业新闻速递**\n*数据来源：36氪+澎湃新闻 | 更新时间 {datetime.now().strftime('%H:%M')}*"
            }
        }
    ]
    
    for category, items in categorized_news.items():
        if not items:
            continue
            
        blocks.append({
            "tag": "div",
            "text": {"tag": "lark_md", "content": f"**{category}**"}
        })
        
        for i, item in enumerate(items, 1):
            blocks.append({
                "tag": "div",
                "text": {"tag": "lark_md", "content": f"{i}. [{item['title']}]({item['url']})"}
            })
    
    return {
        "msg_type": "interactive",
        "card": {
            "config": {"wide_screen_mode": True},
            "header": {"title": {"tag": "plain_text", "content": "📰 行业新闻日报"}},
            "elements": blocks
        }
    }

def main():
    # 获取新闻（36氪+澎湃新闻）
    news_list = get_36kr_news() + get_the_paper_news()
    
    # 分类过滤
    categorized = filter_by_category(news_list)
    
    # 生成飞书消息
    message = generate_feishu_message(categorized)
    
    # 推送到飞书
    webhook = os.getenv("https://open.feishu.cn/open-apis/bot/v2/hook/821f4e1a-59bd-4a2b-b6e5-8f35fc92c54a")
    if not webhook:
        raise ValueError("FEISHU_WEBHOOK 环境变量未设置")
    
    response = requests.post(
        webhook,
        headers={"Content-Type": "application/json"},
        data=json.dumps(message)
    )
    
    if response.status_code != 200:
        print(f"推送失败! 状态码: {response.status_code}, 响应: {response.text}")
        exit(1)
    
    # 打印成功消息（GitHub Actions日志可见）
    print(f"✅ 成功推送 {sum(len(v) for v in categorized.values())} 条行业新闻")

if __name__ == "__main__":
    main()
