"""Input adapters depend only on injected application services."""


class SearchUI:
    def __init__(self, query_service, speech_service, image_service, search_service, order_service):
        self.query_service = query_service
        self.speech_service = speech_service
        self.image_service = image_service
        self.search_service = search_service
        self.order_service = order_service

    def search_text(self, text, **kwargs):
        return self.search_service.search(self.query_service.text_query(text, **kwargs))

    def search_voice(self, transcript, **kwargs):
        text = self.speech_service.transcribe(transcript)
        query = self.query_service.voice_query(text, **kwargs)
        query['raw_input'] = transcript
        return self.search_service.search(query)

    def search_image(self, path, **kwargs):
        embedding = self.image_service.encode(path)
        return self.search_service.search(self.query_service.image_query(embedding, raw_input=str(path), **kwargs))

    def search_multimodal(self, text, path, text_weight=.5, **kwargs):
        embedding = self.image_service.encode(path)
        query = self.query_service.multimodal_query(text, embedding, raw_input=f'{text} | {path}', text_weight=text_weight, **kwargs)
        return self.search_service.search(query)

    def search_order(self, order_id, customer_id):
        return self.order_service.find_order(order_id, customer_id)

    def view_product(self, product_id):
        return self.search_service.view_product(product_id)
