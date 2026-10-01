"""Human readable CLI output without data access or ranking logic."""

import json


class SearchResultView:
    def render(self, payload):
        if isinstance(payload, list):
            return "\n\n".join(self.render(item) for item in payload)
        if "results" not in payload:
            return json.dumps(payload, indent=2, ensure_ascii=False)
        query, processing = payload["query"], payload["processing"]
        lines = [f"=== {query['type'].upper()} SEARCH ===", f"Input: {query['raw_input']}"]
        if processing["simulated_stt"]:
            lines.append("Voice mode: simulated speech-to-text (transcript supplied)")
        lines.extend(
            [
                f"Normalized: {query['query']} | tokens={query['tokens']}",
                f"Filters: {query['filters']}",
                f"Candidates: {processing['candidates_before_filter']} -> {processing['candidates_after_filter']} | weights={query['weights']}",
            ]
        )
        if processing["encoder"]:
            lines.append(f"Pixel encoder: {processing['encoder']}")
        for p in payload["results"]:
            lines.append(
                f"{p['rank']}. [{p['product_id']:02d}] {p['name']} | ${p['price']:.2f} | stock={p['stock']} | text={p['text_score']:.6f} image={p['image_score']:.6f} final={p['final_score']:.6f}"
            )
        if not payload["results"]:
            lines.append("No matching products.")
        return "\n".join(lines)
