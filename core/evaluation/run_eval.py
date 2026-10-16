"""评测基线数据生成脚本 — 运行 50 条测试问题并生成基线报告。

运行方式：
    cd 低空适航与规章问答 AI
    python -m core.evaluation.run_eval

输出：
    data/reports/eval_baseline.json — 包含所有评测维度的基线数据
"""

from __future__ import annotations

import json
import sys
import time
from datetime import datetime
from pathlib import Path

# 确保项目根目录在 sys.path
_project_root = Path(__file__).parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from config.settings import settings
from core.rag.llm_client import LLMClient
from core.vectorstore.retriever import HybridRetriever
from core.vectorstore.reranker import Reranker
from core.vectorstore.embedder import EmbeddingService
from core.vectorstore.chroma_store import ChromaStore
from core.rag.citation_checker import CitationChecker
from core.evaluation import RAGEvaluator, BatchEvaluator, EvaluationResult
from utils.logger import get_logger

log = get_logger(__name__)


# ── 50 条低空适航领域测试问题 ──────────────────────────────────────────
# 按难度和 Skill 类型分类，覆盖：法规查询、概念定义、流程说明、对比分析、合规检查
TEST_QUESTIONS: list[dict] = [
    # === 民用航空法 (1-15) ===
    {"question": "民用航空法所称的航空人员包括哪些？", "skill": "definition",
     "reference": "根据民用航空法第三十九条，航空人员是指从事民用航空活动的空勤人员和地面人员：（一）空勤人员，包括驾驶员、飞行机械人员、乘务员；（二）地面人员，包括民用航空器维修人员、空中交通管制员、飞行签派员、航空电台通信员。"},
    {"question": "航空人员取得执照前需要满足什么条件？", "skill": "rag",
     "reference": "应当接受专门训练，经考核合格，取得国务院民用航空主管部门颁发的执照。空勤人员和空中交通管制员还应当接受体格检查并取得体格检查合格证书。"},
    {"question": "机长在飞行前有什么职责？", "skill": "rag",
     "reference": "机长应当对民用航空器实施必要的检查；未经检查，不得起飞。机长发现民用航空器、机场、气象条件等不符合规定，不能保证飞行安全的，有权拒绝起飞。"},
    {"question": "设计民用航空器需要申请什么证书？", "skill": "rag",
     "reference": "设计民用航空器及其发动机、螺旋桨和民用航空器上设备，应当向国务院民用航空主管部门申请领取型号合格证书。经审查合格的，发给型号合格证书。"},
    {"question": "生产民用航空器需要什么许可？", "skill": "rag",
     "reference": "生产、维修民用航空器及其发动机、螺旋桨和民用航空器上设备，应当向国务院民用航空主管部门申请领取生产许可证书、维修许可证书。"},
    {"question": "民用航空器飞行必须持有什么证书？", "skill": "rag",
     "reference": "具有中华人民共和国国籍的民用航空器，应当持有国务院民用航空主管部门颁发的适航证书，方可飞行。"},
    {"question": "外国制造人的航空器首次进口中国需要什么手续？", "skill": "rag",
     "reference": "外国制造人生产的任何型号的民用航空器首次进口中国的，该外国制造人应当向国务院民用航空主管部门申请领取型号认可证书。"},
    {"question": "民用航空器所有人对适航有什么责任？", "skill": "rag",
     "reference": "民用航空器的所有人或者承租人应当按照适航证书规定的使用范围使用民用航空器，做好维修保养工作，保证民用航空器处于适航状态。"},
    {"question": "民用航空器机组由哪些人组成？", "skill": "definition",
     "reference": "民用航空器机组由机长和其他空勤人员组成。机长应当由具有独立驾驶该型号民用航空器的技术和经验的驾驶员担任。"},
    {"question": "飞行中机长对扰乱秩序的行为有什么权力？", "skill": "rag",
     "reference": "飞行中，对于任何破坏民用航空器、扰乱民用航空器内秩序、危害民用航空器所载人员或者财产安全的行为，机长有权采取必要的适当措施。"},
    {"question": "民用航空器优先权包含哪些债权？", "skill": "rag",
     "reference": "根据民用航空法第二十条，民用航空器优先权的债权人应当自援救或者保管维护工作终了之日起三个月内登记。第二十二条规定民用航空器优先权先于民用航空器抵押权受偿。第二十五条规定优先权自援救或者保管维护工作终了之日起满三个月时终止。"},
    {"question": "民用航空器优先权与抵押权的关系是什么？", "skill": "rag",
     "reference": "民用航空器优先权先于民用航空器抵押权受偿。"},
    {"question": "民用航空器融资租赁期间，出租人和承租人各享有什么权利？", "skill": "rag",
     "reference": "融资租赁期间，出租人依法享有民用航空器所有权，承租人依法享有民用航空器的占有、使用、收益权。"},
    {"question": "航空人员定期检查考核有什么规定？", "skill": "rag",
     "reference": "航空人员应当接受国务院民用航空主管部门定期或者不定期的检查和考核；经检查、考核合格的，方可继续担任其执照载明的工作。"},
    {"question": "空勤人员间断飞行超过规定时限后如何恢复？", "skill": "rag",
     "reference": "空勤人员间断飞行的时间超过规定时限的，应当经过检查和考核；乘务员以外的空勤人员还应当经过带飞。经检查、考核、带飞合格的，方可继续担任工作。"},

    # === 无人驾驶航空器飞行管理暂行条例 (16-35) ===
    {"question": "《无人驾驶航空器飞行管理暂行条例》所称无人驾驶航空器是指什么？", "skill": "definition",
     "reference": "无人驾驶航空器，是指没有机载驾驶员、自备动力系统的航空器。无人驾驶航空器按照性能指标分为微型、轻型、小型、中型和大型。"},
    {"question": "微型无人驾驶航空器的具体标准是什么？", "skill": "rag",
     "reference": "微型无人驾驶航空器，是指空机重量小于0.25千克，最大飞行真高不超过50米，最大平飞速度不超过40千米/小时，无线电发射设备符合微功率短距离技术要求的遥控驾驶航空器。"},
    {"question": "轻型无人驾驶航空器的定义标准有哪些？", "skill": "rag",
     "reference": "轻型无人驾驶航空器，是指空机重量不超过4千克且最大起飞重量不超过7千克，最大平飞速度不超过100千米/小时，具备空域保持能力和可靠被监视能力的遥控驾驶航空器。"},
    {"question": "小型、中型和大型无人驾驶航空器如何划分？", "skill": "rag",
     "reference": "根据暂行条例第三十八条：（三）小型无人驾驶航空器，是指空机重量不超过15千克或者最大起飞重量不超过25千克的无人驾驶航空器，但不包括微型、轻型。（四）中型无人驾驶航空器，是指最大起飞重量超过25千克不超过150千克的无人驾驶航空器。（五）大型无人驾驶航空器，是指最大起飞重量超过150千克的无人驾驶航空器。"},
    {"question": "哪些类型的无人机需要取得适航许可？", "skill": "rag",
     "reference": "从事中型、大型民用无人驾驶航空器系统的设计、生产、进口、飞行和维修活动，应当依法向国务院民用航空主管部门申请取得适航许可。微型、轻型、小型无需取得适航许可。"},
    {"question": "民用无人驾驶航空器所有者有什么登记义务？", "skill": "rag",
     "reference": "民用无人驾驶航空器所有者应当依法进行实名登记。涉及境外飞行的民用无人驾驶航空器，应当依法进行国籍登记。"},
    {"question": "取得无人机运营合格证需要哪些条件？", "skill": "rag",
     "reference": "根据暂行条例，使用小型、中型、大型民用无人驾驶航空器从事经营性飞行活动，应当取得运营合格证。使用最大起飞重量不超过150千克的农用无人驾驶航空器在农林牧渔区域从事作业飞行活动，无需取得运营合格证。"},
    {"question": "哪些情况下无需取得运营合格证？", "skill": "rag",
     "reference": "使用最大起飞重量不超过150千克的农用无人驾驶航空器在农林牧渔区域上方的适飞空域内从事农林牧渔作业飞行活动，无需取得运营合格证。"},
    {"question": "操控小型、中型、大型无人机需要什么执照条件？", "skill": "rag",
     "reference": "根据暂行条例第十六条，操控小型、中型、大型民用无人驾驶航空器飞行的人员应当具备：（一）具备完全民事行为能力；（二）接受安全操控培训，并经民用航空管理部门考核合格；（三）无可能影响操控行为的疾病病史，无吸毒行为记录；（四）近5年内无因危害国家安全、公共安全相关犯罪记录。"},
    {"question": "操控微型、轻型无人机的人员需要执照吗？", "skill": "rag",
     "reference": "操控微型、轻型民用无人驾驶航空器飞行的人员无需取得操控员执照，但应当熟练掌握有关机型操作方法，了解风险警示信息和有关管理制度。"},
    {"question": "无民事行为能力人可以操控什么类型的无人机？", "skill": "rag",
     "reference": "无民事行为能力人只能操控微型民用无人驾驶航空器飞行，限制民事行为能力人只能操控微型、轻型民用无人驾驶航空器飞行，且应当由完全民事行为能力人现场指导。"},
    {"question": "哪些区域上方的空域应当划设为管制空域？", "skill": "rag",
     "reference": "真高120米以上空域；机场周边区域；国界线、边境线一侧区域；军事禁区；核设施控制区域；发电厂、变电站等公共基础设施周边；射电天文台、雷达站等电磁保护设施周边。"},
    {"question": "什么是适飞空域？", "skill": "definition",
     "reference": "管制空域以外的空域为微型、轻型、小型无人驾驶航空器的适飞空域。"},
    {"question": "微型、轻型无人机在适飞空域飞行需要申请吗？", "skill": "rag",
     "reference": "微型、轻型无人驾驶航空器在适飞空域内飞行，无需提交飞行活动申请。"},
    {"question": "飞行活动申请应包含哪些内容？", "skill": "rag",
     "reference": "飞行活动申请应当包括飞行任务、飞行日期和起止时刻、飞行区域（航线）、飞行高度和飞行速度等。"},
    {"question": "哪些情形下可以划设临时管制空域？", "skill": "rag",
     "reference": "（一）重大活动期间；（二）重要目标防护期间；（三）突发事件应急处置期间；（四）军事活动需要；（五）其他需要划设的情形。"},
    {"question": "遇到紧急情况时，空中交通管理机构可以采取什么措施？", "skill": "rag",
     "reference": "空中交通管理机构可以对一定区域或一定范围的无人驾驶航空器发布紧急空域限制措施；操控人员收到指令后应立即停止飞行或按指令立即降落。"},
    {"question": "无人驾驶航空器飞行中可以投放物品吗？", "skill": "rag",
     "reference": "根据暂行条例第二十七条，无人驾驶航空器飞行过程中，不得违规携带或者投放物品。使用无人驾驶航空器进行物流配送或者喷洒作业等需要投放物品的飞行活动，应当按照国家有关规定在适飞空域内进行，并向空中交通管理机构报备。"},
    {"question": "使用民用无人机从事经营性飞行需要投保什么保险？", "skill": "rag",
     "reference": "使用民用无人驾驶航空器从事经营性飞行活动，以及使用小型、中型、大型民用无人驾驶航空器从事非经营性飞行活动，应当依法投保责任保险。"},
    {"question": "《无人驾驶航空器飞行管理暂行条例》何时施行？", "skill": "rag",
     "reference": "本条例自2024年1月1日起施行。"},

    # === 法律责任与处罚 (36-42) ===
    {"question": "未经实名登记飞行的无人机将受到什么处罚？", "skill": "rag",
     "reference": "由公安机关责令改正；拒不改正的，对个人处500元罚款，对单位处5000元罚款。"},
    {"question": "未取得运营合格证从事经营性飞行的处罚是什么？", "skill": "rag",
     "reference": "由民用航空管理部门责令停止经营，没收违法所得，并处违法所得1倍以上5倍以下的罚款；没有违法所得的，处1万元以上5万元以下的罚款。"},
    {"question": "未取得操控员执照操控无人机的处罚是什么？", "skill": "rag",
     "reference": "未取得操控员执照或者超出执照载明范围操控小型、中型、大型民用无人驾驶航空器的，由民用航空管理部门处5000元以上5万元以下的罚款。"},
    {"question": "未经批准在管制空域内飞行的处罚有多严重？", "skill": "rag",
     "reference": "对个人处2000元以上2万元以下罚款，对单位处10万元以上50万元以下罚款；情节严重的，个人处5万至20万罚款，单位处50万至200万罚款。在空中禁区飞行的，从重处罚。"},
    {"question": "利用无人机实施违反治安管理的行为如何处罚？", "skill": "rag",
     "reference": "由公安机关依照《中华人民共和国治安管理处罚法》处罚；构成犯罪的，依法追究刑事责任。"},
    {"question": "生产者未设置唯一产品识别码会受到什么处罚？", "skill": "rag",
     "reference": "由县级以上人民政府市场监督管理部门责令改正；拒不改正的，处1万元以上5万元以下的罚款。"},
    {"question": "危及航空安全的无人机可以被如何处置？", "skill": "rag",
     "reference": "根据暂行条例第二十九条，违反本条例规定，危及或者可能危及航空安全以及公共安全、国家安全的，有关部门按照职责分工可以采取必要技术措施和其他措施对无人驾驶航空器予以拦截、迫降、捕获。"},

    # === 民用航空产品合格审定规定 (43-47) ===
    {"question": "申请型号合格证书需要提交哪些材料？", "skill": "rag",
     "reference": "根据合格审定规定第21.21条，申请人提交的型号设计、试验报告和各种计算证明申请型号合格审定的民用航空产品符合适航规章和环境保护要求，且在预期使用规定的限制条件下运行时没有不安全的特征和特性。申请人应建立符合第十四章要求的设计保证系统。"},
    {"question": "生产许可证持有人有哪些持续责任？", "skill": "rag",
     "reference": "生产许可证持有人应当建立并保持质量系统，确保每件产品均符合经批准的设计，并处于安全可用状态。"},
    {"question": "适航证的类别有哪些？", "skill": "rag",
     "reference": "根据合格审定规定第七章，型号合格证持有人符合相关规定时可以获得适航证。适航证申请人应提交有关文件，局方进行适航检查，确认其符合经批准的型号设计并处于安全可用状态，即可颁发适航证。特殊类别航空器包括滑翔机、飞艇、甚轻型飞机等尚未颁布适航规章的航空器。"},
    {"question": "什么是补充型号合格证？", "skill": "definition",
     "reference": "根据合格审定规定第21.112条，型号合格证持有人对型号设计进行尚未达到应当申请新型号合格证的大改时，该证件持有人可以申请补充型号合格证。补充型号合格证和改装设计批准书持有人享有获得适航证、安装在经审定航空器上、获得生产许可证等权利。"},
    {"question": "零部件制造人批准书的作用是什么？", "skill": "rag",
     "reference": "根据合格审定规定第21.303至21.319条，零部件制造人批准书申请人或持有人应当建立质量系统，提交质量手册供局方评审，确保每一零部件符合经批准的设计并处于安全可用状态，按规定设置标牌或标记，保管相关文件。"},

    # === 限用类无人驾驶航空器系统 (48-50) ===
    {"question": "限用类无人驾驶航空器系统的适用范围是什么？", "skill": "rag",
     "reference": "根据限用类无人驾驶航空器系统适航标准，本标准适用于CCAR-92部第92.343条规定且符合以下限制的限用类民用无人驾驶航空器系统：（1）暂行条例规定的中型无人驾驶航空器系统；（2）暂行条例规定的最大起飞重量小于3180千克的大型无人驾驶航空器系统。面向不用于载人飞行、不进入融合空域飞行且不在地面人员密集区域飞行。"},
    {"question": "申请限用类特殊适航证需要满足什么条件？", "skill": "rag",
     "reference": "根据合格审定规定，适航证申请人应当提交有关文件，局方进行适航检查，确认其符合经批准的型号设计并处于安全可用状态。限用类无人驾驶航空器系统应当具备的功能包括：不飞出限制区域、系统防破解、不飞入禁飞区（电子围栏）、控制指令变化下不失控不超限、防误触功能和空中地面风险缓解能力。"},
    {"question": "限用类无人机的运行限制有哪些？", "skill": "rag",
     "reference": "根据限用类适航标准，限用类无人驾驶航空器系统面向不用于载人飞行、不进入融合空域飞行且不在地面人员密集区域飞行。应当具备标记和标牌、提供飞行手册，系统应具备防破解能力，无线电设备使用应遵守相关规定。运行限制包括使用限制和资料要求、运行场景限制等。"},
]


