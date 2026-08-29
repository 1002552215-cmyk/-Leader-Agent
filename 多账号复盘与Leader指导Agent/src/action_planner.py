"""
行动建议与 Leader 指导提纲模块
针对每个账号的问题，生成下周具体动作（SMART原则）和1on1沟通提纲
"""

import json
import os
from typing import Dict, List
from .llm_client import LLMClient


ACTION_SYSTEM_PROMPT = """你是一位资深社交媒体运营顾问，擅长将诊断问题转化为可执行的具体动作。
你的行动建议必须遵循 SMART 原则：
- Specific：具体做什么，不能空泛（不说"加强互动"，说"每条内容发布后2小时内回复前5条评论"）
- Measurable：可衡量（说"回复率提升到2%以上"，不说"提升互动"）
- Achievable：可实现（不超出运营同学能力范围和时间预算）
- Relevant：与诊断问题强相关
- Time-bound：有明确时间节点

每个动作必须标注优先级（P0/P1/P2）、难度、所需资源。
输出严格 JSON 格式。"""

ACTION_USER_PROMPT_TEMPLATE = """请针对以下账号的诊断问题，生成下周应执行的具体行动建议。

【账号信息】
账号名称: {account_name}
运营负责人: {operator}
账号定位: {positioning}

【诊断结果】
整体健康状态: {overall_health}

主要问题:
{problems_text}

请为每个主要问题生成1-2个具体行动建议，总共不超过4个动作。
每个动作包含：
- action_id: 动作ID（a001, a002...）
- linked_problem: 关联的问题ID
- priority: 优先级（P0最高/P1/P2）
- action: 具体动作描述（SMART原则，要具体到可直接执行）
- expected_outcome: 预期成果（可量化）
- deadline: 时间节点
- difficulty: 难度（low/medium/high）
- required_resources: 所需资源（时间、工具、支持等）

输出严格 JSON 数组，不要额外解释。"""


COACHING_SYSTEM_PROMPT = """你是一位经验丰富的团队 Leader，擅长与运营同学进行高效的1对1沟通。
你的指导提纲必须遵循以下原则：
1. 先肯定再提问题，维护运营同学的自信心
2. 用苏格拉底式提问引导对方自己发现问题，而非直接批评
3. 每个行动建议都要与对方达成共识，而非单方面下达
4. 关注对方的实际困难，提供必要的资源支持
5. 设定小而可实现的目标，不追求一步到位
6. 1on1是赋能会，不是批斗会

输出严格 JSON 格式。"""

COACHING_USER_PROMPT_TEMPLATE = """请为以下账号的 Leader 与运营同学1对1沟通，生成结构化指导提纲。

【沟通背景】
账号名称: {account_name}
运营负责人: {operator}
账号整体评分: {score}/100
沟通时长: 30分钟

【账号诊断结果】
{diagnosis_summary}

【下周行动建议】
{actions_summary}

请生成1on1沟通提纲，包含以下部分：
1. agenda: 沟通议程，每个部分包含 section（环节名称）、purpose（目的）、key_points（要点，含具体提问）、leader_tips（Leader注意事项）
2. do_and_dont: 沟通中的注意事项，包含 do（应该做的）和 dont（不应该做的）各5条

输出严格 JSON，不要额外解释。"""


