"""
多账号复盘与 Leader 指导 Agent — 主工作流
Multi-Account Review & Leader Coaching Agent - Main Workflow

使用方式:
    python -m src.main --demo              # 运行完整周复盘 Demo
    python -m src.main --daily             # 运行每日报告
    python -m src.main --step collect      # 采集多账号数据
    python -m src.main --step diagnose     # 账号诊断与归因
    python -m src.main --step action       # 生成行动建议和指导提纲
    python -m src.main --step report       # 生成每日报告和评分
    python -m src.main --step track        # 执行追踪闭环
"""

import argparse
import json
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.data_loader import generate_full_dataset, save_mock_data
from src.llm_client import LLMClient
from src.diagnoser import AccountDiagnoser
from src.action_planner import ActionPlanner
from src.reporter import AccountScorer, DailyReporter
from src.tracker import ActionTracker


class MultiAccountAgent:
    """
    多账号复盘与 Leader 指导 Agent
    完整工作流：数据采集 → 诊断归因 → 行动建议+指导提纲 → 每日报告+评分 → 执行追踪闭环
    """

    def __init__(self, output_dir: str = None, use_mock: bool = None):
        self.base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.output_dir = output_dir or os.path.join(self.base_dir, "data", "output")
        self.data_dir = os.path.join(self.base_dir, "data")

        os.makedirs(self.output_dir, exist_ok=True)
        os.makedirs(self.data_dir, exist_ok=True)

        # 初始化组件
        self.llm = LLMClient(use_mock=use_mock)
        self.diagnoser = AccountDiagnoser(self.llm)
        self.action_planner = ActionPlanner(self.llm)
        self.scorer = AccountScorer()
        self.reporter = DailyReporter(self.llm, self.scorer)
        self.tracker = ActionTracker(
            tracking_file=os.path.join(self.output_dir, "tracking_data.json")
        )

        # 数据存储
        self.dataset = {}
        self.diagnosis_results = []
        self.action_results = []
        self.coaching_results = []
        self.scores = {}
        self.daily_report = {}
        self.tracking_report = {}

        print(f"\n{'='*60}")
        print(f"  多账号复盘与 Leader 指导 Agent")
        print(f"  输出目录: {self.output_dir}")
        print(f"{'='*60}\n")

    def step_collect(self):
        """步骤1: 采集多账号数据"""
        print("📥 [步骤1/5] 采集多账号数据")
        print("-" * 50)

        self.dataset = generate_full_dataset()

        # 保存原始数据
        raw_path = os.path.join(self.data_dir, "account_dataset.json")
        with open(raw_path, "w", encoding="utf-8") as f:
            json.dump(self.dataset, f, ensure_ascii=False, indent=2)

        # 统计
        accounts = self.dataset["accounts"]
        total_contents = sum(len(v) for v in self.dataset["contents"].values())

        print(f"  ✓ 采集完成: {len(accounts)} 个账号")
        for acc in accounts:
            contents = self.dataset["contents"].get(acc["account_id"], [])
            print(f"    - {acc['account_name']}（{acc['operator']}）: {len(contents)} 条内容, {acc['followers']} 粉丝")
        print(f"  ✓ 总内容数: {total_contents} 条")
        print(f"  ✓ 上周建议追踪数据: {len(self.dataset.get('last_week_actions', []))} 条")
        print(f"  ✓ 原始数据已保存: {raw_path}\n")

        return self.dataset

    def step_diagnose(self):
        """步骤2: 账号诊断与6维度归因"""
        print("🔍 [步骤2/5] 账号诊断与6维度归因")
        print("-" * 50)

        if not self.dataset:
            self.step_collect()

        self.diagnosis_results = self.diagnoser.diagnose_all(self.dataset)

        # 保存
        diagnosis_dir = os.path.join(self.output_dir, "01_diagnosis")
        report_md = self.diagnoser.save_diagnosis(self.diagnosis_results, diagnosis_dir)

        # 统计
        total_problems = sum(len(r.get("diagnosis", {}).get("problems", [])) for r in self.diagnosis_results)

        print(f"\n  ✓ 诊断完成: {len(self.diagnosis_results)} 个账号")
        print(f"  ✓ 识别问题总数: {total_problems} 个")
        for r in self.diagnosis_results:
            diag = r.get("diagnosis", {})
            problems = diag.get("problems", [])
            health = diag.get("overall_health", "unknown")
            print(f"    - {r['account_name']}: {health}, {len(problems)}个问题")
            for p in problems:
                print(f"      · [{p.get('dimension', '')}] {p.get('title', '')[:40]}")
        print(f"  ✓ 诊断报告已保存: {diagnosis_dir}/diagnosis_report.md\n")

        return self.diagnosis_results

    def step_action(self):
        """步骤3: 生成行动建议和Leader指导提纲"""
        print("📋 [步骤3/5] 生成行动建议与 Leader 指导提纲")
        print("-" * 50)

        if not self.diagnosis_results:
            self.step_diagnose()

        # 生成行动建议
        self.action_results = self.action_planner.generate_all_actions(self.diagnosis_results)

        # 计算评分（用于指导提纲）
        self.scores = self.scorer.score_all(self.diagnosis_results)

        # 生成指导提纲
        self.coaching_results = self.action_planner.generate_all_coaching(
            self.diagnosis_results, self.action_results, self.scores
        )

        # 保存
        action_dir = os.path.join(self.output_dir, "02_action_plan")
        report_md = self.action_planner.save_action_plans(
            self.action_results, self.coaching_results, action_dir
        )

        # 统计
        total_actions = sum(len(r.get("actions", [])) for r in self.action_results)
        p0_actions = sum(
            1 for r in self.action_results
            for a in r.get("actions", [])
            if a.get("priority") == "P0"
        )

        print(f"\n  ✓ 行动建议生成完成: {total_actions} 条（P0: {p0_actions} 条）")
        for r in self.action_results:
            actions = r.get("actions", [])
            print(f"    - {r['account_name']}: {len(actions)} 条动作")
        print(f"  ✓ Leader 指导提纲: {len(self.coaching_results)} 份")
        print(f"  ✓ 报告已保存: {action_dir}/action_and_coaching_report.md\n")

        return self.action_results, self.coaching_results

    def step_report(self):
        """步骤4: 生成每日报告和账号评分"""
        print("📊 [步骤4/5] 生成每日报告与账号评分")
        print("-" * 50)

        if not self.dataset:
            self.step_collect()
        if not self.diagnosis_results:
            self.step_diagnose()
        if not self.scores:
            self.scores = self.scorer.score_all(self.diagnosis_results)

        # 生成每日报告
        self.daily_report = self.reporter.generate_daily_report(
            self.dataset, self.diagnosis_results, self.scores,
            pending_actions=self.dataset.get("last_week_actions", [])
        )

        # 保存
        report_dir = os.path.join(self.output_dir, "03_daily_report")
        report_md = self.reporter.save_report(self.daily_report, report_dir)

        # 保存评分详情
        scores_path = os.path.join(report_dir, "account_scores.json")
        with open(scores_path, "w", encoding="utf-8") as f:
            json.dump(self.scores, f, ensure_ascii=False, indent=2)

        # 打印评分
        print(f"\n  ✓ 每日报告生成完成")
        print(f"  ✓ 账号评分:")
        for acc_id, score in self.scores.items():
            acc_name = next(
                (a["account_name"] for a in self.dataset["accounts"] if a["account_id"] == acc_id),
                acc_id
            )
            icon = "🟢" if score["total"] >= 70 else "🟡" if score["total"] >= 55 else "🔴"
            print(f"    {icon} {acc_name}: {score['total']}/100 ({score['level_desc']})")
            bd = score["breakdown"]
            print(f"       内容质量{bd['content_quality']} | 选题{bd['topic_relevance']} | 节奏{bd['posting_rhythm']} | 互动{bd['engagement_health']} | 增长{bd['growth']}")
        print(f"  ✓ 报告已保存: {report_dir}/daily_report_{self.daily_report['report_date']}.md\n")

        return self.daily_report, self.scores

    def step_track(self):
        """步骤5: 执行追踪闭环"""
        print("🔄 [步骤5/5] 执行追踪与闭环验证")
        print("-" * 50)

        if not self.dataset:
            self.step_collect()

        # 加载上周建议
        last_week_actions = self.tracker.load_last_week_actions(self.dataset)

        if not last_week_actions:
            print("  ⚠️ 无上周建议数据，跳过追踪")
            return None

        # 执行追踪
        self.tracking_report = self.tracker.track_execution(last_week_actions)

        # 保存
        track_dir = os.path.join(self.output_dir, "04_tracking")
        report_md = self.tracker.save_tracking_report(self.tracking_report, track_dir)

        # 统计
        s = self.tracking_report["stats"]
        print(f"\n  ✓ 追踪完成: {s['total']} 条上周建议")
        print(f"  ✓ 已执行且有改善: {s['executed_improved']} 条")
        print(f"  ✓ 已执行但无改善: {s['executed_no_improvement']} 条")
        print(f"  ✓ 部分执行: {s['partially_executed']} 条")
        print(f"  ✓ 未执行: {s['not_executed']} 条")
        print(f"  ✓ 整体执行率: {self.tracking_report['execution_rate']*100:.0f}%")
        print(f"  ✓ 闭环改进建议: {len(self.tracking_report['closed_loop_suggestions'])} 条")
        print(f"  ✓ 追踪报告已保存: {track_dir}/tracking_report.md\n")

        return self.tracking_report

    def run_full_demo(self):
        """运行完整 Demo（周复盘模式）"""
        print("\n" + "🚀" * 30)
        print("  开始运行完整 Demo — 多账号复盘与 Leader 指导 Agent")
        print("🚀" * 30 + "\n")

        start_time = datetime.now()

        # 执行所有步骤
        self.step_collect()
        self.step_diagnose()
        self.step_action()
        self.step_report()
        self.step_track()

        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        # 输出总结
        print("=" * 60)
        print("  ✅ Demo 运行完成！")
        print("=" * 60)
        print(f"  总耗时: {duration:.1f} 秒")
        print(f"  输出目录: {self.output_dir}")
        print("\n  生成的文件:")
        print("  ├── 01_diagnosis/           # 账号诊断报告（6维度归因）")
        print("  │   ├── diagnosis_report.md")
        print("  │   └── diagnosis_details.json")
        print("  ├── 02_action_plan/         # 行动建议 + Leader指导提纲")
        print("  │   ├── action_and_coaching_report.md")
        print("  │   ├── action_plans.json")
        print("  │   └── coaching_outlines.json")
        print("  ├── 03_daily_report/        # 每日报告 + 账号评分")
        print("  │   ├── daily_report_*.md")
        print("  │   └── account_scores.json")
        print("  ├── 04_tracking/            # 执行追踪闭环报告")
        print("  │   ├── tracking_report.md")
        print("  │   └── tracking_report.json")
        print("  └── tracking_data.json       # 追踪历史数据")
        print("\n" + "=" * 60)

        # 生成总览
        self._generate_summary()

    def run_daily(self):
        """运行每日报告模式"""
        print("\n" + "📊" * 20)
        print("  每日报告模式")
        print("📊" * 20 + "\n")

        self.step_collect()
        self.step_diagnose()
        self.step_report()

        print("\n✅ 每日报告生成完成！")

    def _generate_summary(self):
        """生成总览文档"""
        summary_path = os.path.join(self.output_dir, "README_总览.md")
        lines = [
            "# 多账号复盘与 Leader 指导 Agent — Demo 输出总览\n",
            f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n",
            "## 工作流概览\n",
            "```",
            "数据采集 → 诊断归因 → 行动建议+指导提纲 → 每日报告+评分 → 执行追踪闭环",
            "```\n",
            "## 输出文件说明\n",
            "| 目录 | 内容 | 关键文件 |",
            "|------|------|----------|",
            "| 01_diagnosis | 3个账号的诊断报告（1-3个主要问题+6维度归因） | diagnosis_report.md |",
            "| 02_action_plan | 下周行动建议（SMART原则）+ Leader 1on1指导提纲 | action_and_coaching_report.md |",
            "| 03_daily_report | 每日运营报告 + 5维度账号评分 | daily_report_*.md |",
            "| 04_tracking | 上周建议执行追踪 + 闭环改进建议 | tracking_report.md |\n",
            "## 3个模拟账号的预设问题\n",
            "| 账号 | 运营 | 预设问题 | 主要归因维度 |",
            "|------|------|---------|-------------|",
            "| AI技术日报 | 张三 | 内容质量好但互动差，运营不回复评论 | 互动 |",
            "| 产品增长实验室 | 李四 | 选题混乱定位模糊，什么都发 | 选题/定位 |",
            "| 创业故事集 | 王五 | 发布节奏不稳定，频繁断更 | 发布节奏 |\n",
            "## 核心设计亮点\n",
            "1. **6维度精准归因**: 内容质量/选题/定位/发布节奏/互动/账号健康，规则引擎+LLM双保险",
            "2. **SMART行动建议**: 每个动作具体到可直接执行，有预期成果、时间节点、难度和所需资源",
            "3. **Leader指导提纲**: 结构化1on1沟通框架，先肯定再提问题，苏格拉底式提问引导，赋能而非批评",
            "4. **5维度加权评分**: 内容质量25%+选题20%+节奏15%+互动20%+增长20%，趋势一目了然",
            "5. **执行追踪闭环**: 追踪建议是否执行、执行后是否改善，未执行/无改善都有原因分析和改进建议",
            "6. **人工审核合规**: Agent只做分析和建议，不自动操作账号，所有建议需人工确认\n",
            "## 运行方式\n",
            "```bash",
            "# 完整周复盘Demo",
            "python -m src.main --demo --mock",
            "",
            "# 每日报告模式",
            "python -m src.main --daily --mock",
            "",
            "# 逐步运行",
            "python -m src.main --step diagnose --mock",
            "python -m src.main --step action --mock",
            "```\n",
        ]

        with open(summary_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

        print(f"\n  📋 总览报告已生成: {summary_path}\n")


def main():
    parser = argparse.ArgumentParser(description="多账号复盘与 Leader 指导 Agent")
    parser.add_argument("--demo", action="store_true", help="运行完整周复盘 Demo")
    parser.add_argument("--daily", action="store_true", help="运行每日报告模式")
    parser.add_argument("--step", type=str,
                        choices=["collect", "diagnose", "action", "report", "track"],
                        help="运行单个步骤")
    parser.add_argument("--output", type=str, default=None, help="输出目录")
    parser.add_argument("--mock", action="store_true", help="强制使用 Mock 模式")
    parser.add_argument("--no-mock", action="store_true", help="强制使用真实 API")

    args = parser.parse_args()

    use_mock = None
    if args.mock:
        use_mock = True
    elif args.no_mock:
        use_mock = False

    agent = MultiAccountAgent(output_dir=args.output, use_mock=use_mock)

    if args.demo:
        agent.run_full_demo()
    elif args.daily:
        agent.run_daily()
    elif args.step:
        step_map = {
            "collect": agent.step_collect,
            "diagnose": agent.step_diagnose,
            "action": agent.step_action,
            "report": agent.step_report,
            "track": agent.step_track,
        }
        step_map[args.step]()
        print(f"\n✅ 步骤 [{args.step}] 执行完成")
    else:
        parser.print_help()
        print("\n提示: 使用 --demo 运行完整周复盘，或 --daily 运行每日报告")


if __name__ == "__main__":
    main()
