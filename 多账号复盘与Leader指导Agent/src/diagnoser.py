"""
账号诊断与6维度归因模块
识别每个账号最主要的1-3个问题，并归因到6大维度
"""

import json
import os
import statistics
from typing import Dict, List, Tuple
from .llm_client import LLMClient


# 6大问题维度
DIMENSIONS = ["内容质量", "选题", "定位", "发布节奏", "互动", "账号健康"]

# 行业基准值（Demo用，实际应根据行业动态调整）
BENCHMARKS = {
    "avg_engagement_rate": 0.03,        # 平均互动率 3%
    "avg_reply_rate": 0.02,              # 平均回复率 2%
    "avg_posts_per_week": 5,             # 每周发布5条
    "posting_cv_threshold": 0.8,         # 发布频率变异系数阈值
    "follower_growth_rate": 0.001,       # 日粉丝增长率 0.1%
    "content_length_min": 150,            # 内容最低长度
    "relevant_content_ratio": 0.8,        # 相关内容占比最低80%
}


DIAGNOSIS_SYSTEM_PROMPT = """你是一位资深社交媒体运营专家，擅长诊断多账号运营问题。
你的诊断必须基于数据，客观、精准，不泛泛而谈。
每个问题必须包含：问题描述、数据证据、影响评估。
问题归因必须从以下6个维度中选择：内容质量、选题、定位、发布节奏、互动、账号健康。
输出严格 JSON 格式。"""

DIAGNOSIS_USER_PROMPT_TEMPLATE = """请诊断以下 X 账号的运营问题，找出最主要的1-3个问题。

【账号信息】
账号名称: {account_name}
账号定位: {positioning}
运营负责人: {operator}
粉丝数: {followers}

【近14天数据概览】
- 发布内容数: {total_posts} 条
- 总点赞: {total_likes}
- 总转发: {total_reposts}
- 总回复: {total_replies}
- 平均互动率: {avg_engagement_rate:.2%}
- 平均回复率: {avg_reply_rate:.2%}
- 发布天数: {active_days} 天 / 14天
- 发布频率变异系数: {posting_cv:.2f}
- 粉丝净增长: {follower_net_change}
- 运营回复率: {operator_reply_rate:.2%}
- 内容平均长度: {avg_content_length} 字
- 与定位相关内容占比: {relevant_ratio:.2%}

【规则引擎初步诊断结果】
{rule_based_findings}

请基于以上数据，进行深度诊断，输出：
1. 账号整体健康状态（excellent/good/medium/low/critical）
2. 最主要的1-3个问题，每个问题包含：
   - problem_id: 问题ID
   - severity: 严重程度（high/medium/low）
   - title: 问题标题
   - description: 问题详细描述
   - dimension: 主要归因维度（6选1）
   - secondary_dimensions: 次要归因维度（数组，可为空）
   - evidence: 数据证据（数组，3条以内）
   - impact: 问题影响评估

输出严格 JSON，不要额外解释。"""