class ActionPlanner:
    def __init__(self, llm_client: LLMClient):
        self.llm = llm_client

    def generate_actions(self, diagnosis_result: Dict) -> Dict:
        """为单个账号生成行动建议"""
        account_name = diagnosis_result["account_name"]
        print(f"[行动建议] 正在为 {account_name} 生成行动建议")

        diag = diagnosis_result.get("diagnosis", {})
        problems = diag.get("problems", [])

        # 格式化问题文本
        problems_text = ""
        for p in problems:
            problems_text += f"- [{p.get('severity', '')}] {p.get('title', '')}（维度: {p.get('dimension', '')}）\n"
            problems_text += f"  描述: {p.get('description', '')}\n"
            problems_text += f"  影响: {p.get('impact', '')}\n\n"

        user_prompt = ACTION_USER_PROMPT_TEMPLATE.format(
            account_name=account_name,
            operator=diagnosis_result["operator"],
            positioning=diagnosis_result.get("metrics", {}).get("positioning", "未提供"),
            overall_health=diag.get("overall_health", "unknown"),
            problems_text=problems_text,
        )

        actions = self.llm.chat_json(ACTION_SYSTEM_PROMPT, user_prompt, temperature=0.4)

        # 确保是列表
        if isinstance(actions, dict):
            actions = actions.get("actions", [])
        if not isinstance(actions, list):
            actions = []

        return {
            "account_id": diagnosis_result["account_id"],
            "account_name": account_name,
            "operator": diagnosis_result["operator"],
            "actions": actions,
        }

    def generate_all_actions(self, diagnosis_results: List[Dict]) -> List[Dict]:
        """为所有账号生成行动建议"""
        return [self.generate_actions(r) for r in diagnosis_results]

    def generate_coaching_outline(self, diagnosis_result: Dict, actions_result: Dict, score: float = 65) -> Dict:
        """生成 Leader 指导提纲"""
        account_name = diagnosis_result["account_name"]
        print(f"[指导提纲] 正在为 {account_name} 生成1on1指导提纲")

        diag = diagnosis_result.get("diagnosis", {})
        problems = diag.get("problems", [])

        # 诊断摘要
        diagnosis_summary = f"整体健康: {diag.get('overall_health', 'unknown')}\n"
        for p in problems:
            diagnosis_summary += f"- {p.get('title', '')}（{p.get('dimension', '')}）\n"

        # 行动建议摘要
        actions = actions_result.get("actions", [])
        actions_summary = ""
        for a in actions:
            actions_summary += f"- [{a.get('priority', '')}] {a.get('action', '')[:80]}...\n"

        user_prompt = COACHING_USER_PROMPT_TEMPLATE.format(
            account_name=account_name,
            operator=diagnosis_result["operator"],
            score=score,
            diagnosis_summary=diagnosis_summary,
            actions_summary=actions_summary,
        )

        outline = self.llm.chat_json(COACHING_SYSTEM_PROMPT, user_prompt, temperature=0.5)

        return {
            "account_id": diagnosis_result["account_id"],
            "account_name": account_name,
            "operator": diagnosis_result["operator"],
            "coaching_outline": outline,
        }

    def generate_all_coaching(self, diagnosis_results: List[Dict], actions_results: List[Dict], scores: Dict = None) -> List[Dict]:
        """为所有账号生成指导提纲"""
        results = []
        for diag, actions in zip(diagnosis_results, actions_results):
            score = 65
            if scores and diag["account_id"] in scores:
                score = scores[diag["account_id"]].get("total", 65)
            outline = self.generate_coaching_outline(diag, actions, score)
            results.append(outline)
        return results

    def save_action_plans(self, actions_results: List[Dict], coaching_results: List[Dict], output_dir: str):
        """保存行动建议和指导提纲"""
        os.makedirs(output_dir, exist_ok=True)

        with open(os.path.join(output_dir, "action_plans.json"), "w", encoding="utf-8") as f:
            json.dump(actions_results, f, ensure_ascii=False, indent=2)

        with open(os.path.join(output_dir, "coaching_outlines.json"), "w", encoding="utf-8") as f:
            json.dump(coaching_results, f, ensure_ascii=False, indent=2)

        # 生成可读报告
        md = self._generate_action_report(actions_results, coaching_results)
        with open(os.path.join(output_dir, "action_and_coaching_report.md"), "w", encoding="utf-8") as f:
            f.write(md)

        return md

    def _generate_action_report(self, actions_results: List[Dict], coaching_results: List[Dict]) -> str:
        """生成行动建议和指导提纲的可读报告"""
        lines = ["# 下周行动建议与 Leader 指导提纲\n"]

        # 行动建议汇总
        lines.append("## 一、各账号下周行动建议汇总\n")
        lines.append("| 账号 | 运营 | P0动作数 | P1动作数 | 总动作数 |")
        lines.append("|------|------|---------|---------|---------|")
        for ar in actions_results:
            actions = ar.get("actions", [])
            p0 = sum(1 for a in actions if a.get("priority") == "P0")
            p1 = sum(1 for a in actions if a.get("priority") == "P1")
            lines.append(f"| {ar['account_name']} | {ar['operator']} | {p0} | {p1} | {len(actions)} |")
        lines.append("")

        # 逐账号详细行动建议
        lines.append("## 二、逐账号行动建议详情\n")
        for i, ar in enumerate(actions_results, 1):
            lines.append(f"### {i}. {ar['account_name']}（{ar['operator']}）\n")
            actions = ar.get("actions", [])
            for j, a in enumerate(actions, 1):
                priority_icon = {"P0": "🔴", "P1": "🟡", "P2": "🟢"}.get(a.get("priority", "P2"), "⚪")
                difficulty_icon = {"low": "⭐", "medium": "⭐⭐", "high": "⭐⭐⭐"}.get(a.get("difficulty", "medium"), "⭐⭐")
                lines.append(f"**{j}. {priority_icon} [{a.get('priority', '')}] {a.get('action', '')[:60]}...**")
                lines.append(f"- 完整动作: {a.get('action', '')}")
                lines.append(f"- 预期成果: {a.get('expected_outcome', '')}")
                lines.append(f"- 时间节点: {a.get('deadline', '')}")
                lines.append(f"- 难度: {difficulty_icon} {a.get('difficulty', '')}")
                lines.append(f"- 所需资源: {a.get('required_resources', '无')}")
                lines.append(f"- 关联问题: {a.get('linked_problem', '')}")
                lines.append("")

        # Leader 指导提纲
        lines.append("---\n")
        lines.append("## 三、Leader 1on1 指导提纲\n")

        for i, cr in enumerate(coaching_results, 1):
            outline = cr.get("coaching_outline", {})
            lines.append(f"### {i}. {cr['account_name']} — 与 {cr['operator']} 的1on1\n")
            lines.append(f"**建议时长**: {outline.get('meeting_duration', '30分钟')}\n")

            agenda = outline.get("agenda", [])
            if isinstance(agenda, list):
                for j, item in enumerate(agenda, 1):
                    lines.append(f"**{j}. {item.get('section', '')}**")
                    lines.append(f"- 目的: {item.get('purpose', '')}")
                    lines.append("- 要点:")
                    for kp in item.get("key_points", []):
                        lines.append(f"  - {kp}")
                    lines.append(f"- Leader注意: {item.get('leader_tips', '')}")
                    lines.append("")

            do_dont = outline.get("do_and_dont", {})
            if do_dont:
                lines.append("**沟通注意事项**:")
                lines.append("\n✅ 应该做:")
                for d in do_dont.get("do", []):
                    lines.append(f"- {d}")
                lines.append("\n❌ 不应该做:")
                for d in do_dont.get("dont", []):
                    lines.append(f"- {d}")
                lines.append("")

            lines.append("---\n")

        return "\n".join(lines)
