from unittest.mock import Mock
from urllib.parse import parse_qs, urlparse

from core.chunker.chunk_models import DocumentChunk
from core.rag.evidence import source_path, original_pages, evidence_records, evidence_context, original_url
from core.skills.utils import validate_citations
from core.router.intent_router import KEYWORD_RULES
import re

SOURCE = 'CAAC-CCAR-92-民用无人驾驶航空器运行安全管理规则-2024.pdf'


def test_source_paths_cannot_escape_public_documents():
    assert source_path('../.env') is None
    assert source_path('..\\.env') is None
    assert source_path('/etc/passwd') is None
    assert original_url('invented.pdf') is None


def test_original_page_and_chapter_headings_are_from_pdf():
    chunk = DocumentChunk(original_pages(SOURCE)[1], {'source_file': SOURCE})
    refs = evidence_records([chunk])
    assert refs[0]['page'] == 2
    context = evidence_context(refs)
    assert re.search(r'E\s*章\s*空中交通管理', context)
    assert re.search(r'F\s*章\s*运行管理', context)
    query = parse_qs(urlparse(original_url(SOURCE, 2)).query)
    assert query == {'source': [SOURCE], 'page': ['2']}


def test_semantic_edit_and_reference_mapping_survive_check():
    chunk = DocumentChunk(original_pages(SOURCE)[1], {'source_file': SOURCE})
    llm = Mock()
    llm.chat.return_value = '室内飞行不适用本规则E章和F章要求。[1]'
    answer, result = validate_citations('E章是运行管理，F章是人员管理。', [chunk], llm, '室内飞行如何适用？')
    assert '人员管理' not in answer
    assert result.is_valid
    assert result.details['references'][0]['page'] == 2
    assert '空中交通管理' in llm.chat.call_args.args[0][1]['content']


def test_uncited_answer_is_explicitly_flagged():
    answer, result = validate_citations('无法确认。', [DocumentChunk('证据', {'source_file': 'unknown.txt'})])
    assert not result.is_valid
    assert '未通过引用编号检查' in answer


def test_scope_question_routes_to_rag_before_definition():
    question = 'CCAR-92 的适用范围是什么？请给出原文依据。'
    first = next(rule['skill'] for rule in KEYWORD_RULES if any(re.search(p, question, re.I) for p in rule['patterns']))
    assert first == 'rag'
