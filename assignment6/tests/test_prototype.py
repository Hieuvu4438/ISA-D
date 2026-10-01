"""Acceptance and boundary tests written before the prototype implementation."""
from copy import deepcopy
import importlib
import json
from pathlib import Path
import subprocess
import sys

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


@pytest.fixture
def ui():
    return importlib.import_module('main').build_services(ROOT)


@pytest.fixture
def qs():
    return importlib.import_module('application.query_service').QueryService()


def test_text_normalizes_alias_punctuation_and_unique_terms(qs):
    q = qs.text_query('  FIND black, BLACK shoe! ')
    assert q['tokens'] == ['black', 'shoes']
    assert q['filters']['category'] == 'shoes'


@pytest.mark.parametrize('value', ['', '   ', None, 32, 'a' * 2001])
def test_text_rejects_invalid_input(qs, value):
    with pytest.raises(ValueError):
        qs.text_query(value)


@pytest.mark.parametrize('value', [0, -1, True, 101, 2.5])
def test_top_k_boundary(qs, value):
    with pytest.raises(ValueError):
        qs.text_query('shoes', top_k=value)


def test_price_strict_vs_inclusive(qs):
    strict = qs.text_query('shoes under 100 dollars')
    inclusive = qs.text_query('shoes at most 100 dollars')
    assert strict['filters']['max_price_exclusive'] == 100
    assert inclusive['filters']['max_price_inclusive'] == 100


@pytest.mark.parametrize('embedding', [[0] * 87, [float('nan')] * 88, [float('inf')] * 88, 'wrong', [[1]*88]])
def test_embedding_validation(qs, embedding):
    with pytest.raises(ValueError):
        qs.image_query(embedding)


@pytest.mark.parametrize('weight', [-0.1, 1.1, float('nan'), True])
def test_fusion_weight_validation(qs, weight):
    with pytest.raises(ValueError):
        qs.multimodal_query('shoes', [1] * 88, text_weight=weight)


def test_dataset_and_repository_are_immutable(ui):
    products = ui.search_service.repository.all_products()
    assert len(products) == 12
    assert len({p['product_id'] for p in products}) == 12
    assert all((ROOT / p['image']).is_file() for p in products)
    original = deepcopy(products)
    products[0]['name'] = 'tampered'
    ui.search_text('black shoes')
    assert ui.search_service.repository.all_products() == original


def test_text_filters_relevance_and_no_matches(ui):
    result = ui.search_text('find Nike shoes under 100 dollars')
    assert result['results'][0]['product_id'] == 5
    assert all(p['price'] < 100 and p['category'] == 'shoes' for p in result['results'])
    assert ui.search_text('unobtainium')['results'] == []


def test_filter_only_and_inclusive_price(ui):
    strict = ui.search_text('under 100', category='shoes')
    inclusive = ui.search_text('at most 100', category='shoes')
    assert all(r['price'] < 100 for r in strict['results'])
    assert 2 in [r['product_id'] for r in inclusive['results']]


def test_voice_calls_speech_adapter_and_matches_text(ui, monkeypatch):
    calls = []
    monkeypatch.setattr(ui.speech_service, 'transcribe', lambda s: calls.append(s) or s)
    voice = ui.search_voice('black running shoes')
    text = ui.search_text('black running shoes')
    assert calls == ['black running shoes']
    assert voice['query']['type'] == 'voice'
    assert voice['results'] == text['results']


def test_speech_rejects_real_audio_and_empty():
    speech = importlib.import_module('application.speech_service').SpeechService()
    for value in [b'audio', '', None]:
        with pytest.raises(ValueError):
            speech.transcribe(value)


def test_pixel_encoder_is_path_independent_and_dimension_88(ui, tmp_path):
    from PIL import Image
    source = ROOT / 'data/images/p001.png'
    copied = tmp_path / 'unrelated_name.png'
    copied.write_bytes(source.read_bytes())
    encoded = ui.image_service.encode(source)
    assert len(encoded) == 88
    assert np.linalg.norm(encoded) == pytest.approx(1)
    assert encoded == ui.image_service.encode(copied)
    Image.new('RGB', (128, 128), 'red').save(copied)
    assert encoded != ui.image_service.encode(copied)


def test_image_missing_and_corrupt_are_clear_errors(ui, tmp_path):
    invalid = tmp_path / 'broken.png'
    invalid.write_text('not an image')
    for path in [invalid, tmp_path / 'missing.png']:
        with pytest.raises(ValueError):
            ui.search_image(path)


