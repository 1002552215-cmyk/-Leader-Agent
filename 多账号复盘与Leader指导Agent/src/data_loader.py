"""
多账号模拟数据生成
Demo 阶段使用内置模拟数据，实际使用时可替换为 X API 采集
3个账号各有不同的表现特征和问题：
- 账号A：内容质量好但互动差（不回复评论）
- 账号B：选题混乱定位模糊（什么都发）
- 账号C：发布节奏不稳定（断更+爆发）
"""

import json
import os
import random
from datetime import datetime, timedelta
from typing import Dict, List


def generate_mock_accounts() -> List[Dict]:
    """生成3个模拟账号的基础信息"""
    return [
        {
            "account_id": "ai_tech_daily",
            "account_name": "AI技术日报",
            "domain": "AI技术",
            "positioning": "每日分享AI前沿技术与工程实践",
            "operator": "张三（运营同学A）",
            "followers": 45000,
            "created_at": "2025-03-15",
        },
        {
            "account_id": "product_growth_lab",
            "account_name": "产品增长实验室",
            "domain": "产品增长",
            "positioning": "产品方法论与增长实战",
            "operator": "李四（运营同学B）",
            "followers": 28000,
            "created_at": "2025-06-01",
        },
        {
            "account_id": "startup_stories",
            "account_name": "创业故事集",
            "domain": "创业",
            "positioning": "创业者的真实故事与经验分享",
            "operator": "王五（运营同学C）",
            "followers": 67000,
            "created_at": "2024-11-20",
        },
    ]


def generate_content_for_account(account_id: str, days: int = 14) -> List[Dict]:
    """
    为指定账号生成近N天的内容数据
    每个账号有不同的问题特征
    """
    contents = []
    base_date = datetime(2026, 8, 29)

    if account_id == "ai_tech_daily":
        # 账号A：内容质量好但互动差，不回复评论
        # 每天稳定发1-2条，内容质量高，但回复率极低
        topics = ["RAG优化", "模型量化", "Prompt工程", "Agent架构", "推理加速", "微调实践", "Embedding", "向量数据库"]
        for day in range(days):
            post_date = base_date - timedelta(days=day)
            num_posts = random.randint(1, 2)
            for i in range(num_posts):
                topic = random.choice(topics)
                likes = random.randint(80, 250)
                reposts = random.randint(20, 80)
                replies = random.randint(0, 5)  # 回复极少
                contents.append({
                    "content_id": f"{account_id}_{day}_{i}",
                    "text": f"关于{topic}的一些实践分享，总结了3个关键点...（内容质量较高，有深度）",
                    "post_time": post_date.strftime("%Y-%m-%d") + f" {random.randint(9,11)}:{random.randint(0,59):02d}:00",
                    "likes": likes,
                    "reposts": reposts,
                    "replies": replies,
                    "content_type": random.choice(["thread", "single", "single"]),
                    "length": random.randint(150, 400),
                    "has_media": random.choice([True, False, False]),
                    "operator_replied": False,  # 运营不回复评论
                    "engagement_score": likes + reposts * 2 + replies * 3,
                })

    elif account_id == "product_growth_lab":
        # 账号B：选题混乱，定位模糊，什么都发
        # 内容领域跳跃，从产品到美食到旅游，互动参差不齐
        topics = ["产品方法论", "用户增长", "美食探店", "旅游攻略", "职场感悟", "A/B测试", "电影推荐", "数据分析", "健身打卡", "需求管理"]
        for day in range(days):
            post_date = base_date - timedelta(days=day)
            num_posts = random.randint(0, 3)
            for i in range(num_posts):
                topic = random.choice(topics)
                # 偏离定位的内容互动差
                if topic in ["产品方法论", "用户增长", "A/B测试", "数据分析", "需求管理"]:
                    likes = random.randint(60, 180)
                    reposts = random.randint(15, 60)
                    replies = random.randint(5, 20)
                else:
                    likes = random.randint(10, 50)
                    reposts = random.randint(2, 15)
                    replies = random.randint(0, 5)
                contents.append({
                    "content_id": f"{account_id}_{day}_{i}",
                    "text": f"{topic}相关内容分享...（选题与账号定位匹配度不一）",
                    "post_time": post_date.strftime("%Y-%m-%d") + f" {random.randint(8,22)}:{random.randint(0,59):02d}:00",
                    "likes": likes,
                    "reposts": reposts,
                    "replies": replies,
                    "content_type": random.choice(["single", "single", "thread", "reply"]),
                    "length": random.randint(50, 300),
                    "has_media": random.choice([True, False]),
                    "operator_replied": random.choice([True, False, False]),
                    "engagement_score": likes + reposts * 2 + replies * 3,
                })

    elif account_id == "startup_stories":
        # 账号C：发布节奏不稳定，断更+爆发
        # 某些天发很多条，某些天完全不发
        topics = ["创业复盘", "融资经历", "团队管理", "产品从0到1", "失败教训", "增长黑客", "投资人视角", "创业者心态"]
        for day in range(days):
            post_date = base_date - timedelta(days=day)
            # 70%的天数不发，30%的天数发3-5条
            if random.random() < 0.7:
                continue
            num_posts = random.randint(3, 5)
            for i in range(num_posts):
                topic = random.choice(topics)
                likes = random.randint(100, 400)
                reposts = random.randint(30, 120)
                replies = random.randint(10, 40)
                contents.append({
                    "content_id": f"{account_id}_{day}_{i}",
                    "text": f"创业{topic}：分享一个真实经历...（内容有故事性，但发布不稳定）",
                    "post_time": post_date.strftime("%Y-%m-%d") + f" {random.randint(10,23)}:{random.randint(0,59):02d}:00",
                    "likes": likes,
                    "reposts": reposts,
                    "replies": replies,
                    "content_type": random.choice(["thread", "single", "thread"]),
                    "length": random.randint(200, 500),
                    "has_media": random.choice([True, False]),
                    "operator_replied": random.choice([True, True, False]),
                    "engagement_score": likes + reposts * 2 + replies * 3,
                })

    return sorted(contents, key=lambda x: x["post_time"], reverse=True)


