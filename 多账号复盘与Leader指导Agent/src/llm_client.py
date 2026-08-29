"""
LLM 客户端封装
支持 OpenAI API 调用和 Mock 模式（无 API Key 时使用内置模拟响应）
"""

import json
import os
import re
from typing import Dict, Optional


class LLMClient:
    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4o", use_mock: bool = None):
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        self.model = model
        self.use_mock = use_mock if use_mock is not None else (self.api_key is None)

        if self.use_mock:
            print("[LLM] 使用 Mock 模式（未检测到 OPENAI_API_KEY）")
        else:
            print(f"[LLM] 使用真实 API 模式，模型: {self.model}")

    def chat(self, system_prompt: str, user_prompt: str, temperature: float = 0.7) -> str:
        if self.use_mock:
            return self._mock_response(system_prompt, user_prompt)

        try:
            import openai
            client = openai.OpenAI(api_key=self.api_key)
            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=temperature,
            )
            return response.choices[0].message.content
        except ImportError:
            print("[LLM] 未安装 openai 库，回退到 Mock 模式")
            self.use_mock = True
            return self._mock_response(system_prompt, user_prompt)
        except Exception as e:
            print(f"[LLM] API 调用失败: {e}，回退到 Mock 模式")
            self.use_mock = True
            return self._mock_response(system_prompt, user_prompt)

    def chat_json(self, system_prompt: str, user_prompt: str, temperature: float = 0.3) -> Dict:
        text = self.chat(system_prompt, user_prompt, temperature)
        return self._parse_json(text)

    def _parse_json(self, text: str) -> Dict:
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        json_match = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', text, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass

        brace_match = re.search(r'\{.*\}', text, re.DOTALL)
        if brace_match:
            try:
                return json.loads(brace_match.group(0))
            except json.JSONDecodeError:
                pass

        bracket_match = re.search(r'\[.*\]', text, re.DOTALL)
        if bracket_match:
            try:
                return json.loads(bracket_match.group(0))
            except json.JSONDecodeError:
                pass

        print(f"[LLM] JSON 解析失败，原始文本: {text[:200]}...")
        return {"_raw_text": text, "_parse_error": True}

    def _mock_response(self, system_prompt: str, user_prompt: str) -> str:
        # 行动建议任务（优先判断，因为prompt中可能包含"主要问题"等诊断相关词）
        if "行动建议" in user_prompt or ("下周" in user_prompt and "动作" in user_prompt):
            return self._mock_action_response(user_prompt)

        # Leader指导提纲
        if "指导提纲" in user_prompt or "1on1" in user_prompt or "一对一" in user_prompt:
            return self._mock_coaching_response(user_prompt)

        # 每日报告
        if "每日报告" in user_prompt or "日报" in user_prompt:
            return self._mock_daily_report_response(user_prompt)

        # 诊断任务（最后判断）
        if "诊断" in user_prompt or ("主要问题" in user_prompt and "维度" in user_prompt):
            return self._mock_diagnosis_response(user_prompt)

        return json.dumps({"status": "mock", "message": "这是Mock模式的默认响应"})

    def _mock_diagnosis_response(self, user_prompt: str) -> str:
        """模拟诊断响应"""
        # 根据账号ID或名称返回不同的诊断结果
        if "ai_tech_daily" in user_prompt or "AI技术日报" in user_prompt or "AI技术" in user_prompt:
            result = {
                "account_id": "ai_tech_daily",
                "overall_health": "medium",
                "problems": [
                    {
                        "problem_id": "p001",
                        "severity": "high",
                        "title": "互动率严重偏低，运营不回复评论",
                        "description": "近14天平均回复率仅0.4%，远低于行业基准3%。运营同学几乎不回复用户评论，导致用户互动意愿低。",
                        "dimension": "互动",
                        "secondary_dimensions": [],
                        "evidence": [
                            "近14天28条内容，总回复数仅47条，平均每条1.7条评论",
                            "运营回复率0%，没有一条内容下有运营的回复",
                            "最高表现内容的回复也仅5条，说明用户缺乏评论动力"
                        ],
                        "impact": "互动率低导致账号权重下降，内容触达减少，形成恶性循环。用户评论后得不到反馈，下次就不再评论。"
                    },
                    {
                        "problem_id": "p002",
                        "severity": "medium",
                        "title": "内容缺乏互动引导设计",
                        "description": "内容质量较高，但末尾没有提问、投票等互动引导，用户看完就走，缺乏评论的理由。",
                        "dimension": "内容质量",
                        "secondary_dimensions": ["互动"],
                        "evidence": [
                            "28条内容中仅2条末尾有提问",
                            "有提问的2条内容平均回复3.5条，无提问的平均1.2条"
                        ],
                        "impact": "即使内容质量好，没有互动引导也无法激发用户评论，进一步加剧互动率低的问题。"
                    }
                ]
            }
        elif "product_growth_lab" in user_prompt or "产品增长实验室" in user_prompt or "产品增长" in user_prompt:
            result = {
                "account_id": "product_growth_lab",
                "overall_health": "low",
                "problems": [
                    {
                        "problem_id": "p001",
                        "severity": "high",
                        "title": "选题混乱，定位模糊，非相关内容占比过高",
                        "description": "账号定位是产品增长，但近14天内容中美食、旅游、电影、健身等非相关内容占比达50%，用户无法形成稳定预期。",
                        "dimension": "选题",
                        "secondary_dimensions": ["定位"],
                        "evidence": [
                            "近14天32条内容中，16条与产品增长无关",
                            "非相关内容平均点赞28，相关内容平均点赞120，差距4倍以上",
                            "粉丝评论中多次出现\"这个号到底发什么的\"之类的困惑"
                        ],
                        "impact": "定位模糊导致老粉丝流失（近14天净掉粉120），新粉丝无法建立认知，账号增长停滞。"
                    },
                    {
                        "problem_id": "p002",
                        "severity": "medium",
                        "title": "内容质量参差不齐，缺乏深度",
                        "description": "相关内容也多为浅尝辄止的观点输出，缺乏案例和数据支撑，内容深度不足。",
                        "dimension": "内容质量",
                        "secondary_dimensions": [],
                        "evidence": [
                            "相关内容平均长度仅120字，多为一句话观点",
                            "包含具体案例或数据的内容仅占15%",
                            "转发率低，说明内容缺乏\"值得分享\"的价值"
                        ],
                        "impact": "内容深度不足导致转发率低，无法通过社交传播获取新粉丝，增长完全依赖自然推荐。"
                    }
                ]
            }
        elif "startup_stories" in user_prompt or "创业故事集" in user_prompt or "创业故事" in user_prompt:
            result = {
                "account_id": "startup_stories",
                "overall_health": "medium",
                "problems": [
                    {
                        "problem_id": "p001",
                        "severity": "high",
                        "title": "发布节奏极不稳定，频繁断更",
                        "description": "近14天中有10天完全没有发布内容，集中在4天发布了22条，发布频率变异系数超过1.2，用户无法形成阅读习惯。",
                        "dimension": "发布节奏",
                        "secondary_dimensions": [],
                        "evidence": [
                            "近14天仅4天有内容发布，断更最长达4天",
                            "发布日平均发5.5条，存在刷屏现象",
                            "断更后复更的第一条内容互动量比稳定期低40%"
                        ],
                        "impact": "断更导致账号活跃度下降，平台推荐量减少；集中发布导致用户刷屏反感，部分用户取关。"
                    },
                    {
                        "problem_id": "p002",
                        "severity": "medium",
                        "title": "发布时段不固定，未覆盖受众活跃高峰",
                        "description": "发布时间从早8点到晚11点都有，没有固定规律，且很少在受众最活跃的晚8-10点发布。",
                        "dimension": "发布节奏",
                        "secondary_dimensions": [],
                        "evidence": [
                            "22条内容的发布时段分布在8个不同小时段",
                            "晚8-10点发布的内容仅3条，但这3条的平均互动是其他时段的1.8倍",
                            "粉丝活跃数据显示晚9点是峰值，但该时段发布占比仅14%"
                        ],
                        "impact": "发布时段不对导致内容错过受众活跃高峰，初始互动量低，无法触发平台的二次推荐。"
                    }
                ]
            }
        else:
            result = {"account_id": "unknown", "problems": []}

        return json.dumps(result, ensure_ascii=False, indent=2)

    def _mock_action_response(self, user_prompt: str) -> str:
        """模拟行动建议响应"""
        if "ai_tech_daily" in user_prompt or "AI技术日报" in user_prompt or "AI技术" in user_prompt:
            result = {
                "account_id": "ai_tech_daily",
                "actions": [
                    {
                        "action_id": "a001",
                        "linked_problem": "p001",
                        "priority": "P0",
                        "action": "建立\"发布后2小时回复\"机制：每条内容发布后，运营同学必须在2小时内回复前5条评论，回复需包含具体内容（如\"这个问题我之前也遇到过，我的做法是...\"），不能只用\"谢谢\"等模板化回复",
                        "expected_outcome": "回复率从0.4%提升到2%以上，单条内容平均回复数从1.7提升到5以上",
                        "deadline": "下周一启动，全周执行",
                        "difficulty": "low",
                        "required_resources": "每天额外投入30分钟回复评论"
                    },
                    {
                        "action_id": "a002",
                        "linked_problem": "p002",
                        "priority": "P1",
                        "action": "内容末尾强制增加互动引导：每条Thread的最后一条必须是一个开放性问题，问题要与内容主题强相关，且答案不唯一，能引发讨论。例如\"你们在做RAG时遇到过这个问题吗？是怎么解决的？\"",
                        "expected_outcome": "有互动引导的内容占比从7%提升到100%，评论数提升30%",
                        "deadline": "下周所有新发布内容执行",
                        "difficulty": "low",
                        "required_resources": "无额外资源，写作时注意即可"
                    },
                    {
                        "action_id": "a003",
                        "linked_problem": "p001",
                        "priority": "P1",
                        "action": "主动互动：每天花15分钟，去同领域其他账号的高互动内容下发表有价值的评论（不是灌水），引导对方粉丝关注自己。每周至少主动评论20条",
                        "expected_outcome": "通过主动互动带来的新粉丝占比提升到15%以上",
                        "deadline": "下周开始执行，持续至少2周",
                        "difficulty": "medium",
                        "required_resources": "每天15分钟"
                    }
                ]
            }
        elif "product_growth_lab" in user_prompt or "产品增长实验室" in user_prompt or "产品增长" in user_prompt:
            result = {
                "account_id": "product_growth_lab",
                "actions": [
                    {
                        "action_id": "a001",
                        "linked_problem": "p001",
                        "priority": "P0",
                        "action": "内容选题聚焦：制定\"80/20内容规则\"——80%的内容必须与产品增长强相关（产品方法论、增长案例、数据分析、A/B测试等），最多20%可以是泛互联网/职场相关内容，完全禁止美食、旅游、电影、健身等无关内容",
                        "expected_outcome": "非相关内容占比从50%降到20%以下，粉丝困惑评论消失",
                        "deadline": "下周一开始执行，全周严格遵守",
                        "difficulty": "medium",
                        "required_resources": "需要运营同学克制发生活类内容的冲动"
                    },
                    {
                        "action_id": "a002",
                        "linked_problem": "p002",
                        "priority": "P0",
                        "action": "提升内容深度：每条相关内容必须包含至少1个具体案例或1组数据支撑，不能只有观点。建立\"观点+案例+结论\"三段式写作模板，内容长度不低于200字",
                        "expected_outcome": "内容平均长度从120字提升到250字以上，转发率提升50%",
                        "deadline": "下周所有新发布内容执行",
                        "difficulty": "medium",
                        "required_resources": "每条内容写作时间增加15分钟"
                    },
                    {
                        "action_id": "a003",
                        "linked_problem": "p001",
                        "priority": "P1",
                        "action": "明确账号定位并对外声明：在账号简介中明确写清\"专注产品增长方法论与实战案例\"，并发布一条置顶内容说明账号定位和内容方向，让新粉丝一眼知道这个号是做什么的",
                        "expected_outcome": "新粉丝关注后的取关率下降，账号认知清晰度提升",
                        "deadline": "下周三前完成",
                        "difficulty": "low",
                        "required_resources": "无"
                    }
                ]
            }
        elif "startup_stories" in user_prompt or "创业故事集" in user_prompt or "创业故事" in user_prompt:
            result = {
                "account_id": "startup_stories",
                "actions": [
                    {
                        "action_id": "a001",
                        "linked_problem": "p001",
                        "priority": "P0",
                        "action": "制定内容日历并严格执行：提前一周规划好下周每天的内容选题，保证每周至少发布5条，每天最多发布2条，断更不超过2天。使用日历工具设置发布提醒",
                        "expected_outcome": "每周发布5条以上，断更不超过2天，发布频率变异系数降到0.5以下",
                        "deadline": "下周日完成下周内容日历，下周一开始执行",
                        "difficulty": "medium",
                        "required_resources": "周末额外投入1小时规划内容"
                    },
                    {
                        "action_id": "a002",
                        "linked_problem": "p002",
                        "priority": "P0",
                        "action": "固定发布时段：将主要内容发布时间固定在晚8:30-9:30（受众活跃高峰），每天最多在这个时段发布1条主内容，其他时段不发布或只发互动类短内容",
                        "expected_outcome": "晚8-10点发布的内容占比从14%提升到70%以上，初始互动量提升30%",
                        "deadline": "下周一开始执行",
                        "difficulty": "low",
                        "required_resources": "无"
                    },
                    {
                        "action_id": "a003",
                        "linked_problem": "p001",
                        "priority": "P1",
                        "action": "建立内容素材库：平时积累创业故事、案例、数据素材，分类整理，避免临时想选题导致断更。每周至少补充5条素材到素材库",
                        "expected_outcome": "素材库积累20条以上可用素材，断更原因中\"不知道写什么\"的比例降为0",
                        "deadline": "下周开始持续积累",
                        "difficulty": "low",
                        "required_resources": "每周30分钟整理素材"
                    }
                ]
            }
        else:
            result = {"account_id": "unknown", "actions": []}

        return json.dumps(result, ensure_ascii=False, indent=2)

    def _mock_coaching_response(self, user_prompt: str) -> str:
        """模拟Leader指导提纲响应"""
        if "ai_tech_daily" in user_prompt or "张三" in user_prompt:
            result = {
                "account_id": "ai_tech_daily",
                "operator": "张三",
                "meeting_duration": "30分钟",
                "agenda": [
                    {
                        "section": "开场与整体表现（5分钟）",
                        "purpose": "让运营同学了解账号整体状况，先肯定做得好的地方",
                        "key_points": [
                            "账号整体评分65分，内容质量维度得分最高（80分），说明内容本身是有竞争力的",
                            "近14天粉丝净增长350，虽然慢但在正增长",
                            "内容专业度受到认可，多条内容被行业KOL转发"
                        ],
                        "leader_tips": "开场先肯定内容质量，让张三知道他的核心能力没问题，问题出在运营环节而非内容本身"
                    },
                    {
                        "section": "核心问题探讨（10分钟）",
                        "purpose": "引导运营同学自己发现问题，而不是Leader直接批评",
                        "key_points": [
                            "互动率数据：平均每条内容仅1.7条评论，你觉得这个数据正常吗？",
                            "引导思考：你自己发了内容后，会去看评论吗？会回复吗？",
                            "用户视角：如果你在别人的内容下评论了，却从来得不到回复，你下次还会评论吗？",
                            "根因确认：互动率低的根本原因不是内容不好，而是没有形成\"评论-回复-再评论\"的正向循环"
                        ],
                        "leader_tips": "用苏格拉底式提问引导张三自己意识到\"不回复评论\"是问题根源，比直接告诉他\"你要回复评论\"有效得多。不要指责，要共同分析"
                    },
                    {
                        "section": "行动共识（8分钟）",
                        "purpose": "与运营同学共同确认下周具体动作，达成一致而非单方面下达",
                        "key_points": [
                            "动作1：发布后2小时内回复前5条评论——你觉得这个时间投入你能做到吗？有没有困难？",
                            "动作2：每条内容末尾加开放性问题——这个写作习惯需要调整，你觉得需要什么支持？",
                            "动作3：每天15分钟主动去同行账号下评论——这个你愿意试试吗？",
                            "确认优先级：三个动作中，你觉得哪个最容易先做起来？我们先从那个开始"
                        ],
                        "leader_tips": "每个动作都要问张三的意见和困难，不要直接安排。如果他觉得有困难，一起想办法降低难度，比如先从回复前3条开始而不是前5条"
                    },
                    {
                        "section": "资源支持与答疑（5分钟）",
                        "purpose": "了解运营同学需要什么帮助，扫清执行障碍",
                        "key_points": [
                            "回复评论需要时间，你目前每天的时间分配是怎样的？需要调整吗？",
                            "有没有什么工具或模板可以帮你提高回复效率？",
                            "内容写作方面需要什么支持？需要选题库还是案例库？",
                            "对账号发展有什么想法或困惑？"
                        ],
                        "leader_tips": "这部分要倾听为主，很多时候运营同学不执行不是因为懒，而是有实际困难没说出来。创造安全的表达环境"
                    },
                    {
                        "section": "收尾与下次约定（2分钟）",
                        "purpose": "鼓励信心，明确下次沟通时间",
                        "key_points": [
                            "总结：你的内容能力很强，只要把互动这个环节补上，账号表现会有明显提升",
                            "下周目标：先把\"回复前5条评论\"这个动作做起来，我们不追求一步到位",
                            "下次沟通：下周五同一时间，看看执行情况和数据变化",
                            "鼓励：我对你有信心，这个问题不难解决，我们一起推进"
                        ],
                        "leader_tips": "收尾一定要正面鼓励，让张三带着信心离开。不要把1on1开成批斗会，要开成赋能会"
                    }
                ],
                "do_and_dont": {
                    "do": [
                        "先肯定再提问题，维护运营同学的自信心",
                        "用提问引导而非直接告知，让对方自己得出结论",
                        "每个行动建议都征求对方意见，达成共识",
                        "关注对方的实际困难，提供必要支持",
                        "设定小而可实现的目标，不追求一步到位"
                    ],
                    "dont": [
                        "不要一上来就批评数据差",
                        "不要说\"你应该\"\"你必须\"，换成\"我们一起看看\"\"你觉得呢\"",
                        "不要一次性安排太多动作，先从1-2个开始",
                        "不要拿其他账号做横向比较贬低对方",
                        "不要只谈问题不谈支持，1on1是双向沟通不是单向考核"
                    ]
                }
            }
        else:
            # 通用模板
            result = {
                "account_id": "general",
                "operator": "运营同学",
                "meeting_duration": "30分钟",
                "agenda": [
                    {"section": "开场与整体表现（5分钟）", "key_points": ["账号整体评分", "本周亮点", "数据趋势"]},
                    {"section": "核心问题探讨（10分钟）", "key_points": ["主要问题", "根因分析", "引导思考"]},
                    {"section": "行动共识（8分钟）", "key_points": ["下周动作", "优先级确认", "困难排查"]},
                    {"section": "资源支持（5分钟）", "key_points": ["所需支持", "工具/培训", "答疑"]},
                    {"section": "收尾（2分钟）", "key_points": ["总结鼓励", "下次约定"]}
                ],
                "do_and_dont": {"do": ["先肯定再提问题", "用提问引导", "达成共识"], "dont": ["不要批评", "不要单方面下达"]}
            }

        return json.dumps(result, ensure_ascii=False, indent=2)

    def _mock_daily_report_response(self, user_prompt: str) -> str:
        """模拟每日报告响应"""
        result = {
            "report_date": "2026-08-29",
            "summary": "今日3个账号整体表现平稳，AI技术日报互动率仍偏低需关注，产品增长实验室非相关内容占比有所下降，创业故事集发布稳定性提升。",
            "accounts": [
                {
                    "account_id": "ai_tech_daily",
                    "account_name": "AI技术日报",
                    "daily_score": 62,
                    "score_change": -2,
                    "yesterday_data": {
                        "posts": 1,
                        "likes": 156,
                        "reposts": 45,
                        "replies": 2,
                        "follower_change": +25,
                    },
                    "alerts": [
                        {"level": "warning", "message": "昨日发布内容仅2条回复，回复率0.3%，持续低于基准线"},
                        {"level": "info", "message": "内容质量评分稳定在80分以上，核心能力保持良好"}
                    ],
                    "pending_actions": ["发布后2小时内回复前5条评论（已建议3天，未执行）"]
                },
                {
                    "account_id": "product_growth_lab",
                    "account_name": "产品增长实验室",
                    "daily_score": 55,
                    "score_change": +3,
                    "yesterday_data": {
                        "posts": 2,
                        "likes": 180,
                        "reposts": 52,
                        "replies": 18,
                        "follower_change": -5,
                    },
                    "alerts": [
                        {"level": "info", "message": "昨日2条内容均为产品增长相关，非相关内容占比下降，趋势向好"},
                        {"level": "warning", "message": "粉丝仍在净减少，定位模糊的负面影响尚未完全消除"}
                    ],
                    "pending_actions": ["内容选题聚焦80/20规则（部分执行中）", "更新账号简介明确 positioning（未执行）"]
                },
                {
                    "account_id": "startup_stories",
                    "account_name": "创业故事集",
                    "daily_score": 70,
                    "score_change": +5,
                    "yesterday_data": {
                        "posts": 1,
                        "likes": 320,
                        "reposts": 95,
                        "replies": 28,
                        "follower_change": +68,
                    },
                    "alerts": [
                        {"level": "success", "message": "连续3天有内容发布，断更问题改善，发布稳定性提升"},
                        {"level": "info", "message": "昨日内容在晚9点发布，互动量高于均值30%，时段选择正确"}
                    ],
                    "pending_actions": ["固定晚8:30-9:30发布（执行中）", "建立内容素材库（未执行）"]
                }
            ],
            "team_summary": {
                "total_posts_yesterday": 4,
                "total_engagement": 1234,
                "avg_account_score": 62.3,
                "best_performer": "创业故事集（70分）",
                "needs_attention": "AI技术日报（互动率持续偏低）",
                "action_execution_rate": "50%（上周4个建议中2个已执行）"
            }
        }
        return json.dumps(result, ensure_ascii=False, indent=2)
