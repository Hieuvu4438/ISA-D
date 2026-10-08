class RankingService:
    @staticmethod
    def rank(candidates, top_k):
        return sorted(candidates, key=lambda c: (-c["score"], c["product_id"]))[:top_k]
