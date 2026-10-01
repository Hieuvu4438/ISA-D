"""Final score, deterministic ordering, and top-k belong only here."""
from copy import deepcopy
import math


class RankingService:
    def rank(self, candidates, query):
        weights = query['weights']
        if set(weights) != {'text', 'image'} or any(isinstance(w, bool) or not isinstance(w, (int, float)) or not math.isfinite(w) or w < 0 for w in weights.values()) or not math.isclose(sum(weights.values()), 1):
            raise ValueError('ranking weights must be nonnegative and sum to one')
        results = deepcopy(candidates)
        for result in results:
            result['final_score'] = weights['text'] * result['text_score'] + weights['image'] * result['image_score']
        results.sort(key=lambda p: (-p['final_score'], p['product_id']))
        return [dict(result, rank=i + 1) for i, result in enumerate(results[:query['top_k']])]
