"""
执行追踪闭环模块
持续追踪建议是否执行、执行后是否带来改善，形成"诊断→建议→执行→验证"闭环
"""

import json
import os
from typing import Dict, List
from datetime import datetime


class ActionTracker:
    """
    行动建议追踪器
    追踪每个建议的执行状态和效果
    """

    def __init__(self, tracking_file: str = None):
        self.tracking_file = tracking_file
        self.tracking_data = self._load_tracking_data()

    def _load_tracking_data(self) -> Dict:
        """加载追踪数据"""
        if self.tracking_file and os.path.exists(self.tracking_file):
            try:
                with open(self.tracking_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                print(f"[追踪] 加载追踪数据失败: {e}")
        return {
            "version": "1.0",
            "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "history": [],
            "current_week_actions": [],
            "iteration_count": 0,
        }

    def save_tracking_data(self):
        """保存追踪数据"""
        if not self.tracking_file:
            return
        os.makedirs(os.path.dirname(self.tracking_file), exist_ok=True)
        self.tracking_data["last_updated"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(self.tracking_file, "w", encoding="utf-8") as f:
            json.dump(self.tracking_data, f, ensure_ascii=False, indent=2)

    def set_current_week_actions(self, actions: List[Dict]):
        """设置本周的行动建议（来自 action_planner）"""
        self.tracking_data["current_week_actions"] = actions
        self.save_tracking_data()

    def load_last_week_actions(self, dataset: Dict) -> List[Dict]:
        """加载上周的行动建议（用于追踪演示）"""
        return dataset.get("last_week_actions", [])

    def track_execution(self, last_week_actions: List[Dict], current_metrics: Dict = None) -> Dict:
        """
        追踪上周建议的执行情况和效果

        Args:
            last_week_actions: 上周的行动建议列表
            current_metrics: 当前账号指标（用于验证效果）

        Returns:
            追踪报告
        """
        print(f"[追踪] 正在追踪 {len(last_week_actions)} 条上周建议的执行情况")

        results = []
        stats = {
            "total": len(last_week_actions),
            "executed": 0,
            "not_executed": 0,
            "partially_executed": 0,
            "executed_improved": 0,
            "executed_no_improvement": 0,
        }

        for action in last_week_actions:
            status = action.get("status", "unknown")
            result = {
                "action_id": action.get("action_id", ""),
                "account_id": action.get("account_id", ""),
                "action": action.get("action", ""),
                "status": status,
                "status_desc": self._get_status_desc(status),
                "expected_outcome": action.get("expected_outcome", ""),
                "actual_outcome": action.get("actual_outcome", "待验证"),
                "reason": action.get("reason", ""),
            }

            # 统计
            if status == "executed_improved":
                stats["executed"] += 1
                stats["executed_improved"] += 1
                result["verdict"] = "✅ 已执行且有改善"
            elif status == "executed_no_improvement":
                stats["executed"] += 1
                stats["executed_no_improvement"] += 1
                result["verdict"] = "⚠️ 已执行但无明显改善，需分析原因"
            elif status == "partially_executed":
                stats["partially_executed"] += 1
                result["verdict"] = "🟡 部分执行，未完全达标"
            elif status == "not_executed":
                stats["not_executed"] += 1
                result["verdict"] = "🔴 未执行"
            else:
                result["verdict"] = "⚪ 状态未知"

            results.append(result)

        # 计算执行率
        execution_rate = (stats["executed"] + stats["partially_executed"] * 0.5) / stats["total"] if stats["total"] > 0 else 0
        improvement_rate = stats["executed_improved"] / stats["executed"] if stats["executed"] > 0 else 0

        # 生成闭环建议
        closed_loop_suggestions = self._generate_closed_loop_suggestions(results)

        report = {
            "tracking_date": datetime.now().strftime("%Y-%m-%d"),
            "iteration": self.tracking_data.get("iteration_count", 0) + 1,
            "results": results,
            "stats": stats,
            "execution_rate": round(execution_rate, 2),
            "improvement_rate": round(improvement_rate, 2),
            "closed_loop_suggestions": closed_loop_suggestions,
        }

        # 记录到历史
        self.tracking_data["history"].append({
            "date": report["tracking_date"],
            "iteration": report["iteration"],
            "execution_rate": report["execution_rate"],
            "stats": stats,
        })
        self.tracking_data["iteration_count"] = report["iteration"]
        self.save_tracking_data()

        return report

    def _get_status_desc(self, status: str) -> str:
        """状态描述"""
        desc_map = {
            "executed_improved": "已执行且有改善",
            "executed_no_improvement": "已执行但无改善",
            "partially_executed": "部分执行",
            "not_executed": "未执行",
            "pending": "待执行",
        }
        return desc_map.get(status, status)

    def _generate_closed_loop_suggestions(self, results: List[Dict]) -> List[Dict]:
        """生成闭环改进建议"""
        suggestions = []

        # 未执行的建议
        not_executed = [r for r in results if r["status"] == "not_executed"]
        if not_executed:
            reasons = set(r.get("reason", "") for r in not_executed if r.get("reason"))
            suggestions.append({
                "type": "未执行改进",
                "target": [r["action_id"] for r in not_executed],
                "suggestion": f"有{len(not_executed)}条建议未执行，主要原因: {'; '.join(reasons) if reasons else '未说明'}。建议：1) 与运营同学1on1时深入了解未执行的真实障碍；2) 将动作拆解为更小的步骤，降低执行门槛；3) 设定每日提醒，建立执行习惯。",
                "priority": "high",
            })

        # 执行了但无改善
        no_improvement = [r for r in results if r["status"] == "executed_no_improvement"]
        if no_improvement:
            suggestions.append({
                "type": "无效动作优化",
                "target": [r["action_id"] for r in no_improvement],
                "suggestion": f"有{len(no_improvement)}条建议已执行但无改善。可能原因：动作本身不对症、执行不到位、或存在其他制约因素。建议：1) 深入分析根因，可能需要调整动作方向；2) 检查执行质量，是否真的按要求做了；3) 考虑组合拳，单一动作可能不足以改变局面。",
                "priority": "high",
            })

        # 部分执行
        partial = [r for r in results if r["status"] == "partially_executed"]
        if partial:
            suggestions.append({
                "type": "部分执行跟进",
                "target": [r["action_id"] for r in partial],
                "suggestion": f"有{len(partial)}条建议部分执行，有改善趋势但未达标。建议：1) 肯定已取得的进展，增强运营同学信心；2) 分析未完全达标的原因，针对性调整；3) 下周继续执行，给予更多时间看到效果。",
                "priority": "medium",
            })

        # 已执行且有改善
        improved = [r for r in results if r["status"] == "executed_improved"]
        if improved:
            suggestions.append({
                "type": "有效动作固化",
                "target": [r["action_id"] for r in improved],
                "suggestion": f"有{len(improved)}条建议已执行且有改善。建议：1) 将这些有效动作固化为日常运营SOP；2) 总结成功经验，复制到其他账号；3) 在该方向上持续加码，争取更大提升。",
                "priority": "medium",
            })

        if not suggestions:
            suggestions.append({
                "type": "整体评估",
                "target": [],
                "suggestion": "本周建议执行情况良好，继续保持当前节奏，关注长期趋势。",
                "priority": "low",
            })

        return suggestions

    def save_tracking_report(self, report: Dict, output_dir: str):
        """保存追踪报告"""
        os.makedirs(output_dir, exist_ok=True)

        with open(os.path.join(output_dir, "tracking_report.json"), "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        md = self._generate_tracking_markdown(report)
        with open(os.path.join(output_dir, "tracking_report.md"), "w", encoding="utf-8") as f:
            f.write(md)

        return md

    def _generate_tracking_markdown(self, report: Dict) -> str:
        """生成追踪报告 Markdown"""
        lines = ["# 行动建议执行追踪与闭环报告\n"]
        lines.append(f"**追踪日期**: {report['tracking_date']}")
        lines.append(f"**迭代轮次**: 第 {report['iteration']} 轮\n")

        # 统计概览
        s = report["stats"]
        lines.append("## 一、执行情况概览\n")
        lines.append(f"- 上周建议总数: {s['total']} 条")
        lines.append(f"- ✅ 已执行且有改善: {s['executed_improved']} 条")
        lines.append(f"- ⚠️ 已执行但无改善: {s['executed_no_improvement']} 条")
        lines.append(f"- 🟡 部分执行: {s['partially_executed']} 条")
        lines.append(f"- 🔴 未执行: {s['not_executed']} 条")
        lines.append(f"- **整体执行率**: {report['execution_rate']*100:.0f}%")
        lines.append(f"- **有效动作占比**: {report['improvement_rate']*100:.0f}%（已执行动作中有改善的比例）")
        lines.append("")

        # 执行率评级
        if report["execution_rate"] >= 0.8:
            exec_level = "🟢 优秀"
        elif report["execution_rate"] >= 0.6:
            exec_level = "🟡 良好"
        elif report["execution_rate"] >= 0.4:
            exec_level = "🟠 一般"
        else:
            exec_level = "🔴 需改进"
        lines.append(f"**执行率评级**: {exec_level}\n")

        # 逐条追踪
        lines.append("## 二、逐条追踪详情\n")
        for i, r in enumerate(report["results"], 1):
            lines.append(f"### {i}. {r['verdict']}\n")
            lines.append(f"**动作ID**: {r['action_id']}")
            lines.append(f"**账号**: {r['account_id']}")
            lines.append(f"**状态**: {r['status_desc']}")
            lines.append(f"**动作内容**: {r['action']}")
            lines.append(f"**预期成果**: {r['expected_outcome']}")
            lines.append(f"**实际成果**: {r['actual_outcome']}")
            if r.get("reason"):
                lines.append(f"**原因分析**: {r['reason']}")
            lines.append("")

        # 闭环建议
        lines.append("## 三、闭环改进建议\n")
        for i, sug in enumerate(report["closed_loop_suggestions"], 1):
            priority_icon = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(sug.get("priority", "low"), "⚪")
            lines.append(f"### {i}. {priority_icon} [{sug.get('type', '')}]\n")
            lines.append(f"{sug.get('suggestion', '')}\n")
            if sug.get("target"):
                lines.append(f"**涉及动作**: {', '.join(sug['target'])}\n")

        # 闭环说明
        lines.append("---\n")
        lines.append("## 四、闭环机制说明\n")
        lines.append("本追踪系统形成完整闭环：")
        lines.append("1. **诊断** → 识别账号问题")
        lines.append("2. **建议** → 生成具体行动")
        lines.append("3. **执行** → 运营同学执行动作")
        lines.append("4. **追踪** → 验证是否执行、是否改善")
        lines.append("5. **反馈** → 根据追踪结果调整下周诊断和建议")
        lines.append("")
        lines.append("每轮迭代都会让诊断更精准、建议更可执行、执行率更高，形成持续优化的正向循环。\n")

        return "\n".join(lines)
