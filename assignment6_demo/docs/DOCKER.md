# Hướng dẫn Docker cho Cortis Storefront & Backend

Tài liệu hướng dẫn triển khai hệ thống showroom Cortis bằng Docker và Docker Compose theo kiến trúc tách biệt container frontend và backend, tối ưu inference CPU và phục vụ static SPA qua Nginx reverse proxy.

---

## 1. Kiến trúc Container

Hệ thống được đóng gói thành 2 dịch vụ độc lập trong `docker-compose.yml`:

```
                           ┌───────────────────────────────┐
                           │      Trình duyệt người dùng   │
                           └───────────────┬───────────────┘
                                           │
                        ┌──────────────────┴──────────────────┐
                        │ http://localhost:5173 (Port 80 Nginx)│
                        ▼                                     │
           ┌───────────────────────────────┐                  │
           │       cortis-frontend         │                  │
           │  (Nginx Alpine: SPA + Proxy)  │                  │
           └───────┬───────────────────────┘                  │
                   │                                          │
       /api/*, /health/* (Internal Proxy)                     │
                   │                                          │
                   ▼                                          ▼
           ┌───────────────────────────────┐      Direct API Access:
           │        cortis-backend         │      http://localhost:8000
           │  (Python 3.12 Slim + PyTorch) │
           └───────────────┬───────────────┘
                           │
       Volumes: ./data, ./runtime, ./models
```

### cortis-backend
- **Base image**: `python:3.12-slim-bookworm`.
- **System packages**: `curl`, `ca-certificates`, `libasound2`, `libgomp1`, `ffmpeg`.
- **Inference**: PyTorch CPU (`torch==2.14.1+cpu`), `sentence-transformers==6.1.0`.
- **Cổng**: 8000 (nội bộ và map ra host `${BACKEND_PORT:-8000}`).
- **Healthcheck**: kiểm tra định kỳ `/health/live` bằng `curl`.

### cortis-frontend
- **Multi-stage build**:
  - Stage 1: `node:22-alpine` build React + TypeScript + Vite thành static assets trong `dist/`.
  - Stage 2: `nginx:alpine` phục vụ assets, kích hoạt Gzip, cache 1 năm cho assets bất biến, fallback SPA (`/index.html`) và reverse proxy toàn bộ `/api/` và `/health/` sang `backend:8000`.
- **Cổng**: 80 (map ra host `${FRONTEND_PORT:-5173}`).
- **Healthcheck**: kiểm tra định kỳ bằng `wget`.

---

## 2. Yêu cầu trước khi chạy

1. **Docker Engine**: Docker Desktop hoặc Docker Engine ≥ 24.0.
2. **Docker Compose**: Docker Compose V2 (`docker compose version`).
3. Dữ liệu catalog đã sẵn sàng trong thư mục `data/` (đã commit và mount vào container).
4. Models và vector index đã tải/build trong `runtime/` (hoặc build trực tiếp bằng scripts bên trong container).

---

## 3. Các bước triển khai

### Bước 1: Chuẩn bị biến môi trường (tùy chọn)

Sao chép `.env.example` thành `.env` nếu cần cấu hình nhận dạng giọng nói (Azure Speech, Groq) hoặc tùy chỉnh cổng:

```bash
cp .env.example .env
```

Nếu chạy mặc định với dữ liệu và index offline, không bắt buộc cần `.env`.

### Bước 2: Build Docker images

Từ thư mục gốc dự án:

```bash
docker compose build
```

Lệnh này sẽ:
1. Build `cortis-backend` sử dụng dependencies từ `backend/requirements.lock.txt`.
2. Build `cortis-frontend` qua `npm ci` và `npm run build`, đóng gói vào image Nginx nhẹ (~45MB).

### Bước 3: Khởi chạy hệ thống

```bash
docker compose up -d
```

Kiểm tra trạng thái container và healthcheck:

```bash
docker compose ps
```

Kết quả mong đợi: Cả `cortis-backend` và `cortis-frontend` đều ở trạng thái `running (healthy)`.

---

## 4. Kiểm tra và sử dụng

| Dịch vụ | URL | Mô tả |
|---|---|---|
| **Cortis Web Showroom** | `http://localhost:5173` | Giao diện cửa hàng đầy đủ tính năng |
| **Backend API Direct** | `http://localhost:8000` | FastAPI documentation và direct endpoints |
| **Health Check (Live)** | `http://localhost:5173/health/live` | Trạng thái sống của backend |
| **Health Check (Ready)**| `http://localhost:5173/health/ready` | Kiểm tra model và vector index |
| **API Metadata** | `http://localhost:5173/api/v1/meta` | Danh mục, capabilities, fingerprints |

### Kiểm tra bằng lệnh curl:

```bash
# Liveness
curl http://localhost:8000/health/live

# Readiness (kiểm tra catalog, model và index)
curl http://localhost:8000/health/ready

# Catalog sản phẩm qua frontend proxy
curl http://localhost:5173/api/v1/products?limit=5
```

---

## 5. Chạy scripts kiểm thử và index trong container

Nếu cần cập nhật index hoặc chạy test trong môi trường Docker:

```bash
# Kiểm tra tính toàn vẹn dataset catalog
docker compose exec backend python scripts/validate_dataset.py

# Xây dựng vector index offline (nếu có thay đổi catalog)
docker compose exec backend python scripts/build_index.py

# Cân chỉnh ngưỡng tương đồng (calibration)
docker compose exec backend python scripts/calibrate_thresholds.py

# Chạy toàn bộ backend unit/integration tests
docker compose exec backend pytest backend/tests
```

---

## 6. Quản lý container

```bash
# Xem logs real-time của cả hai dịch vụ
docker compose logs -f

# Xem riêng logs của backend
docker compose logs -f backend

# Dừng container
docker compose down

# Dừng container và xóa volume tạm
docker compose down -v
```

---

## 7. Xử lý sự cố thường gặp (Troubleshooting)

1. **Lỗi `port is already allocated`**:
   - Nếu cổng 8000 hoặc 5173 đã bị chiếm bởi tiến trình trên máy host, bạn có thể đổi cổng trong `.env`:
     ```env
     BACKEND_PORT=8001
     FRONTEND_PORT=5174
     ```
   - Sau đó chạy: `docker compose up -d`.

2. **Backend báo `MODEL_UNAVAILABLE` hoặc `INDEX_MISSING`**:
   - Đảm bảo thư mục `./runtime` trên host chứa `runtime/models` và `runtime/index`.
   - Vì `./runtime` được mount dạng volume, bạn có thể chạy `docker compose exec backend python scripts/download_models.py` và `docker compose exec backend python scripts/build_index.py` ngay bên trong container.
