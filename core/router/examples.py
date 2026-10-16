"""Few-shot 示例库 — 供 Intent Router 提升意图分类准确率。"""

# 每条示例: (用户问题, 应匹配的 skill_name, 简要理由)
ROUTING_EXAMPLES: list[dict] = [
    # ── RAG 知识库问答 ──
    {
        "question": "CCAR-21部对适航证申请有什么要求？",
        "skill": "rag",
        "reason": "明确引用法规编号，属于知识库条款查询"
    },
    {
        "question": "eVTOL 适航审定需要哪些试验项目？",
        "skill": "rag",
        "reason": "询问具体审定流程与试验要求"
    },
    {
        "question": "无人机飞行空域申请流程是什么？",
        "skill": "rag",
        "reason": "询问具体法规流程"
    },
    {
        "question": "限用类无人驾驶航空器系统安全性要求有哪些？",
        "skill": "rag",
        "reason": "针对特定法规文件的内容查询"
    },

    # ── 文档摘要 ──
    {
        "question": "帮我总结一下 CCAR-21 部的主要内容",
        "skill": "summary",
        "reason": "用户要求对整个文档进行摘要总结"
    },
    {
        "question": "概括一下无人机飞行管理暂行条例的核心要点",
        "skill": "summary",
        "reason": "要求概括、总结整篇法规"
    },
    {
        "question": "能否帮我对比一下新旧适航规定的区别？",
        "skill": "summary",
        "reason": "对比分析多个文档属于摘要类任务"
    },

    # ── 术语解释 ──
    {
        "question": "什么是 TC 型号合格证？",
        "skill": "definition",
        "reason": "询问专业术语定义"
    },
    {
        "question": "适航标准中的 MOC 是什么意思？",
        "skill": "definition",
        "reason": "缩写词/术语定义查询"
    },
    {
        "question": "请解释一下型号合格审定与生产许可审定的区别",
        "skill": "definition",
        "reason": "概念辨析属于术语解释"
    },

    # ── 合规性检查 ──
    {
        "question": "我们的无人机起飞重量 30kg，需要满足哪些适航要求？",
        "skill": "compliance_check",
        "reason": "用户给出具体参数，要求进行合规性判断"
    },
    {
        "question": "在城市上空飞行 eVTOL 需要哪些许可？是否合规？",
        "skill": "compliance_check",
        "reason": "合规性检查和许可要求查询"
    },
    {
        "question": "我们的产品是否满足 CCAR-91 的运行要求？",
        "skill": "compliance_check",
        "reason": "判断产品是否符合特定法规"
    },

    # ── 闲聊/超出范围 ──
    {
        "question": "你好，今天天气怎么样？",
        "skill": "chitchat",
        "reason": "非适航法规相关问题，属于闲聊"
    },
    {
        "question": "帮我写一首诗",
        "skill": "chitchat",
        "reason": "完全超出适航问答范围"
    },
    {
        "question": "你是谁？你能做什么？",
        "skill": "chitchat",
        "reason": "系统自我介绍，非知识库查询"
    },

    # ── 计算分析 ──
    {
        "question": "微型无人机的最大起飞重量限制是多少？",
        "skill": "calculation",
        "reason": "询问具体数值参数"
    },
    {
        "question": "不同类别无人机的限高分别是多少米？",
        "skill": "calculation",
        "reason": "涉及多个数值参数的提取和统计"
    },

    # ── 对比分析 ──
    {
        "question": "CCAR-21部和CCAR-91部在适航管理上有什么区别？",
        "skill": "comparison",
        "reason": "明确要求两个法规之间的对比"
    },
    {
        "question": "微型和轻型无人机在飞行限制上有什么不同？",
        "skill": "comparison",
        "reason": "不同类别之间的差异对比"
    },

    # ── 时间线梳理 ──
    {
        "question": "中国无人机管理法规的发展历程是怎样的？",
        "skill": "timeline",
        "reason": "询问发展历程，需要时间线梳理"
    },
    {
        "question": "无人驾驶航空器飞行管理暂行条例是什么时候颁布生效的？",
        "skill": "timeline",
        "reason": "询问具体时间节点"
    },

    # ── 导出报告 ──
    {
        "question": "帮我生成一份关于eVTOL适航审定的综合分析报告",
        "skill": "export",
        "reason": "用户明确要求生成分析报告"
    },
    {
        "question": "请汇总整理所有与低空经济相关的法规要求",
        "skill": "export",
        "reason": "要求汇总整理，适合导出报告"
    },
]


def format_few_shot_examples(examples: list[dict] | None = None) -> str:
    """将 few-shot 示例格式化为 Prompt 文本。"""
    if examples is None:
        examples = ROUTING_EXAMPLES

    lines = []
    for ex in examples:
        lines.append(
            f'问题: "{ex["question"]}"\n'
            f'选择: {{"skill": "{ex["skill"]}", "confidence": 0.95, '
            f'"reason": "{ex["reason"]}"}}'
        )
    return "\n\n".join(lines)
