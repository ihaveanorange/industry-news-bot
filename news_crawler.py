import requests
import feedparser
from datetime import datetime
import re
import os
import json

# ===== 配置区（按需修改）=====
CATEGORIES = {
    "智能网联": ["智能网联", "V2X", "车联网", "5G车联", "智驾", "车路协同", "高精地图", "车机", "车联"],
    "自动驾驶": ["自动驾驶", "ADAS", "Robotaxi", "L4", "无人驾驶", "FSD", "激光雷达", "自动泊车"],
    "客车/商用车": ["客车", "商用车", "重卡", "物流车", "宇通", "比亚迪客车", "金龙", "中通"]
}
MAX_ITEMS_PER_CATEGORY = 3  # 每个领域最多抓3条
# ==========================

def get_36kr_news():
    """从36氪获取新闻（修复了widgetTitle字段问题）"""
    print("📡 正在从36氪获取新闻...")
    
    # 备用API列表
    apis = [
        "https://v2.xxapi.cn/api/hot36kr",
        "https://api.vvhan.com/api/hotlist/36Ke",
        "https://tenapi.cn/v2/36kr",
        "https://api.03c3.cn/api/36kr"
    ]
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://www.36kr.com/"
    }
    
    for api_url in apis:
        try:
            print(f"  尝试API: {api_url}")
            response = requests.get(api_url, headers=headers, timeout=10)
            response.raise_for_status()
            
            if not response.text.strip():
                print(f"  ❌ API返回空数据")
                continue
            
            data = response.json()
            print(f"  📊 返回数据类型: {type(data)}")
            
            items = []
            # 处理标准字典结构
            if isinstance(data, dict):
                for key in ["data", "list", "items", "result"]:
                    if key in data and isinstance(data[key], list):
                        items = data[key]
                        print(f"  ✅ 从键 '{key}' 找到列表，长度: {len(items)}")
                        break
            
            # 核心修复点：提取widgetTitle
            news_list = []
            for item in items[:30]:
                # 优先检查是否有 templateMaterial.widgetTitle (根据你提供的网页源码)
                title = ""
                if isinstance(item, dict):
                    # 尝试新结构
                    if "templateMaterial" in item and isinstance(item["templateMaterial"], dict):
                        title = item["templateMaterial"].get("widgetTitle", "")
                    # 尝试旧结构作为备用
                    if not title:
                        title = (item.get("title") or item.get("subject") or item.get("name") or "")
                
                url = (item.get("url") or item.get("link") or 
                      item.get("href") or item.get("Url") or "")
                
                if title:
                    news_list.append({"title": title, "summary": "", "url": url})
            
            # 打印前几条标题用于调试（确认是否抓到了文字）
            if news_list:
                print(f"  🟢 抓取到的前5条标题示例: {[n['title'][:20] for n in news_list[:5]]}")
            
            print(f"  ✅ 成功解析 {len(news_list)} 条新闻")
            return news_list
            
        except Exception as e:
            print(f"  ❌ API {api_url} 失败: {str(e)}")
            continue
    
    print("❌ 所有36氪API均失败")
    return []

def get_the_paper_news():
    """从澎湃新闻获取新闻（优化了RSS解析）"""
    print("📡 正在从澎湃新闻获取新闻...")
    
    # 备用RSS源
    rss_sources = [
        "https://m.thepaper.cn/rss/news.xml", # 官方源
        "https://feedx.net/rss/thepaper.xml", # 备用源
        "https://rsshub.app/thepaper/latest"
    ]
    
    for rss_url in rss_sources:
        try:
            print(f"  尝试RSS: {rss_url}")
            feed = feedparser.parse(rss_url)
            
            if not feed.entries:
                print(f"  ❌ RSS无条目")
                continue
            
            news_list = []
            for entry in feed.entries[:30]:
                title = entry.title
                summary = re.sub('<[^<]+?>', '', entry.summary) if hasattr(entry, 'summary') else ""
                link = entry.link
                news_list.append({"title": title, "summary": summary, "url": link})
            
            print(f"  ✅ 成功获取 {len(news_list)} 条新闻")
            # 打印标题用于确认内容
            if news_list:
                print(f"  🟢 澎湃抓取示例: {news_list[0]['title']}")
            return news_list
            
        except Exception as e:
            print(f"  ❌ RSS {rss_url} 失败: {str(e)}")
            continue
    
    print("❌ 所有澎湃新闻源均失败")
    return []

