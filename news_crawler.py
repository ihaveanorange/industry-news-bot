import requests
import feedparser
from datetime import datetime
import re
import os
import json

# ===== 配置区：已更新为包含AI与科技热点的关键词 =====
CATEGORIES = {
    # 原有的汽车领域（保留，以防万一）
    "智能汽车": ["智能网联", "V2X", "车联网", "智驾", "车路协同", "高精地图", "车机", "车联", "智能座舱", "车载"],
    
    # 核心新增：AI大模型与算力（匹配当前抓取到的“英伟达”、“豆包”等热点）
    "AI大模型": ["大模型", "LLM", "生成式AI", "ChatGPT", "GPT-", "Claude", "豆包", "DeepSeek", "L4", "无人驾驶", 
                 "英伟达", "NVIDIA", "AMD", "芯片", "算力", "Transformer", "AI芯片", "AI算力", "FSD"],
    
    # 新增：消费电子与科技巨头（匹配“三星”、“苹果”等热点）
    "科技消费": ["三星", "苹果", "华为", "小米", "消费电子", "AI手机", "智能硬件", "机器人", "人形机器人", "AI眼镜"]
}
MAX_ITEMS_PER_CATEGORY = 3
# =================================================

def get_36kr_news():
    print("📡 正在从36氪获取新闻...")
    apis = [
        "https://v2.xxapi.cn/api/hot36kr",
        "https://api.vvhan.com/api/hotlist/36Ke",
        "https://tenapi.cn/v2/36kr",
        "https://api.03c3.cn/api/36kr"
    ]
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": "https://www.36kr.com/"
    }
    
    for api_url in apis:
        try:
            response = requests.get(api_url, headers=headers, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            items = []
            if isinstance(data, dict):
                for key in ["data", "list", "items", "result"]:
                    if key in data and isinstance(data[key], list):
                        items = data[key]
                        break
            
            news_list = []
            for item in items[:30]:
                title = ""
                if isinstance(item, dict):
                    # 优先提取 widgetTitle (根据源码结构)
                    if "templateMaterial" in item and isinstance(item["templateMaterial"], dict):
                        title = item["templateMaterial"].get("widgetTitle", "")
                    if not title:
                        title = (item.get("title") or item.get("subject") or item.get("name") or "")
                
                url = (item.get("url") or item.get("link") or item.get("href") or "")
                if title:
                    news_list.append({"title": title, "summary": "", "url": url})
            
            print(f"  ✅ 成功解析 {len(news_list)} 条36氪新闻")
            return news_list
            
        except Exception as e:
            print(f"  ❌ API {api_url} 失败: {str(e)}")
            continue
    return []

def get_the_paper_news():
    print("📡 正在从澎湃新闻获取新闻...")
    rss_sources = [
        "https://m.thepaper.cn/rss/news.xml",
        "https://feedx.net/rss/thepaper.xml",
        "https://rsshub.app/thepaper/latest"
    ]
    
    for rss_url in rss_sources:
        try:
            feed = feedparser.parse(rss_url)
            if not feed.entries:
                print(f"  ❌ RSS {rss_url} 无条目")
                continue
            
            news_list = []
            for entry in feed.entries[:20]:
                title = entry.title
                summary = re.sub('<[^<]+?>', '', entry.summary) if hasattr(entry, 'summary') else ""
                news_list.append({"title": title, "summary": summary, "url": entry.link})
            
            print(f"  ✅ 成功获取 {len(news_list)} 条澎湃新闻新闻")
            return news_list
            
        except Exception as e:
            print(f"  ❌ RSS {rss_url} 失败: {str(e)}")
            continue
    return []

def filter_by_category(news_list):
    print(f"🔍 正在对 {len(news_list)} 条新闻进行分类...")
    categorized = {category: [] for category in CATEGORIES}
    
    # 用于保底的热门新闻（如果分类为空）
    hot_news = news_list[:5] 
    
    for news in news_list:
        title = news["title"] + " " + news["summary"]
        matched = False
        for category, keywords in CATEGORIES.items():
            for kw in keywords:
                if kw in title:
                    categorized[category].append({
                        "title": news["title"],
                        "url": news["url"]
                    })
                    matched = True
                    break
            if matched:
                break
    
    # 统计并打印结果
    total_matched = 0
    for category, items in categorized.items():
        print(f"📊 {category}: 匹配到 {len(items)} 条")
        total_matched += len(items)
        categorized[category] = items[:MAX_ITEMS_PER_CATEGORY]
    
    # === 保底逻辑：如果一条都没匹配到，推送前5条最热新闻 ===
    if total_matched == 0:
        print("⚠️ 警告：未匹配到任何预设关键词，正在启用保底模式（推送前5条热门新闻）...")
        categorized["🔥 今日热门"] = [{"title": n["title"], "url": n.get("url", "#")} for n in hot_news]
    
    return categorized

def generate_feishu_message(categorized_news):
    today = datetime.now().strftime("%Y年%m月%d日")
    current_time = datetime.now().strftime("%H:%M")
    
    blocks = [
        {
            "tag": "div",
            "text": {
                "tag": "lark_md",
                "content": f"📰 **{today} 科技与行业速递**\n\n*更新时间：{current_time}*"
            }
        }
    ]
    
    for category, items in categorized_news.items():
        if not items:
            continue
        blocks.append({"tag": "div", "text": {"tag": "lark_md", "content": f"**{category}**"}})
        for i, item in enumerate(items, 1):
            if item['url'] and item['url'] != "#":
                blocks.append({"tag": "div", "text": {"tag": "lark_md", "content": f"{i}. [{item['title']}]({item['url']})"}})
            else:
                blocks.append({"tag": "div", "text": {"tag": "lark_md", "content": f"{i}. {item['title']}"}})
    
    return {
        "msg_type": "interactive",
        "card": {
            "config": {"wide_screen_mode": True},
            "header": {"title": {"tag": "plain_text", "content": "🚀 今日资讯快报"}},
            "elements": blocks
        }
    }

def main():
    print("🚀 开始获取行业新闻...")
    news_list = []
    news_list.extend(get_36kr_news())
    news_list.extend(get_the_paper_news())
    
    print(f"📊 总共获取到 {len(news_list)} 条新闻")
    
    if not news_list:
        print("❌ 未获取到任何新闻")
        return
    
    categorized = filter_by_category(news_list)
    message = generate_feishu_message(categorized)
    
    webhook = os.getenv("FEISHU_WEBHOOK")
    if not webhook:
        print("⚠️ 测试模式：")
        print(json.dumps(message, indent=2, ensure_ascii=False))
        return

    print("📤 正在推送消息到飞书...")
    response = requests.post(webhook, headers={"Content-Type": "application/json"}, data=json.dumps(message))
    
    if response.status_code == 200:
        total = sum(len(v) for v in categorized.values())
        print(f"✅ 成功推送 {total} 条新闻")
    else:
        print(f"❌ 推送失败: {response.status_code}, {response.text}")

if __name__ == "__main__":
    main()
