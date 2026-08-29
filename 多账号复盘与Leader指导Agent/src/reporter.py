"""
账号评分与每日报告模块
5维度加权评分（0-100分）+ 每日自动生成报告
"""

import json
import os
import statistics
from datetime import datetime
from typing import Dict, List
from .llm_client import LLMClient


# 评分权重
SCORE_WEIGHTS = {
    "content_quality": 0.25,    # 内容质量 25%
    "topic_relevance": 0.20,    # 选题适配 20%
    "posting_rhythm": 0.15,     # 发布节奏 15%
    "engagement_health": 0.20,  # 互动健康 20%
    "growth": 0.20,             # 账号增长 20%
}


class AccountScorer:
    """账号评分器"""

    def calculate_score(self, metrics: Dict) -> Dict:
        """
        计算账号综合评分（0-100）
        5维度加权
        """
        # 1. 内容质量分 (0-100)
        content_score = self._score_content_quality(metrics)

        # 2. 选题适配分 (0-100)
        topic_score = self._score_topic_relevance(metrics)

        # 3. 发布节奏分 (0-100)
        rhythm_score = self._score_posting_rhythm(metrics)

        # 4. 互动健康分 (0-100)
        engagement_score = self._score_engagement_health(metrics)

        # 5. 账号增长分 (0-100)
        growth_score = self._score_growth(metrics)

        # 加权总分
        total = (
            content_score * SCORE_WEIGHTS["content_quality"]
            + topic_score * SCORE_WEIGHTS["topic_relevance"]
            + rhythm_score * SCORE_WEIGHTS["posting_rhythm"]
            + engagement_score * SCORE_WEIGHTS["engagement_health"]
            + growth_score * SCORE_WEIGHTS["growth"]
        )

        # 等级
        if total >= 80:
            level = "excellent"
            level_desc = "优秀"
        elif total >= 65:
            level = "good"
            level_desc = "良好"
        elif total >= 50:
            level = "medium"
            level_desc = "一般"
        elif total >= 35:
            level = "needs_improvement"
            level_desc = "待改善"
        else:
            level = "critical"
            level_desc = "危急"

        return {
            "total": round(total, 1),
            "level": level,
            "level_desc": level_desc,
            "breakdown": {
                "content_quality": round(content_score, 1),
                "topic_relevance": round(topic_score, 1),
                "posting_rhythm": round(rhythm_score, 1),
                "engagement_health": round(engagement_score, 1),
                "growth": round(growth_score, 1),
            },
            "weights": SCORE_WEIGHTS,
        }

    def _score_content_quality(self, metrics: Dict) -> float:
        """内容质量评分"""
        score = 50.0  # 基础分

        # 内容长度（越长分越高，上限100）
        avg_length = metrics.get("avg_content_length", 100)
        length_score = min(avg_length / 3, 30)  # 300字以上满分30
        score += length_score - 10  # 基准调整

        # 互动表现（内容质量的间接反映）
        avg_likes = metrics.get("avg_likes_per_post", 0)
        if avg_likes > 200:
            score += 15
        elif avg_likes > 100:
            score += 10
        elif avg_likes > 50:
            score += 5

        # Thread类型内容占比（深度内容标志）
        content_types = metrics.get("content_types", {})
        thread_ratio = content_types.get("thread", 0) / max(metrics.get("total_posts", 1), 1)
        if thread_ratio > 0.3:
            score += 5

        return max(0, min(100, score))

    def _score_topic_relevance(self, metrics: Dict) -> float:
        """选题适配评分"""
        relevant_ratio = metrics.get("relevant_ratio", 0.5)
        # 相关内容占比直接映射
        score = relevant_ratio * 100

        # 内容类型多样性（适度多样性加分，过度分散扣分）
        content_types = metrics.get("content_types", {})
        type_count = len([k for k, v in content_types.items() if v > 0])
        if type_count == 2:
            score += 5  # 适度多样
        elif type_count > 3:
            score -= 10  # 过于分散

        return max(0, min(100, score))

    def _score_posting_rhythm(self, metrics: Dict) -> float:
        """发布节奏评分"""
        score = 50.0

        # 发布天数（14天中活跃天数）
        active_days = metrics.get("active_days", 0)
        if active_days >= 12:
            score += 30
        elif active_days >= 10:
            score += 20
        elif active_days >= 7:
            score += 10
        elif active_days >= 5:
            score -= 10
        else:
            score -= 25

        # 发布稳定性（变异系数越低越好）
        cv = metrics.get("posting_cv", 1)
        if cv < 0.3:
            score += 20
        elif cv < 0.6:
            score += 10
        elif cv < 1.0:
            score -= 5
        else:
            score -= 20

        # 每周发布数量
        posts_per_week = metrics.get("total_posts", 0) / 2  # 14天=2周
        if 4 <= posts_per_week <= 8:
            score += 10  # 合理范围
        elif posts_per_week > 10:
            score -= 5  # 过多可能刷屏

        return max(0, min(100, score))

    def _score_engagement_health(self, metrics: Dict) -> float:
        """互动健康评分"""
        score = 30.0  # 基础分较低，互动是重点

        # 回复率
        reply_rate = metrics.get("avg_reply_rate", 0)
        if reply_rate > 0.05:
            score += 35
        elif reply_rate > 0.03:
            score += 25
        elif reply_rate > 0.015:
            score += 15
        elif reply_rate > 0.005:
            score += 5
        else:
            score -= 10

        # 运营回复率
        op_reply_rate = metrics.get("operator_reply_rate", 0)
        if op_reply_rate > 0.7:
            score += 25
        elif op_reply_rate > 0.5:
            score += 15
        elif op_reply_rate > 0.3:
            score += 5
        else:
            score -= 15

        # 整体互动率
        eng_rate = metrics.get("avg_engagement_rate", 0)
        if eng_rate > 0.05:
            score += 10
        elif eng_rate > 0.03:
            score += 5

        return max(0, min(100, score))

    def _score_growth(self, metrics: Dict) -> float:
        """账号增长评分"""
        score = 50.0

        # 粉丝净增长
        net_change = metrics.get("follower_net_change", 0)
        if net_change > 200:
            score += 30
        elif net_change > 100:
            score += 20
        elif net_change > 50:
            score += 10
        elif net_change > 0:
            score += 5
        elif net_change > -50:
            score -= 10
        else:
            score -= 25

        # 互动趋势（用最好内容和平均内容的比值间接反映）
        best = metrics.get("best_content")
        if best:
            best_eng = best.get("engagement_score", 0)
            avg_eng = metrics.get("total_engagement", 0) / max(metrics.get("total_posts", 1), 1)
            if avg_eng > 0 and best_eng / avg_eng < 3:
                score += 10  # 表现稳定，不是靠单条爆款

        return max(0, min(100, score))

    def score_all(self, diagnosis_results: List[Dict]) -> Dict:
        """为所有账号评分"""
        scores = {}
        for r in diagnosis_results:
            acc_id = r["account_id"]
            metrics = r.get("metrics", {})
            score = self.calculate_score(metrics)
            scores[acc_id] = score
        return scores


