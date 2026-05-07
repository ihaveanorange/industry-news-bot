import requests
import feedparser
from datetime import datetime
import re
import os
import json

# ===== 配置区 =====
CATEGORIES = {
    "商用车": ["商用车", "客车", "重卡", "轻卡", "公交", "卡车", "货车", "大巴", "宇通", "金龙",
                     "中通", "比亚迪", "安凯", "福田", "东风", "解放", "重汽", "陕汽", "巴士", "欧曼", 
                     "江淮", "江铃", "庆铃", "五十铃"],
    
    "乘用车": ["乘用车", "轿车", "SUV", "MPV", "新能源车", "电动车", "纯电车", "插混", "增程", 
                     "比亚迪", "特斯拉", "蔚来", "小鹏", "理想", "小米汽车", "华为", "问界", "极氪", 
                     "长安", "吉利", "长城", "上汽", "广汽", "一汽", "北汽", "奇瑞", "东风", 
                     "大众", "丰田", "本田", "宝马", "奔驰", "奥迪", "小米", "华为", "鸿蒙"],

    "氢能产业": ["氢气", "氢能", "燃料电池", "氢燃料", "加氢", "制氢", "加氢站", "储氢", "质子交换膜", 
                  "绿氢", "灰氢", "氢"],
    
    "自动驾驶": ["自动驾驶", "无人驾驶", "ADAS", "Robotaxi", "L0", "L1", "L2", "L3", "L4", "L5", "FSD", "NOA", "NOP", "NGP", 
                  "激光雷达", "毫米波雷达", "摄像头", "感知", "决策", "规划", "高精地图", "自动泊车", 
                  "AEB", "ACC", "LCC", "APA"],
    
    "智能网联": ["智能网联", "V2X", "车联网", "车路协同", "5G车联", "C-V2X", "OBU", "RSU", "路侧", "云控", 
                 "OTA", "智能座舱", "车机", "HUD", "AR-HUD", "语音交互", "手势控制"],
    
    "标准法规": ["标准", "法规", "准入", "认证", "测试", "检测", "公告", "工信部", "交通部", "国标", "行标", 
                 "团标", "强标", "安全标准", "排放标准", "油耗标准", "新能源补贴", "购置税", "双积分"]
}
MAX_ITEMS_PER_CATEGORY = 6
# ==========================

def get_36kr_news():
    """从36氪获取新闻"""
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
            print(f"  尝试API: {api_url}")
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
            # 在 get_36kr_news() 函数中，解析 item 的部分
            for item in items[:100]:
                title = ""
                item_id = None
                
                if isinstance(item, dict):
                    # 提取标题（不变）
                    if "templateMaterial" in item and isinstance(item["templateMaterial"], dict):
                        title = item["templateMaterial"].get("widgetTitle", "")
                    if not title:
                        title = (item.get("title") or item.get("subject") or item.get("name") or "")
                    
                    # 修复：从 templateMaterial 中提取 itemId
                    if "templateMaterial" in item and isinstance(item["templateMaterial"], dict):
                        item_id = item["templateMaterial"].get("itemId")
                    # 如果上面没取到，尝试从根层级获取
                    if not item_id:
                        item_id = item.get("itemId")
                
                # 修复：根据 itemId 拼接标准 URL
                url = ""
                if item_id:
                    url = f"https://www.36kr.com/p/{item_id}"
                else:
                    # 备用方案：如果API直接提供了url字段
                    url = (item.get("url") or item.get("link") or "")
                
                # 修复：确保有 URL 才加入列表
                if title and url:
                    news_list.append({"title": title, "summary": "", "url": url})
            
            print(f"  ✅ 成功解析 {len(news_list)} 条36氪新闻")
            return news_list
            
        except Exception as e:
            print(f"  ❌ API {api_url} 失败: {str(e)}")
            continue
    return []

def get_the_paper_news():
    """从澎湃新闻获取新闻（已优化源）"""
    print("📡 正在从澎湃新闻获取新闻...")
    
    # 优化源列表：移除了失效的 m.thepaper.cn/rss，直接使用更稳定的聚合源
    rss_sources = [
        "https://feedx.net/rss/thepaper.xml", # 你日志中显示此源成功，优先使用
        "https://rsshub.app/thepaper/latest",
        "https://m.thepaper.cn/rss/news.xml"  # 放在最后作为兜底
    ]
    
    for rss_url in rss_sources:
        try:
            print(f"  尝试RSS: {rss_url}")
            feed = feedparser.parse(rss_url)
            
            if not feed.entries:
                print(f"  ❌ RSS无条目")
                continue
            
            news_list = []
            for entry in feed.entries[:100]:
                title = entry.title
                summary = re.sub('<[^<]+?>', '', entry.summary) if hasattr(entry, 'summary') else ""
                news_list.append({"title": title, "summary": summary, "url": entry.link})
            
            print(f"  ✅ 成功获取 {len(news_list)} 条澎湃新闻")
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
        return {
            "msg_type": "text",
            "content": {
                "text": f"📰 {today} 行业新闻日报\n\n"
                       f"⚠️ 今日未匹配到相关领域新闻\n"
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
    print(f"📅 当前时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
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
