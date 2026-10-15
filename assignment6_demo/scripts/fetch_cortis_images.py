import urllib.request
import json
import os
import hashlib
from pathlib import Path

dest_dir = Path('frontend/public/images/cortis')
dest_dir.mkdir(parents=True, exist_ok=True)

items = [
    {
        'id': 'cortis-group-tiktok',
        'title': 'CORTIS - TikTok Awards Korea',
        'filename': 'cortis_group_tiktok.jpg',
        'url': 'https://upload.wikimedia.org/wikipedia/commons/6/65/Cortis_at_TikTok_Awards_Korea.jpg',
        'author': 'TikTok Awards Korea / Wikimedia Commons contributors',
        'license': 'CC BY 3.0 / CC BY-SA 4.0',
        'source_page': 'https://commons.wikimedia.org/wiki/File:Cortis_at_TikTok_Awards_Korea.jpg',
        'description': 'Đội hình 5 thành viên CORTIS (James, Seonghyeon, Juhoon, Keonho, Martin) trong phong cách streetwear thanh lịch hiện đại.'
    },
    {
        'id': 'cortis-group-gda',
        'title': 'CORTIS - 40th Golden Disc Awards',
        'filename': 'cortis_group_gda.jpg',
        'url': 'https://upload.wikimedia.org/wikipedia/commons/2/28/Cortis_at_40th_Golden_Disc_Awards%2C_2026.jpg',
        'author': 'Golden Disc Awards / Wikimedia Commons contributors',
        'license': 'CC BY-SA 4.0',
        'source_page': 'https://commons.wikimedia.org/wiki/File:Cortis_at_40th_Golden_Disc_Awards,_2026.jpg',
        'description': 'CORTIS nhận giải Tân binh của năm (Rookie Artist of the Year) tại giải thưởng Golden Disc Awards lần thứ 40.'
    },
    {
        'id': 'cortis-martin',
        'title': 'Martin - Leader & Vocalist',
        'filename': 'cortis_martin.jpg',
        'url': 'https://upload.wikimedia.org/wikipedia/commons/8/80/Cortis_Martin_at_TikTok_Awards_Korea.jpg',
        'author': 'Wikimedia Commons contributors',
        'license': 'CC BY 3.0',
        'source_page': 'https://commons.wikimedia.org/wiki/File:Cortis_Martin_at_TikTok_Awards_Korea.jpg',
        'description': 'Martin (trưởng nhóm) với áo blazer phối streetwear sắc sảo.'
    },
    {
        'id': 'cortis-james',
        'title': 'James - Main Dancer & Rapper',
        'filename': 'cortis_james.png',
        'url': 'https://upload.wikimedia.org/wikipedia/commons/8/8f/JAMES_of_CORTIS_at_Airport_in_20251001.png',
        'author': 'Newsen / Wikimedia Commons contributors',
        'license': 'CC BY 3.0',
        'source_page': 'https://commons.wikimedia.org/wiki/File:JAMES_of_CORTIS_at_Airport_in_20251001.png',
        'description': 'James (vũ công chính & rapper) diện trang phục airport street style cá tính.'
    },
    {
        'id': 'cortis-juhoon',
        'title': 'Juhoon - Creator & Visual',
        'filename': 'cortis_juhoon.png',
        'url': 'https://upload.wikimedia.org/wikipedia/commons/3/30/JUHOON_of_CORTIS_at_Cultwo_Show_in_20250914.png',
        'author': 'SBS Radio / Wikimedia Commons contributors',
        'license': 'CC BY 3.0',
        'source_page': 'https://commons.wikimedia.org/wiki/File:JUHOON_of_CORTIS_at_Cultwo_Show_in_20250914.png',
        'description': 'Juhoon trẻ trung trong trang phục thu đông cao cấp thanh thoát.'
    },
    {
        'id': 'cortis-seonghyeon',
        'title': 'Seonghyeon - Creator & Performer',
        'filename': 'cortis_seonghyeon.png',
        'url': 'https://upload.wikimedia.org/wikipedia/commons/9/97/SEONGHYEON_of_CORTIS_at_Cultwo_Show_in_20250914.png',
        'author': 'SBS Radio / Wikimedia Commons contributors',
        'license': 'CC BY 3.0',
        'source_page': 'https://commons.wikimedia.org/wiki/File:SEONGHYEON_of_CORTIS_at_Cultwo_Show_in_20250914.png',
        'description': 'Seonghyeon với phong cách phối màu avant-garde hiện đại.'
    },
    {
        'id': 'cortis-keonho',
        'title': 'Keonho - Vocalist',
        'filename': 'cortis_keonho.jpg',
        'url': 'https://upload.wikimedia.org/wikipedia/commons/9/95/Cortis_Keonho_at_TikTok_Awards_Korea.jpg',
        'author': 'Wikimedia Commons contributors',
        'license': 'CC BY 3.0',
        'source_page': 'https://commons.wikimedia.org/wiki/File:Cortis_Keonho_at_TikTok_Awards_Korea.jpg',
        'description': 'Keonho mang điểm nhấn phụ kiện và giày sneaker tinh xảo.'
    }
]

manifest = []
for item in items:
    out_file = dest_dir / item['filename']
    print(f"Downloading {item['title']}...")
    req = urllib.request.Request(
        item['url'],
        headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) CortisStorefront/1.0 (contact: admin@cortis.demo)'}
    )
    try:
        content = urllib.request.urlopen(req).read()
        out_file.write_bytes(content)
        sha256 = hashlib.sha256(content).hexdigest()
        manifest.append({
            **item,
            'local_path': f"/images/cortis/{item['filename']}",
            'size_bytes': len(content),
            'sha256': sha256
        })
        print(f"Saved {out_file} ({len(content)} bytes)")
    except Exception as e:
        print(f"Error downloading {item['url']}: {e}")

manifest_path = dest_dir / 'manifest.json'
manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding='utf-8')
print("Manifest written successfully to", manifest_path)