class AccountDiagnoser:
    def __init__(self, llm_client: LLMClient):
        self.llm = llm_client

    def diagnose_account(self, account: Dict, contents: List[Dict], follower_history: List[Dict]) -> Dict:
        """
        诊断单个账号
        1. 计算各项指标
        2. 规则引擎初步诊断
        3. LLM 深度诊断
        """
        print(f"[诊断] 正在诊断账号: {account['account_name']}")

        # 计算指标
        metrics = self._calculate_metrics(account, contents, follower_history)

        # 规则引擎初步诊断
        rule_findings = self._rule_based_diagnosis(metrics)

        # LLM 深度诊断
        llm_diagnosis = self._llm_diagnosis(account, metrics, rule_findings)

        return {
            "account_id": account["account_id"],
            "account_name": account["account_name"],
            "operator": account["operator"],
            "metrics": metrics,
            "rule_based_findings": rule_findings,
            "diagnosis": llm_diagnosis,
        }

    def diagnose_all(self, dataset: Dict) -> List[Dict]:
        """诊断所有账号"""
        results = []
        for account in dataset["accounts"]:
            acc_id = account["account_id"]
            contents = dataset["contents"].get(acc_id, [])
            follower_history = dataset["follower_history"].get(acc_id, [])
            result = self.diagnose_account(account, contents, follower_history)
            results.append(result)
        return results

    def _calculate_metrics(self, account: Dict, contents: List[Dict], follower_history: List[Dict]) -> Dict:
        """计算账号各项指标"""
        if not contents:
            return {"error": "无内容数据"}

        total_posts = len(contents)
        total_likes = sum(c["likes"] for c in contents)
        total_reposts = sum(c["reposts"] for c in contents)
        total_replies = sum(c["replies"] for c in contents)
        total_engagement = total_likes + total_reposts * 2 + total_replies * 3

        # 互动率 = 总互动 / (粉丝数 * 发布数)
        followers = account.get("followers", 10000)
        avg_engagement_rate = total_engagement / (followers * total_posts) if followers > 0 and total_posts > 0 else 0

        # 回复率 = 总回复 / 总点赞（近似）
        avg_reply_rate = total_replies / total_likes if total_likes > 0 else 0

        # 发布天数
        post_dates = set(c["post_time"].split(" ")[0] for c in contents)
        active_days = len(post_dates)

        # 发布频率变异系数
        posts_per_day = {}
        for c in contents:
            day = c["post_time"].split(" ")[0]
            posts_per_day[day] = posts_per_day.get(day, 0) + 1
        # 包含未发布的天数（0条）
        daily_counts = list(posts_per_day.values()) + [0] * (14 - active_days)
        if len(daily_counts) > 1:
            mean_posts = statistics.mean(daily_counts)
            std_posts = statistics.stdev(daily_counts)
            posting_cv = std_posts / mean_posts if mean_posts > 0 else 999
        else:
            posting_cv = 0

        # 粉丝净增长
        follower_net_change = 0
        if follower_history:
            latest = follower_history[0]["followers"]
            oldest = follower_history[-1]["followers"]
            follower_net_change = latest - oldest

        # 运营回复率
        operator_replied_count = sum(1 for c in contents if c.get("operator_replied", False))
        operator_reply_rate = operator_replied_count / total_posts if total_posts > 0 else 0

        # 内容平均长度
        avg_content_length = int(statistics.mean(c.get("length", 100) for c in contents))

        # 与定位相关内容占比（Demo中通过内容类型判断，实际应用LLM判断）
        # 这里简化：reply类型和过短的内容视为相关性低
        relevant_count = sum(1 for c in contents if c.get("content_type") != "reply" and c.get("length", 0) >= 80)
        relevant_ratio = relevant_count / total_posts if total_posts > 0 else 0

        # 内容类型分布
        content_types = {}
        for c in contents:
            ct = c.get("content_type", "unknown")
            content_types[ct] = content_types.get(ct, 0) + 1

        # 发布时段分布
        post_hours = []
        for c in contents:
            try:
                hour = int(c["post_time"].split(" ")[1].split(":")[0])
                post_hours.append(hour)
            except (IndexError, ValueError):
                pass

        return {
            "total_posts": total_posts,
            "total_likes": total_likes,
            "total_reposts": total_reposts,
            "total_replies": total_replies,
            "total_engagement": total_engagement,
            "avg_likes_per_post": round(total_likes / total_posts, 1),
            "avg_reposts_per_post": round(total_reposts / total_posts, 1),
            "avg_replies_per_post": round(total_replies / total_posts, 1),
            "avg_engagement_rate": avg_engagement_rate,
            "avg_reply_rate": avg_reply_rate,
            "active_days": active_days,
            "posting_cv": posting_cv,
            "follower_net_change": follower_net_change,
            "operator_reply_rate": operator_reply_rate,
            "avg_content_length": avg_content_length,
            "relevant_ratio": relevant_ratio,
            "content_types": content_types,
            "post_hours": post_hours,
            "best_content": max(contents, key=lambda x: x["engagement_score"]) if contents else None,
            "worst_content": min(contents, key=lambda x: x["engagement_score"]) if contents else None,
        }

    def _rule_based_diagnosis(self, metrics: Dict) -> List[Dict]:
        """基于规则引擎的初步诊断"""
        findings = []

        # 1. 互动问题
        if metrics.get("avg_reply_rate", 1) < BENCHMARKS["avg_reply_rate"] * 0.5:
            findings.append({
                "dimension": "互动",
                "severity": "high",
                "finding": f"回复率严重偏低：{metrics['avg_reply_rate']:.2%}，基准为{BENCHMARKS['avg_reply_rate']:.2%}",
                "possible_cause": "运营不回复评论 / 内容缺乏互动引导",
            })

        if metrics.get("operator_reply_rate", 1) < 0.3:
            findings.append({
                "dimension": "互动",
                "severity": "high",
                "finding": f"运营回复率极低：{metrics['operator_reply_rate']:.2%}，大部分内容下没有运营回复",
                "possible_cause": "运营没有回复评论的习惯 / 时间不足",
            })

        # 2. 发布节奏问题
        if metrics.get("active_days", 14) < 7:
            findings.append({
                "dimension": "发布节奏",
                "severity": "high",
                "finding": f"发布天数不足：14天中仅{metrics['active_days']}天有内容发布，频繁断更",
                "possible_cause": "没有内容规划 / 素材不足",
            })

        if metrics.get("posting_cv", 0) > BENCHMARKS["posting_cv_threshold"]:
            findings.append({
                "dimension": "发布节奏",
                "severity": "high",
                "finding": f"发布频率极不稳定：变异系数{metrics['posting_cv']:.2f}，超过阈值{BENCHMARKS['posting_cv_threshold']}",
                "possible_cause": "集中发布+长时间断更，没有固定节奏",
            })

        # 3. 选题/定位问题
        if metrics.get("relevant_ratio", 1) < BENCHMARKS["relevant_content_ratio"]:
            findings.append({
                "dimension": "选题",
                "severity": "high",
                "finding": f"非相关内容占比过高：相关内容仅{metrics['relevant_ratio']:.2%}，低于基准{BENCHMARKS['relevant_content_ratio']:.0%}",
                "possible_cause": "选题混乱，什么都发，定位模糊",
            })

        # 4. 内容质量问题
        if metrics.get("avg_content_length", 1000) < BENCHMARKS["content_length_min"]:
            findings.append({
                "dimension": "内容质量",
                "severity": "medium",
                "finding": f"内容平均长度偏短：{metrics['avg_content_length']}字，低于基准{BENCHMARKS['content_length_min']}字",
                "possible_cause": "内容缺乏深度，多为浅尝辄止的观点",
            })

        # 5. 账号健康问题
        if metrics.get("follower_net_change", 0) < 0:
            findings.append({
                "dimension": "账号健康",
                "severity": "medium",
                "finding": f"粉丝净减少：近14天掉粉{abs(metrics['follower_net_change'])}人",
                "possible_cause": "定位模糊导致老粉丝流失 / 内容质量下降",
            })

        # 6. 互动率整体偏低
        if metrics.get("avg_engagement_rate", 1) < BENCHMARKS["avg_engagement_rate"] * 0.5:
            findings.append({
                "dimension": "互动",
                "severity": "medium",
                "finding": f"整体互动率偏低：{metrics['avg_engagement_rate']:.2%}，基准为{BENCHMARKS['avg_engagement_rate']:.2%}",
                "possible_cause": "多维度综合问题，需进一步分析",
            })

        return findings

    def _llm_diagnosis(self, account: Dict, metrics: Dict, rule_findings: List[Dict]) -> Dict:
        """调用 LLM 进行深度诊断"""
        rule_findings_text = json.dumps(rule_findings, ensure_ascii=False, indent=2) if rule_findings else "无规则引擎发现"

        user_prompt = DIAGNOSIS_USER_PROMPT_TEMPLATE.format(
            account_name=account["account_name"],
            positioning=account["positioning"],
            operator=account["operator"],
            followers=account["followers"],
            total_posts=metrics["total_posts"],
            total_likes=metrics["total_likes"],
            total_reposts=metrics["total_reposts"],
            total_replies=metrics["total_replies"],
            avg_engagement_rate=metrics["avg_engagement_rate"],
            avg_reply_rate=metrics["avg_reply_rate"],
            active_days=metrics["active_days"],
            posting_cv=metrics["posting_cv"],
            follower_net_change=metrics["follower_net_change"],
            operator_reply_rate=metrics["operator_reply_rate"],
            avg_content_length=metrics["avg_content_length"],
            relevant_ratio=metrics["relevant_ratio"],
            rule_based_findings=rule_findings_text,
        )

        return self.llm.chat_json(DIAGNOSIS_SYSTEM_PROMPT, user_prompt, temperature=0.3)

    def save_diagnosis(self, results: List[Dict], output_dir: str):
        """保存诊断结果"""
        os.makedirs(output_dir, exist_ok=True)

        with open(os.path.join(output_dir, "diagnosis_details.json"), "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)

        # 生成可读报告
        md = self._generate_diagnosis_report(results)
        with open(os.path.join(output_dir, "diagnosis_report.md"), "w", encoding="utf-8") as f:
            f.write(md)

        return md

    def _generate_diagnosis_report(self, results: List[Dict]) -> str:
        """生成诊断报告 Markdown"""
        lines = ["# 多账号诊断报告\n"]
        lines.append(f"**诊断时间**: 近14天数据\n")
        lines.append(f"**账号数量**: {len(results)}\n")

        # 汇总表
        lines.append("## 一、账号健康概览\n")
        lines.append("| 账号 | 运营负责人 | 整体健康 | 主要问题数 | 粉丝变化 | 平均互动率 |")
        lines.append("|------|-----------|---------|-----------|---------|-----------|")
        for r in results:
            diag = r.get("diagnosis", {})
            health = diag.get("overall_health", "unknown")
            health_icon = {"excellent": "🟢", "good": "🟢", "medium": "🟡", "low": "🟠", "critical": "🔴"}.get(health, "⚪")
            problems = diag.get("problems", [])
            metrics = r.get("metrics", {})
            lines.append(
                f"| {r['account_name']} | {r['operator']} | {health_icon} {health} | {len(problems)} | "
                f"{metrics.get('follower_net_change', 0):+d} | {metrics.get('avg_engagement_rate', 0):.2%} |"
            )
        lines.append("")

        # 逐账号详细诊断
        lines.append("## 二、逐账号详细诊断\n")
        for i, r in enumerate(results, 1):
            diag = r.get("diagnosis", {})
            metrics = r.get("metrics", {})

            lines.append(f"### {i}. {r['account_name']}（{r['operator']}）\n")
            lines.append(f"**整体健康状态**: {diag.get('overall_health', 'unknown')}\n")

            # 关键指标
            lines.append("**关键指标**:")
            lines.append(f"- 发布内容: {metrics.get('total_posts', 0)} 条（活跃 {metrics.get('active_days', 0)}/14 天）")
            lines.append(f"- 平均点赞: {metrics.get('avg_likes_per_post', 0)} | 平均转发: {metrics.get('avg_reposts_per_post', 0)} | 平均回复: {metrics.get('avg_replies_per_post', 0)}")
            lines.append(f"- 互动率: {metrics.get('avg_engagement_rate', 0):.2%} | 回复率: {metrics.get('avg_reply_rate', 0):.2%}")
            lines.append(f"- 运营回复率: {metrics.get('operator_reply_rate', 0):.2%}")
            lines.append(f"- 发布稳定性(CV): {metrics.get('posting_cv', 0):.2f}")
            lines.append(f"- 粉丝净增长: {metrics.get('follower_net_change', 0):+d}")
            lines.append("")

            # 问题列表
            problems = diag.get("problems", [])
            if problems:
                lines.append(f"**主要问题（{len(problems)}个）**:")
                for j, p in enumerate(problems, 1):
                    severity_icon = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(p.get("severity", "low"), "⚪")
                    lines.append(f"\n{j}. {severity_icon} **{p.get('title', '')}** [{p.get('dimension', '')}]")
                    lines.append(f"   - 描述: {p.get('description', '')}")
                    if p.get("secondary_dimensions"):
                        lines.append(f"   - 次要维度: {', '.join(p['secondary_dimensions'])}")
                    lines.append(f"   - 影响: {p.get('impact', '')}")
                    lines.append("   - 证据:")
                    for ev in p.get("evidence", [])[:3]:
                        lines.append(f"     - {ev}")
            else:
                lines.append("**未发现明显问题**")

            lines.append("\n---\n")

        return "\n".join(lines)