def generate_follower_history(account_id: str, days: int = 14) -> List[Dict]:
    """生成粉丝变化历史"""
    base_followers = {
        "ai_tech_daily": 45000,
        "product_growth_lab": 28000,
        "startup_stories": 67000,
    }
    base = base_followers.get(account_id, 10000)
    history = []
    current = base

    # 不同账号的粉丝趋势
    if account_id == "ai_tech_daily":
        # 缓慢增长
        daily_change = lambda: random.randint(20, 80)
    elif account_id == "product_growth_lab":
        # 停滞甚至微降
        daily_change = lambda: random.randint(-30, 20)
    else:
        # 波动大，断更时掉粉
        daily_change = lambda: random.randint(-50, 100)

    base_date = datetime(2026, 8, 29)
    for day in range(days):
        date = base_date - timedelta(days=day)
        change = daily_change()
        current += change
        history.append({
            "date": date.strftime("%Y-%m-%d"),
            "followers": current,
            "daily_change": change,
        })

    return history


def generate_last_week_actions() -> List[Dict]:
    """生成上周的行动建议（用于追踪闭环演示）"""
    return [
        {
            "action_id": "prev_001",
            "account_id": "ai_tech_daily",
            "action": "每条内容发布后2小时内回复前5条评论",
            "status": "not_executed",  # 未执行
            "expected_outcome": "回复率提升到1%以上",
            "actual_outcome": None,
            "reason": "运营同学反馈没时间，经常忘记",
        },
        {
            "action_id": "prev_002",
            "account_id": "product_growth_lab",
            "action": "内容选题聚焦产品增长领域，减少非相关内容占比到20%以下",
            "status": "partially_executed",  # 部分执行
            "expected_outcome": "非相关内容占比从50%降到20%以下",
            "actual_outcome": "非相关内容占比从50%降到35%，有改善但未达标",
            "reason": "运营同学觉得只发产品内容太单调，忍不住发生活类内容",
        },
        {
            "action_id": "prev_003",
            "account_id": "startup_stories",
            "action": "制定内容日历，保证每周至少发布5条，避免断更超过2天",
            "status": "executed_improved",  # 已执行且有改善
            "expected_outcome": "每周发布5条以上，断更不超过2天",
            "actual_outcome": "本周发布6条，最长断更1.5天，发布稳定性提升",
            "reason": None,
        },
        {
            "action_id": "prev_004",
            "account_id": "ai_tech_daily",
            "action": "在内容末尾增加提问引导评论",
            "status": "executed_no_improvement",  # 已执行但无改善
            "expected_outcome": "评论数提升30%",
            "actual_outcome": "评论数无明显变化，因为运营不回复导致用户不愿意评论",
            "reason": "只加了提问但不回复，用户评论后得不到反馈，互动意愿仍然低",
        },
    ]


def generate_full_dataset() -> Dict:
    """生成完整的模拟数据集"""
    accounts = generate_mock_accounts()
    dataset = {
        "accounts": accounts,
        "contents": {},
        "follower_history": {},
        "last_week_actions": generate_last_week_actions(),
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }

    for account in accounts:
        acc_id = account["account_id"]
        dataset["contents"][acc_id] = generate_content_for_account(acc_id)
        dataset["follower_history"][acc_id] = generate_follower_history(acc_id)

    return dataset


def save_mock_data(output_path: str = None):
    """保存模拟数据到文件"""
    if output_path is None:
        output_path = os.path.join(os.path.dirname(__file__), "..", "data", "account_dataset.json")

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    data = generate_full_dataset()
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return output_path


if __name__ == "__main__":
    path = save_mock_data()
    print(f"模拟数据已保存到: {path}")
    data = generate_full_dataset()
    print(f"账号数: {len(data['accounts'])}")
    for acc in data["accounts"]:
        contents = data["contents"][acc["account_id"]]
        print(f"  {acc['account_name']}: {len(contents)} 条内容")