def build_rag_pipeline():
    """构建 RAG 流水线组件。"""
    # 初始化 Embedding
    embedder = EmbeddingService(
        api_key=settings.EMBEDDING_API_KEY,
        base_url=settings.EMBEDDING_BASE_URL,
        model_name=settings.EMBEDDING_MODEL_NAME,
    )

    # 初始化检索器
    chroma_store = ChromaStore(persist_dir=settings.CHROMA_DIR, embedding_service=embedder)
    reranker = None
    if settings.USE_RERANKER:
        reranker = Reranker(
            api_key=settings.EMBEDDING_API_KEY,
            base_url=settings.EMBEDDING_BASE_URL,
            model_name=settings.RERANKER_MODEL_NAME,
        )
    retriever = HybridRetriever(chroma_store, reranker=reranker)

    # 初始化 LLM 客户端
    main_llm = LLMClient.create_from_settings("main")
    judge_llm = LLMClient.create_from_settings("judge")

    return retriever, main_llm, judge_llm


def run_single_qa(retriever, main_llm, question: str) -> dict:
    """单次 RAG 问答：检索 + 生成。"""
    # 检索
    chunks = retriever.retrieve(question, top_k=settings.RAG_TOP_K)
    context = retriever.format_context(chunks)
    sources = list(set([c.metadata.get("source_file", "Unknown") for c in chunks]))

    # 构建 prompt
    from config.prompts import RAG_SYSTEM_PROMPT, format_rag_prompt
    prompt = format_rag_prompt(context, question, "")
    messages = [
        {"role": "system", "content": RAG_SYSTEM_PROMPT},
        {"role": "user", "content": prompt},
    ]

    # 生成回答
    result = main_llm.chat_with_usage(messages)
    answer = result["content"]
    citation_checker = CitationChecker()
    citation_result = citation_checker.check(answer, len(chunks))
    if not citation_result.is_valid:
        answer = citation_checker.strip_invalid_citations(answer, len(chunks))

    return {
        "question": question,
        "answer": answer,
        "context": context[:10000],  # 保留足够上下文用于评测（5 chunk × 1500+ 字符）
        "sources": sources,
        "citation_check": citation_result.__dict__,
        "tokens": {
            "prompt": result["prompt_tokens"],
            "completion": result["completion_tokens"],
            "total": result["total_tokens"],
        },
    }


