# Thiết bị microphone giả cho E2E

`fake-microphone-44100.wav` là tín hiệu sine 440 Hz được tạo bằng code, stereo PCM16 44.100 Hz, dài 4 giây. Chỉ dùng với Chromium isolated `--use-file-for-fake-audio-capture` để kiểm tra quy trình mic và chuyển WAV PCM16 mono 16.000 Hz. Đây không phải giọng nói thật, không dùng đo nhận dạng Azure, không gửi vào dịch vụ trả phí.

`synthetic-upload-16000.wav` cũng là sine 440 Hz, mono PCM16 16.000 Hz, dài 1,5 giây. Dùng kiểm tra upload WAV hợp lệ và luồng transcript với provider stub được gắn nhãn trong tên test; không có nhận dạng lời nói thật.

Ảnh sản phẩm và ảnh query trong E2E lấy từ ảnh thật đã tải ở `data/`; không tạo ảnh synthetic.