def test_cosine_boundaries():
    cosine = importlib.import_module('data.vector_index').cosine_similarity
    assert cosine([1, 0], [1, 0]) == pytest.approx(1)
    assert cosine([1, 0], [0, 1]) == pytest.approx(0)
    assert cosine([0, 0], [1, 1]) == 0
    assert cosine([-1, 0], [1, 0]) == -1
    for a, b in [([1], [1, 2]), ([float('nan')], [1])]:
        with pytest.raises(ValueError):
            cosine(a, b)


def test_image_exact_and_transformed_samples(ui):
    exact = ui.search_image(ROOT / 'data/images/p001.png')
    query = ui.search_image(ROOT / 'data/queries/black_shoe_query.png')
    assert exact['results'][0]['product_id'] == 1
    assert exact['results'][0]['image_score'] == pytest.approx(1)
    assert query['results'][0]['product_id'] in {1, 5}


def test_retrieval_separate_from_ranking_and_tie_break(ui, qs):
    q = qs.text_query('black shoes', top_k=1)
    candidates = ui.search_service.retrieve_candidates(q)
    assert len(candidates) > 1
    assert 'rank' not in candidates[0]
    ranked = ui.search_service.ranking.rank(list(reversed(candidates)), q)
    assert len(ranked) == 1
    assert ranked[0]['product_id'] == 1


def test_fusion_has_union_candidates_and_component_formula(ui, qs):
    image = ui.image_service.encode(ROOT / 'data/images/p003.png')
    q = qs.multimodal_query('blue', image, top_k=12)
    candidates = ui.search_service.retrieve_candidates(q)
    assert {3, 4} <= {c['product_id'] for c in candidates}
    result = ui.search_service.search(q)
    for item in result['results']:
        assert item['final_score'] == pytest.approx(.5 * item['text_score'] + .5 * item['image_score'])
    text_only = ui.search_service.search(qs.multimodal_query('blue', image, text_weight=1))
    image_only = ui.search_service.search(qs.multimodal_query('blue', image, text_weight=0))
    assert text_only['results'][0]['product_id'] == 4
    assert image_only['results'][0]['product_id'] == 3


def test_order_customer_scope(ui):
    assert ui.search_order('O001', 'C001')['order']['status'] == 'Shipped'
    assert ui.search_order('O002', 'C001')['order'] is None
    assert ui.search_order('O999', 'C001')['order'] is None
    with pytest.raises(ValueError):
        ui.search_order('O001', '')


def test_product_detail(ui):
    assert ui.view_product(1)['product']['name'] == 'Nike Running Shoes'
    assert ui.view_product(999)['product'] is None


@pytest.mark.parametrize('args', [[], ['--mode', 'text', '--query', 'black shoes'], ['--mode', 'voice', '--query', 'find running shoes'], ['--mode', 'image', '--image', 'data/queries/black_shoe_query.png'], ['--mode', 'multimodal', '--query', 'black shoes', '--image', 'data/queries/black_shoe_query.png'], ['--mode', 'order', '--order-id', 'O001', '--customer-id', 'C001']])
def test_cli_end_to_end_json(args, tmp_path):
    output = tmp_path / 'result.json'
    completed = subprocess.run([sys.executable, str(ROOT / 'main.py'), *args, '--json', '--output', str(output)], cwd=tmp_path, capture_output=True, text=True)
    assert completed.returncode == 0, completed.stderr
    payload = json.loads(completed.stdout)
    assert payload == json.loads(output.read_text(encoding='utf-8'))
    if isinstance(payload, list):
        assert {'text', 'voice', 'image'} <= {r.get('query', {}).get('type') for r in payload}
    elif 'results' in payload:
        assert {'query', 'processing', 'results'} <= payload.keys()
        assert payload['results'][0]['final_score'] >= 0


def test_cli_invalid_input_without_traceback():
    completed = subprocess.run([sys.executable, str(ROOT / 'main.py'), '--mode', 'text', '--query', ''], capture_output=True, text=True)
    assert completed.returncode != 0
    assert 'Traceback' not in completed.stderr


def test_architecture_import_boundaries():
    import ast
    forbidden = {'presentation': {'data'}, 'data': {'application', 'presentation'}, 'application': {'presentation'}}
    for package, blocked in forbidden.items():
        files = list((ROOT / package).glob('*.py'))
        assert files
        for file in files:
            tree = ast.parse(file.read_text(encoding='utf-8'))
            imports = [node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)]
            imports += [alias.name for node in ast.walk(tree) if isinstance(node, ast.Import) for alias in node.names]
            assert not {name.split('.')[0] for name in imports if name} & blocked