class DailyReporter:
    """每日报告生成器"""

    def __init__(self, llm_client: LLMClient, scorer: AccountScorer):
        self.llm = llm_client
        self.scorer = scorer

    def generate_daily_report(self, dataset: Dict, diagnosis_results: List[Dict], scores: Dict, pending_actions: List[Dict] = None) -> Dict:
        """生成每日报告"""
        print("[每日报告] 正在生成每日报告")

        # 构建报告数据
        report_date = datetime.now().strftime("%Y-%m-%d")
        accounts_report = []

        for account in dataset["accounts"]:
            acc_id = account["account_id"]
            contents = dataset["contents"].get(acc_id, [])
            score = scores.get(acc_id, {})

            # 昨日数据（取最新一天的内容）
            if contents:
                latest_date = contents[0]["post_time"].split(" ")[0]
                yesterday_contents = [c for c in contents if c["post_time"].split(" ")[0] == latest_date]
                yesterday_data = {
                    "posts": len(yesterday_contents),
                    "likes": sum(c["likes"] for c in yesterday_contents),
                    "reposts": sum(c["reposts"] for c in yesterday_contents),
                    "replies": sum(c["replies"] for c in yesterday_contents),
                }
            else:
                yesterday_data = {"posts": 0, "likes": 0, "reposts": 0, "replies": 0}

            # 粉丝变化
            follower_history = dataset["follower_history"].get(acc_id, [])
            follower_change = follower_history[0]["daily_change"] if follower_history else 0
            yesterday_data["follower_change"] = follower_change

            # 预警
            alerts = self._generate_alerts(account, contents, score)

            # 待办动作
            account_pending = []
            if pending_actions:
                account_pending = [a for a in pending_actions if a.get("account_id") == acc_id and a.get("status") != "executed_improved"]

            accounts_report.append({
                "account_id": acc_id,
                "account_name": account["account_name"],
                "daily_score": score.get("total", 0),
                "score_change": 0,  # Demo 简化，实际应与昨日对比
                "yesterday_data": yesterday_data,
                "alerts": alerts,
                "pending_actions": [a.get("action", "") for a in account_pending],
            })

        # 团队汇总
        total_posts = sum(a["yesterday_data"]["posts"] for a in accounts_report)
        total_engagement = sum(
            a["yesterday_data"]["likes"] + a["yesterday_data"]["reposts"] * 2 + a["yesterday_data"]["replies"] * 3
            for a in accounts_report
        )
        avg_score = statistics.mean([a["daily_score"] for a in accounts_report]) if accounts_report else 0

        best_account = max(accounts_report, key=lambda x: x["daily_score"]) if accounts_report else None
        worst_account = min(accounts_report, key=lambda x: x["daily_score"]) if accounts_report else None

        report = {
            "report_date": report_date,
            "summary": self._generate_summary(accounts_report),
            "accounts": accounts_report,
            "team_summary": {
                "total_posts_yesterday": total_posts,
                "total_engagement": total_engagement,
                "avg_account_score": round(avg_score, 1),
                "best_performer": f"{best_account['account_name']}（{best_account['daily_score']}分）" if best_account else "无",
                "needs_attention": f"{worst_account['account_name']}（{worst_account['daily_score']}分）" if worst_account else "无",
                "action_execution_rate": "待计算",
            },
        }

        return report

    def _generate_alerts(self, account: Dict, contents: List[Dict], score: Dict) -> List[Dict]:
        """生成预警信息"""
        alerts = []

        # 评分预警
        total = score.get("total", 100)
        if total < 50:
            alerts.append({"level": "danger", "message": f"账号综合评分{total}分，低于警戒线，需重点关注"})
        elif total < 65:
            alerts.append({"level": "warning", "message": f"账号综合评分{total}分，有提升空间"})

        # 互动预警
        if contents:
            avg_replies = statistics.mean([c["replies"] for c in contents[:5]])
            if avg_replies < 3:
                alerts.append({"level": "warning", "message": f"近期内容平均回复仅{avg_replies:.1f}条，互动率偏低"})

        # 发布预警
        if contents:
            latest_date = contents[0]["post_time"].split(" ")[0]
            try:
                latest_dt = datetime.strptime(latest_date, "%Y-%m-%d")
                days_since = (datetime.now() - latest_dt).days
                if days_since > 2:
                    alerts.append({"level": "warning", "message": f"已{days_since}天未发布新内容，注意断更"})
            except ValueError:
                pass

        if not alerts:
            alerts.append({"level": "success", "message": "各项指标正常，继续保持"})

        return alerts

    def _generate_summary(self, accounts_report: List[Dict]) -> str:
        """生成报告摘要"""
        parts = []
        for a in accounts_report:
            if a["daily_score"] >= 70:
                parts.append(f"{a['account_name']}表现良好")
            elif a["daily_score"] < 55:
                parts.append(f"{a['account_name']}需重点关注")
            else:
                parts.append(f"{a['account_name']}平稳")
        return f"今日{len(accounts_report)}个账号整体表现：" + "，".join(parts) + "。"

    def save_report(self, report: Dict, output_dir: str):
        """保存每日报告"""
        os.makedirs(output_dir, exist_ok=True)

        report_date = report.get("report_date", "latest")
        filename = f"daily_report_{report_date}.md"

        with open(os.path.join(output_dir, "daily_report.json"), "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        md = self._generate_report_markdown(report)
        with open(os.path.join(output_dir, filename), "w", encoding="utf-8") as f:
            f.write(md)

        return md

    def _generate_report_markdown(self, report: Dict) -> str:
        """生成每日报告 Markdown"""
        lines = [f"# 多账号每日运营报告\n"]
        lines.append(f"**报告日期**: {report['report_date']}\n")
        lines.append(f"**摘要**: {report['summary']}\n")

        # 团队汇总
        ts = report["team_summary"]
        lines.append("## 一、团队整体概览\n")
        lines.append(f"- 昨日总发布: {ts['total_posts_yesterday']} 条")
        lines.append(f"- 总互动量: {ts['total_engagement']}")
        lines.append(f"- 账号平均评分: {ts['avg_account_score']}/100")
        lines.append(f"- 🏆 最佳表现: {ts['best_performer']}")
        lines.append(f"- ⚠️ 需关注: {ts['needs_attention']}")
        lines.append("")

        # 逐账号
        lines.append("## 二、各账号详情\n")
        for i, acc in enumerate(report["accounts"], 1):
            score_icon = "🟢" if acc["daily_score"] >= 70 else "🟡" if acc["daily_score"] >= 55 else "🔴"
            lines.append(f"### {i}. {score_icon} {acc['account_name']} — {acc['daily_score']}分\n")

            yd = acc["yesterday_data"]
            lines.append("**昨日数据**:")
            lines.append(f"- 发布: {yd['posts']} 条 | 点赞: {yd['likes']} | 转发: {yd['reposts']} | 回复: {yd['replies']}")
            lines.append(f"- 粉丝变化: {yd['follower_change']:+d}\n")

            lines.append("**预警与提醒**:")
            for alert in acc["alerts"]:
                icon = {"success": "✅", "info": "ℹ️", "warning": "⚠️", "danger": "🚨"}.get(alert["level"], "•")
                lines.append(f"- {icon} {alert['message']}")
            lines.append("")

            if acc["pending_actions"]:
                lines.append("**待执行动作**:")
                for action in acc["pending_actions"]:
                    lines.append(f"- ⏳ {action[:60]}...")
                lines.append("")

            lines.append("---\n")

        return "\n".join(lines)
