"""Rebuild the human-readable credits from the validated local manifest."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def cell(value):
    return str(value).replace("|", "\\|").replace("\n", " ")


def main():
    products = json.loads((ROOT / "data/products.json").read_text(encoding="utf-8"))
    assets = json.loads((ROOT / "data/image_sources.json").read_text(encoding="utf-8"))["assets"]
    sources = {a["product_id"]: a for a in assets}
    lines = [
        "# Nguồn ảnh sản phẩm", "",
        f"Catalog có {len(products)} ảnh chụp thật tải từ Wikimedia Commons. Nguồn, tác giả, giấy phép, "
        "checksum và ngày tải được lưu trong [image_sources.json](../data/image_sources.json). "
        "Ảnh được phục vụ từ file local; giá, tồn kho và đơn hàng là dữ liệu giả định cho demo. "
        "Không sử dụng ảnh sản phẩm tạo bằng AI.", "",
        "| Sản phẩm | Nguồn ảnh | Tác giả | Giấy phép | File local |",
        "| --- | --- | --- | --- | --- |",
    ]
    for product in products:
        source = sources[product["product_id"]]
        lines.append(
            f"| {cell(product['product_id'] + ' ' + product['name'])} "
            f"| [Nguồn]({source['source_page']}) | {cell(source['author'])} "
            f"| [{cell(source['license'])}]({source['license_url']}) "
            f"| [Ảnh](../{source['local_path']}) |"
        )
    lines.extend([
        "", "Dùng thumbnail Wikimedia khi nguồn có sẵn; không chỉnh sửa hình ảnh local. "
        "P006 là ảnh chụp thật đã có xử lý màu chọn lọc tại nguồn. "
        "Các ảnh CC BY-SA tiếp tục theo giấy phép tương ứng khi phân phối lại.", "",
        "Kiểm tra trực quan: [12 ảnh gốc](assets/asset-contact-sheet.jpg), "
        "[ảnh mở rộng 1](assets/expansion-contact-1.jpg), "
        "[ảnh mở rộng 2](assets/expansion-contact-2.jpg), "
        "[ảnh mở rộng 3](assets/expansion-contact-3.jpg). "
        "Contact sheet chỉ ghép các ảnh đã tải để duyệt, không phải ảnh sản phẩm tạo mới.", "",
    ])
    (ROOT / "docs/IMAGE_CREDITS.md").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
