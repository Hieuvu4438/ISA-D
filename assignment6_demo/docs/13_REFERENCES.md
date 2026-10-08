# Nguồn và giới hạn xác minh

Tra cứu ngày 08/10/2026, ưu tiên nguồn chính thức. Nguồn dưới đây hỗ trợ quyết định kỹ thuật; không thay thế test website/model trên máy demo.

| Nguồn | Dùng để xác minh |
| --- | --- |
| [CONTEXT.md](CONTEXT.md) | Analysis FR/UC, kiến trúc, các phiên bản CLIP/88D, prototype |
| Assignment 06 PDF và bản trích nội dung trong repo `assignment6` (chỉ đọc đối chiếu) | Danh mục use cases, ba lớp, sequence voice, yêu cầu demo từng input/processing/results/score; không đưa các artifact cũ vào evidence website mới |
| [Multilingual CLIP model card](https://huggingface.co/sentence-transformers/clip-ViT-B-32-multilingual-v1) | Text DistilBERT, tiếng Việt trong languages, 512D, pair với original CLIP image |
| [CLIP image model card](https://huggingface.co/sentence-transformers/clip-ViT-B-32) | Load ảnh bằng SentenceTransformer, embedding cho ảnh |
| [Sentence Transformers pretrained models](https://www.sbert.net/docs/sentence_transformer/pretrained_models.html) | Loading model conventions; implementation phải dùng API tương ứng bản được lock |
| [HF metadata API text](https://huggingface.co/api/models/sentence-transformers/clip-ViT-B-32-multilingual-v1) và [image](https://huggingface.co/api/models/sentence-transformers/clip-ViT-B-32) | Commit revisions ghi trong 05 đã đọc trực tiếp, không đo latency/relevance |
| [Azure Speech quickstart Python](https://learn.microsoft.com/en-us/azure/ai-services/speech-service/get-started-speech-to-text?pivots=programming-language-python) | SpeechConfig subscription/region, recognition results; credentials chỉ backend |
| [Azure SDK input streams](https://learn.microsoft.com/en-us/azure/ai-services/speech-service/how-to-use-audio-input-streams) | Raw PCM signed16 little-endian, mono, sample rate, header-free stream |
| [Azure SpeechRecognizer Python](https://learn.microsoft.com/en-us/python/api/azure-cognitiveservices-speech/azure.cognitiveservices.speech.speechrecognizer) | Single-shot recognition kết thúc bởi silence, không phải ghi âm browser |
| [Azure regions](https://learn.microsoft.com/en-us/azure/ai-services/speech-service/regions) | Region canonical `southeastasia`, chưa xác minh key/resource người dùng |
| [Azure languages](https://learn.microsoft.com/en-us/azure/ai-services/speech-service/language-support) | STT `vi-VN`; không suy CLIP hiểu tiếng Việt từ capability Azure |
| [MDN getUserMedia](https://developer.mozilla.org/en-US/docs/Web/API/MediaDevices/getUserMedia) | Mic permissions và secure context; browser flow phải test localhost thực |
| [FastAPI file uploads](https://fastapi.tiangolo.com/tutorial/request-files/) | Multipart, UploadFile, không trộn JSON body thường với multipart |
| [Visual Paradigm class diagram](https://www.visual-paradigm.com/guide/uml-unified-modeling-language/what-is-class-diagram/) và [sequence diagram](https://www.visual-paradigm.com/guide/uml-unified-modeling-language/what-is-sequence-diagram/) | UML notation; Mermaid chỉ là hướng dẫn tái dựng |

Nguồn ảnh từng asset nằm tại [image_sources.json](../data/image_sources.json), [bảng credit](IMAGE_CREDITS.md). Không coi mọi file Wikimedia đều là photograph; đã kiểm tra visual những file tải trong bộ seed. Không tải/gọi Azure với khóa thật để kiểm thử trong đợt đặc tả.

Các quyết định đề xuất của bộ đặc tả (stack, giá VND, fixed C001, threshold targets, recording15s, upload limits, performance≤5s) là thiết kế của demo, không phải “quy chuẩn bắt buộc” của nguồn tham khảo. Chúng phải được nghiệm thu theo 10 và ghi giới hạn nếu evidence chưa đạt.
