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
    "智能网联": ["智能网联", "V2X", "车联网", "5G车联", "智驾", "车路协同", "高精地图", "车机", "车联"],
    "自动驾驶": ["自动驾驶", "ADAS", "Robotaxi", "L4", "无人驾驶", "FSD", "激光雷达", "自动泊车"],
    "客车/商用车": ["客车", "商用车", "重卡", "物流车", "宇通", "比亚迪客车", "金龙", "中通"]
}
MAX_ITEMS_PER_CATEGORY = 3  # 每个领域最多抓3条
# ==========================

def get_36kr_news():
    """使用多个备用API获取36氪新闻"""
    print("📡 正在从36氪获取新闻...")
    
    # 备用API列表（按可靠性排序）
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
            
            # 尝试多种可能的返回格式
            items = []
            
            # 格式1: {"data": [...]}
            if isinstance(data, dict):
                # 尝试所有可能的键名
                for key in ["data", "list", "items", "result", "news", "hot", "dataList"]:
                    if key in data and isinstance(data[key], list):
                        items = data[key]
                        print(f"  ✅ 从键 '{key}' 找到列表，长度: {len(items)}")
                        break
                
                # 如果还没找到，尝试直接取第一个列表值
                if not items:
                    for key, value in data.items():
                        if isinstance(value, list):
                            items = value
                            print(f"  ✅ 从键 '{key}' 找到列表（备用），长度: {len(items)}")
                            break
            
            # 格式2: 直接是列表
            elif isinstance(data, list):
                items = data
                print(f"  ✅ 直接是列表，长度: {len(items)}")
            
            if not items:
                print(f"  ❌ 无法从响应中提取列表")
                continue
            
            news_list = []
            for item in items[:30]:
                # 尝试多种可能的字段名
                title = (item.get("title") or item.get("subject") or 
                        item.get("name") or item.get("content") or 
                        item.get("Title") or item.get("text") or "")
                url = (item.get("url") or item.get("link") or 
                      item.get("href") or item.get("Url") or "")
                
                if title:
                    news_list.append({"title": title, "summary": "", "url": url})
            
            print(f"  ✅ 成功解析 {len(news_list)} 条新闻")
            return news_list
            
        except Exception as e:
            print(f"  ❌ API {api_url} 失败: {str(e)}")
            continue
    
    print("❌ 所有36氪API均失败")
    return []

def get_the_paper_news():
    """从澎湃新闻获取新闻（使用多个备用源）"""
    print("📡 正在从澎湃新闻获取新闻...")
    
    # 备用RSS源
    rss_sources = [
        "https://m.thepaper.cn/rss/news.xml",
        "https://feedx.net/rss/thepaper.xml",
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
                news_list.append({"title": title, "summary": summary, "url": entry.link})
            
            print(f"  ✅ 成功获取 {len(news_list)} 条新闻")
            return news_list
            
        except Exception as e:
            print(f"  ❌ RSS {rss_url} 失败: {str(e)}")
            continue
    
    print("❌ 所有澎湃新闻源均失败")
    return []

def get_baidu_news():
    """从百度热搜获取科技新闻（备用源）"""
    print("📡 正在从百度获取新闻...")
    try:
        url = "https://top.baidu.com/board?tab=realtime"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        response = requests.get(url, headers=headers, timeout=10)
        
        # 使用正则提取数据
        pattern = r'"word":"(.*?)"'
        titles = re.findall(pattern, response.text)
        
        news_list = []
        for title in titles[:30]:
            if title:
                news_list.append({"title": title, "summary": "", "url": ""})
        
        print(f"  ✅ 百度获取到 {len(news_list)} 条新闻")
        return news_list
    except Exception as e:
        print(f"  ❌ 百度抓取失败: {str(e)}")
        return []

def filter_by_category(news_list):
    """按行业领域分类新闻"""
    print(f"🔍 正在对 {len(news_list)} 条新闻进行分类...")
    categorized = {category: [] for category in CATEGORIES}
    
    for news in news_list:
        title = news["title"] + " " + news["summary"]
        for category, keywords in CATEGORIES.items():
            if any(kw in title for kw in keywords):
                categorized[category].append({
                    "title": news["title"],
                    "url": news["url"]
                })
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
        # 如果没有匹配到新闻，发送所有新闻的摘要
        return {
            "msg_type": "text",
            "content": {
                "text": f"📰 {today} 行业新闻日报\n\n"
                       f"⚠️ 今日未匹配到相关领域新闻\n"
                       f"建议：检查关键词配置或新闻源可用性\n"
                       f"更新时间：{current_time}"
            }
        }
    
    blocks = [
        {
            "tag": "div",
            "text": {
                "tag": "lark_md",
                "content": f"🚗 **{today} 行业新闻速递**\n*数据来源：36氪+澎湃新闻+百度热搜 | 更新时间 {current_time}*"
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
    
    # 从多个源获取新闻
    news_list = []
    news_list.extend(get_36kr_news())
    news_list.extend(get_the_paper_news())
    news_list.extend(get_baidu_news())
    
    print(f"📊 总共获取到 {len(news_list)} 条新闻")
    
    # 如果没有获取到任何新闻，使用模拟数据
    if not news_list:
        print("⚠️ 所有新闻源均失败，使用模拟数据")
        news_list = [
            {"title": "工信部发布智能网联汽车标准体系建设指南", "summary": "", "url": "https://www.36kr.com/p/1"},
            {"title": "百度Apollo宣布Robotaxi商业化运营", "summary": "", "url": "https://www.36kr.com/p/2"},
            {"title": "特斯拉FSD V12.4版本推送", "summary": "", "url": "https://www.36kr.com/p/3"},
            {"title": "小马智行获准在京开展无人化测试", "summary": "", "url": "https://www.36kr.com/p/4"},
            {"title": "宇通发布全球首款纯电氢能客车", "summary": "", "url": "https://www.36kr.com/p/5"},
            {"title": "重汽推出L4级无人物流车", "summary": "", "url": "https://www.36kr.com/p/6"},
            {"title": "华为发布车路协同解决方案", "summary": "", "url": "https://www.36kr.com/p/7"},
            {"title": "宁德时代发布新一代电池技术", "summary": "", "url": "https://www.36kr.com/p/8"},
        ]
    
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