def main():
    log.info("=" * 60)
    log.info("开始 RAG 评测基线数据生成")
    log.info("=" * 60)

    # 构建流水线
    retriever, main_llm, judge_llm = build_rag_pipeline()
    log.info("RAG 流水线初始化完成")

    # 构建评测器
    evaluator = RAGEvaluator(judge_llm=judge_llm)
    batch_evaluator = BatchEvaluator(evaluator)

    # 准备测试用例
    reports_dir = Path(settings.BASE_DIR) / "final_eval_outputs"
    reports_dir.mkdir(parents=True, exist_ok=True)
    checkpoint_path = reports_dir / "eval_final_checkpoint.json"
    output_path = reports_dir / "eval_final_report.json"

    test_cases = _load_generated_checkpoint(checkpoint_path)
    if test_cases:
        log.info(f"从 checkpoint 恢复已生成问答: {len(test_cases)} 条")
    else:
        test_cases = []
    log.info(f"共 {len(TEST_QUESTIONS)} 条测试问题")

    for idx, tq in enumerate(TEST_QUESTIONS[len(test_cases):], start=len(test_cases)):
        log.info(f"[{idx+1}/{len(TEST_QUESTIONS)}] 处理: {tq['question'][:50]}...")

        try:
            # RAG 问答
            qa_result = run_single_qa(retriever, main_llm, tq["question"])
            test_cases.append({
                "question": qa_result["question"],
                "answer": qa_result["answer"],
                "context": qa_result["context"],
                "reference": tq.get("reference", ""),
                "skill_name": tq.get("skill", ""),
                "sources": qa_result["sources"],
                "tokens": qa_result["tokens"],
            })
            _save_checkpoint(checkpoint_path, test_cases, phase="generation")
            log.info(f"  → 回答长度: {len(qa_result['answer'])} 字符, "
                     f"Token: {qa_result['tokens']['total']}")
        except Exception as e:
            log.error(f"  [FAIL] 问答失败: {e}")
            test_cases.append({
                "question": tq["question"],
                "answer": f"[生成失败: {e}]",
                "context": "",
                "reference": tq.get("reference", ""),
                "skill_name": tq.get("skill", ""),
                "sources": [],
                "tokens": {"prompt": 0, "completion": 0, "total": 0},
            })
            _save_checkpoint(checkpoint_path, test_cases, phase="generation")

        # 适当延迟避免 API 限流
        time.sleep(1)

    # 批量评测
    log.info("开始 LLM-as-Judge 评测...")
    existing_results = _load_judge_checkpoint(checkpoint_path)
    if existing_results:
        log.info(f"从 checkpoint 恢复已完成 Judge 评分: {len(existing_results)} 条")
    remaining_cases = test_cases[len(existing_results):]
    partial_eval = batch_evaluator.evaluate_batch(
        remaining_cases,
        on_progress=lambda idx, total, results=None: _save_checkpoint(
            checkpoint_path,
            test_cases,
            phase=f"judge:{len(existing_results) + idx}/{len(test_cases)}",
            eval_results=existing_results + (results or []),
        ),
    )
    all_results = existing_results + partial_eval["results"]
    eval_result = _build_eval_summary(all_results)

    # 统计幻觉率（hallucination_free 的补数）
    hallucination_rate = round(1.0 - eval_result["summary"]["avg_hallucination_free"], 4)

    # 构建完整报告
    timestamp = datetime.utcnow().isoformat()
    report = {
        "meta": {
            "generated_at": timestamp,
            "total_questions": len(TEST_QUESTIONS),
            "evaluation_model": judge_llm.model_name,
            "generation_model": main_llm.model_name,
        },
        "summary": {
            **eval_result["summary"],
            "hallucination_rate": hallucination_rate,  # 幻觉率 = 1 - 无幻觉率
        },
        "per_skill": _aggregate_by_skill(test_cases, eval_result["results"]),
        "test_cases": [
            {
                "question": tc["question"],
                "answer": tc["answer"][:3000],
                "reference": tc.get("reference", ""),
                "skill": tc.get("skill_name", ""),
                "sources": tc.get("sources", []),
                "citation_check": tc.get("citation_check", {}),
                "tokens": tc.get("tokens", {}),
                "scores": {
                    "faithfulness": r.faithfulness,
                    "relevance": r.relevance,
                    "citation_accuracy": r.citation_accuracy,
                    "hallucination_free": r.hallucination_free,
                    "recall": r.recall,
                    "overall": r.overall_score,
                },
            }
            for tc, r in zip(test_cases, eval_result["results"])
        ],
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    log.info("=" * 60)
    log.info(f"评测报告已保存: {output_path}")
    log.info(f"总题数: {report['meta']['total_questions']}")
    log.info(f"平均总分: {report['summary']['avg_overall']:.3f}")
    log.info(f"忠实度: {report['summary']['avg_faithfulness']:.3f}")
    log.info(f"相关性: {report['summary']['avg_relevance']:.3f}")
    log.info(f"引用准确率: {report['summary']['avg_citation_accuracy']:.3f}")
    log.info(f"无幻觉率: {report['summary']['avg_hallucination_free']:.3f}")
    log.info(f"幻觉率: {hallucination_rate:.3f}")
    log.info(f"召回率: {report['summary']['avg_recall']:.3f}")
    log.info("=" * 60)

    return report


def _save_checkpoint(path: Path, test_cases: list[dict], phase: str, eval_results: list | None = None) -> None:
    """长评测过程的轻量级断点文件。"""
    payload = {
        "phase": phase,
        "saved_at": datetime.utcnow().isoformat(),
        "completed_cases": len(test_cases),
        "test_cases": [
            {
                "question": tc.get("question", ""),
                "answer": tc.get("answer", ""),
                "context": tc.get("context", ""),
                "reference": tc.get("reference", ""),
                "skill": tc.get("skill_name", ""),
                "sources": tc.get("sources", []),
                "citation_check": tc.get("citation_check", {}),
                "tokens": tc.get("tokens", {}),
            }
            for tc in test_cases
        ],
    }
    if eval_results is not None:
        payload["judge_completed"] = len(eval_results)
        payload["judge_results"] = [
            {
                "question": r.question,
                "scores": {
                    "faithfulness": r.faithfulness,
                    "relevance": r.relevance,
                    "citation_accuracy": r.citation_accuracy,
                    "hallucination_free": r.hallucination_free,
                    "recall": r.recall,
                    "overall": r.overall_score,
                },
                "details": r.details,
            }
            for r in eval_results
        ]
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def _load_generated_checkpoint(path: Path) -> list[dict]:
    """若已有完整生成结果，避免重新消耗生成阶段 token。"""
    if not path.exists():
        return []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return []
    cases = payload.get("test_cases", [])
    if len(cases) > len(TEST_QUESTIONS):
        return []
    restored = []
    for item in cases:
        restored.append({
            "question": item.get("question", ""),
            "answer": item.get("answer", ""),
            "context": item.get("context", ""),
            "reference": item.get("reference", ""),
            "skill_name": item.get("skill", ""),
            "sources": item.get("sources", []),
            "citation_check": item.get("citation_check", {}),
            "tokens": item.get("tokens", {}),
        })
    return restored


def _load_judge_checkpoint(path: Path) -> list[EvaluationResult]:
    """恢复已经完成的 Judge 评分结果。"""
    if not path.exists():
        return []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return []
    restored = []
    for item in payload.get("judge_results", []):
        scores = item.get("scores", {})
        restored.append(EvaluationResult(
            question=item.get("question", ""),
            answer="",
            faithfulness=scores.get("faithfulness", 0),
            relevance=scores.get("relevance", 0),
            citation_accuracy=scores.get("citation_accuracy", 0),
            hallucination_free=scores.get("hallucination_free", 0),
            recall=scores.get("recall", 0),
            overall_score=scores.get("overall", 0),
            details=item.get("details", {}),
        ))
    return restored


def _build_eval_summary(results: list[EvaluationResult]) -> dict:
    """按 BatchEvaluator 输出格式聚合已有和新增评分。"""
    n = max(len(results), 1)
    summary = {
        "avg_faithfulness": sum(r.faithfulness for r in results) / n,
        "avg_relevance": sum(r.relevance for r in results) / n,
        "avg_citation_accuracy": sum(r.citation_accuracy for r in results) / n,
        "avg_hallucination_free": sum(r.hallucination_free for r in results) / n,
        "avg_recall": sum(r.recall for r in results) / n,
        "avg_overall": sum(r.overall_score for r in results) / n,
        "total": len(results),
    }
    return {"results": results, "summary": summary}


def _aggregate_by_skill(test_cases: list[dict], results: list) -> dict:
    """按 Skill 类型聚合评测指标。"""
    skill_groups: dict[str, list] = {}
    for tc, r in zip(test_cases, results):
        skill = tc.get("skill_name", "unknown")
        if skill not in skill_groups:
            skill_groups[skill] = []
        skill_groups[skill].append(r)

    skill_summary = {}
    for skill, group_results in skill_groups.items():
        n = len(group_results)
        skill_summary[skill] = {
            "count": n,
            "avg_faithfulness": round(sum(r.faithfulness for r in group_results) / n, 3),
            "avg_relevance": round(sum(r.relevance for r in group_results) / n, 3),
            "avg_hallucination_free": round(sum(r.hallucination_free for r in group_results) / n, 3),
            "avg_recall": round(sum(r.recall for r in group_results) / n, 3),
            "avg_overall": round(sum(r.overall_score for r in group_results) / n, 3),
        }
    return skill_summary


if __name__ == "__main__":
    main()
