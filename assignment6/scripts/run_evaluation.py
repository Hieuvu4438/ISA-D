"""Evaluate frozen ground truth against the actual application pipeline."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import platform
import statistics
import sys
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from main import build_services


def evaluate(queries_path, output):
    queries_path, output = Path(queries_path), Path(output)
    ground_truth_bytes = queries_path.read_bytes()
    ground_truth = json.loads(ground_truth_bytes)
    ui = build_services(ROOT)
    rows = []
    for case in ground_truth['queries']:
        started = perf_counter()
        error, payload = None, {}
        try:
            if case['mode'] == 'text':
                payload = ui.search_text(case['query'])
            elif case['mode'] == 'voice':
                payload = ui.search_voice(case['query'])
            elif case['mode'] == 'image':
                if case.get('embedding_zero'):
                    payload = ui.search_service.search(ui.query_service.image_query([0.] * 88, raw_input='zero-vector robustness fixture'))
                else:
                    payload = ui.search_image(ROOT / case['image'])
            elif case['mode'] == 'multimodal':
                payload = ui.search_multimodal(case['query'], ROOT / case['image'])
            else:
                payload = ui.search_order(case['order_id'], case['customer_id'])
        except ValueError as exc:
            error = str(exc)
        elapsed = (perf_counter() - started) * 1000
        results = payload.get('results', [])
        ids = [p['product_id'] for p in results]
        if case.get('expected_error'):
            success = error is not None
        elif case.get('expected_empty'):
            success = error is None and not ids
        elif case.get('expected_zero_scores'):
            success = error is None and bool(results) and all(p['image_score'] == 0 for p in results)
        elif case.get('expected_empty_order'):
            success = error is None and payload.get('order') is None
        elif 'expected_order' in case:
            success = error is None and (payload.get('order') or {}).get('order_id') == case['expected_order']
        else:
            success = error is None and bool(ids) and ids[0] in case['relevant_ids']
        rows.append({'id': case['id'], 'group': case['group'], 'mode': case['mode'], 'input': {k: v for k, v in case.items() if k not in {'id', 'group', 'relevant_ids'}}, 'relevant_ids': case.get('relevant_ids', []), 'top_1_product_id': ids[0] if ids else None, 'top_k_ids': ids, 'scores': [p['final_score'] for p in results], 'actual_order_id': (payload.get('order') or {}).get('order_id'), 'success': success, 'processing_ms': elapsed, 'error': error, 'processing': payload.get('processing'), 'note': case.get('note', '')})
    def summarize(selected):
        total = len(selected)
        successful = sum(r['success'] for r in selected)
        return {'total': total, 'successful': successful, 'success_rate': successful / total if total else 0.0}
    primary = [r for r in rows if r['group'] == 'primary']
    primary_summary = summarize(primary)
    times = sorted(r['processing_ms'] for r in primary)
    metrics = {'total_queries': primary_summary['total'], 'successful_queries': primary_summary['successful'], 'success_rate': primary_summary['success_rate'], 'criterion': ground_truth['criterion'], 'by_mode': {mode: summarize([r for r in primary if r['mode'] == mode]) for mode in ['text', 'voice', 'image']}, 'groups': {group: summarize([r for r in rows if r['group'] == group]) for group in ['primary', 'extension', 'challenge', 'robustness']}, 'encoder': ui.image_service.encoder, 'ranking': 'weighted normalized text/image scores; ties product_id ascending; business weight 0', 'ground_truth_version': ground_truth['version'], 'ground_truth_sha256': hashlib.sha256(ground_truth_bytes).hexdigest(), 'timing_ms': {'mean': statistics.mean(times), 'p95': times[max(0, int(.95 * len(times)) - 1)], 'max': max(times), 'startup_excluded': True, 'samples': len(times)}, 'environment': {'python': platform.python_version(), 'platform': platform.platform()}, 'incorrect_examples': [r for r in rows if not r['success']]}
    output.mkdir(parents=True, exist_ok=True)
    (output / 'results.json').write_text(json.dumps(rows, indent=2, allow_nan=False) + '\n', encoding='utf-8')
    (output / 'metrics.json').write_text(json.dumps(metrics, indent=2, allow_nan=False) + '\n', encoding='utf-8')
    fields = ['id', 'group', 'mode', 'input', 'relevant_ids', 'top_1_product_id', 'top_k_ids', 'scores', 'actual_order_id', 'success', 'processing_ms', 'error', 'note']
    with (output / 'results.csv').open('w', encoding='utf-8', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction='ignore')
        writer.writeheader()
        for row in rows:
            writer.writerow({k: json.dumps(v, ensure_ascii=False) if isinstance(v, (list, dict)) else v for k, v in row.items()})
    return metrics


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--queries', type=Path, default=ROOT / 'evaluation/queries.json')
    parser.add_argument('--output', type=Path, default=ROOT / 'artifacts/evaluation')
    args = parser.parse_args()
    print(json.dumps(evaluate(args.queries, args.output), indent=2))