def filter_by_category(news_list):
    """按行业领域分类新闻"""
    print(f"🔍 正在对 {len(news_list)} 条新闻进行分类...")
    categorized = {category: [] for category in CATEGORIES}
    
    # 调试：打印所有抓取到的标题，方便你确认是否包含关键词
    all_titles = [news["title"] for news in news_list]
    print(f"📄 抓取到的所有标题: {all_titles}")
    
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
    
    # 统计分类结果
    for category, items in categorized.items():
        print(f"📊 {category}: 匹配到 {len(items)} 条")
    
    # 限制每类新闻数量
    for category in categorized:
        categorized[category] = categorized[category][:MAX_ITEMS_PER_CATEGORY]
    
    return categorized

def generate_feishu_message(categorized_news):
    """生成飞书兼容的富文本消息"""
    today = datetime.now().strftime("%Y年%m月%d日")
    current_time = datetime.now().strftime("%H:%M")
    
    # 检查是否有任何新闻
    total_news = sum(len(v) for v in categorized_news.values())
    
    if total_news == 0:
        # 如果没有匹配到新闻，发送提示消息（包含当前时间地点）
        return {
            "msg_type": "text",
            "content": {
                "text": f"📰 {today} 行业新闻日报\n\n"
                       f"⚠️ 今日未匹配到相关领域新闻\n"
                       f"📍 当前地点：福建省厦门市\n"
                       f"🕒 更新时间：{current_time}\n"
                       f"💡 建议：检查关键词配置或新闻源可用性"
            }
        }
    
    blocks = [
        {
            "tag": "div",
            "text": {
                "tag": "lark_md",
                "content": f"🚗 **{today} 行业新闻速递**\n*数据来源：36氪+澎湃新闻 | 更新时间 {current_time}*"
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
            if item['url']:
                blocks.append({
                    "tag": "div",
                    "text": {"tag": "lark_md", "content": f"{i}. [{item['title']}]({item['url']})"}
                })
            else:
                blocks.append({
                    "tag": "div",
                    "text": {"tag": "lark_md", "content": f"{i}. {item['title']}"}
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
    print("🚀 开始获取行业新闻...")
    
    # 从36氪和澎湃新闻获取新闻
    news_list = []
    news_list.extend(get_36kr_news())
    news_list.extend(get_the_paper_news())
    
    print(f"📊 总共获取到 {len(news_list)} 条新闻")
    
    # 如果没有获取到任何新闻，发送提示消息
    if not news_list:
        print("⚠️ 所有新闻源均失败，将发送提示消息")
        categorized = {category: [] for category in CATEGORIES}
        message = generate_feishu_message(categorized)
    else:
        # 分类过滤
        categorized = filter_by_category(news_list)
        # 生成飞书消息
        message = generate_feishu_message(categorized)
    
    # 获取Webhook
    webhook = os.getenv("FEISHU_WEBHOOK")
    if not webhook:
        print("⚠️ 未检测到FEISHU_WEBHOOK环境变量，进入测试模式")
        print(json.dumps(message, indent=2, ensure_ascii=False))
        return
    
    # 推送消息
    print("📤 正在推送消息到飞书...")
    response = requests.post(
        webhook,
        headers={"Content-Type": "application/json"},
        data=json.dumps(message)
    )
    
    if response.status_code == 200:
        total = sum(len(v) for v in categorized.values())
        print(f"✅ 成功推送 {total} 条行业新闻")
    else:
        print(f"❌ 推送失败! 状态码: {response.status_code}")
        print(f"响应内容: {response.text}")

if __name__ == "__main__":
    main()
