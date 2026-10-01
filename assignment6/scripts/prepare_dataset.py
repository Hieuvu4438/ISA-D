"""Create original synthetic illustrations. Existing data are preserved by default."""
import argparse
import json
from pathlib import Path
import sys

from PIL import Image, ImageDraw, ImageEnhance

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

PRODUCTS = [
    (1, 'Nike Running Shoes', 'Nike', 'shoes', 'black', 120, 10, 'Black running shoes for everyday training.'),
    (2, 'Adidas Running Shoes', 'Adidas', 'shoes', 'white', 100, 15, 'White running shoes for daily exercise.'),
    (3, 'Black Leather Bag', 'Local', 'bag', 'black', 80, 20, 'Black leather shoulder bag with a carry handle.'),
    (4, 'Blue Sports Shoes', 'Local', 'shoes', 'blue', 75, 12, 'Blue sports shoes with a flexible sole.'),
    (5, 'Nike Budget Running Shoes', 'Nike', 'shoes', 'black', 95, 8, 'Affordable black running shoes for training.'),
    (6, 'Red Canvas Shoes', 'Local', 'shoes', 'red', 60, 18, 'Red canvas shoes for casual walks.'),
    (7, 'White Casual Shoes', 'Local', 'shoes', 'white', 45, 20, 'White casual shoes for everyday wear.'),
    (8, 'Brown Leather Bag', 'Local', 'bag', 'brown', 90, 6, 'Brown leather shoulder bag with a carry handle.'),
    (9, 'Black Backpack', 'Local', 'bag', 'black', 55, 10, 'Black backpack with a front pocket.'),
    (10, 'Blue Cotton T-Shirt', 'Local', 'clothing', 'blue', 25, 30, 'Blue cotton shirt with short sleeves.'),
    (11, 'Black Sports Jacket', 'Local', 'clothing', 'black', 85, 7, 'Black sports jacket with long sleeves and a zipper.'),
    (12, 'Green Travel Backpack', 'Local', 'bag', 'green', 65, 0, 'Green travel backpack with a front pocket.'),
]
COLORS = {'black': '#20242a', 'white': '#e5e7e9', 'blue': '#2563c5', 'red': '#ce3848', 'brown': '#98613e', 'green': '#398051'}


def illustration(product):
    image = Image.new('RGB', (256, 256), '#f6f2eb')
    draw = ImageDraw.Draw(image)
    color = COLORS[product['color']]
    outline = '#4b5158'
    identifier = product['product_id']
    if product['category'] == 'shoes':
        shift = (identifier % 3) * 3
        draw.polygon([(39, 159), (54, 141), (72, 131), (87, 88 + shift), (121, 93), (148, 129), (207, 149), (224, 176), (212, 187), (46, 187)], fill=color, outline=outline, width=3)
        draw.rounded_rectangle((43, 179, 221, 195), radius=8, fill='#d0d1d4', outline=outline, width=2)
        for y in range(111, 142, 8):
            draw.line((93, y, 127, y + 7), fill='#989a9d', width=3)
        draw.line((149, 151, 178, 168), fill='#f3ce66' if identifier == 5 else '#8494a8', width=6)
    elif 'Backpack' in product['name']:
        draw.arc((100, 31, 156, 73), 180, 360, fill=outline, width=8)
        draw.rounded_rectangle((65, 54, 193, 219), radius=35, fill=color, outline=outline, width=4)
        draw.rounded_rectangle((82, 137, 176, 204), radius=16, fill=color, outline='#b2b5b9', width=3)
        draw.line((91, 153, 166, 153), fill='#b2b5b9', width=3)
    elif product['category'] == 'bag':
        draw.arc((81, 35, 177, 125), 180, 360, fill=color, width=13)
        draw.rounded_rectangle((51, 87, 207, 209), radius=15, fill=color, outline=outline, width=4)
        draw.line((60, 126, 198, 126), fill='#b2b5b9', width=3)
        draw.rounded_rectangle((111, 114, 146, 139), radius=3, fill='#d0b174')
    else:
        long = 'Jacket' in product['name']
        points = [(83, 55), (102, 47), (125, 66), (149, 47), (169, 55), (221, 172 if long else 94), (190, 187 if long else 122), (172, 113), (175, 217), (78, 217), (82, 113), (61, 187 if long else 122), (29, 172 if long else 94)]
        draw.polygon(points, fill=color, outline=outline, width=3)
        if long:
            draw.line((126, 66, 126, 214), fill='#b2b5b9', width=4)
    return image


def write_json(path, payload, force):
    if path.exists() and not force:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    return True


def prepare(root=ROOT, force=False):
    root = Path(root)
    products = [dict(zip(['product_id', 'name', 'brand', 'category', 'color', 'price', 'stock', 'description'], row), image=f'data/images/p{row[0]:03d}.png') for row in PRODUCTS]
    catalogue = root / 'data/products.json'
    if catalogue.exists() and not force:
        products = json.loads(catalogue.read_text(encoding='utf-8'))
    else:
        write_json(catalogue, products, force)
    for p in products:
        path = root / str(p['image'])
        if not path.exists() or force:
            path.parent.mkdir(parents=True, exist_ok=True)
            illustration(p).save(path)
    queries = root / 'data/queries'
    queries.mkdir(parents=True, exist_ok=True)
    for name, identifier in [('black_shoe_query', 1), ('blue_shoe_query', 4), ('brown_bag_query', 8)]:
        path = queries / f'{name}.png'
        if not path.exists() or force:
            source = next(p for p in products if p['product_id'] == identifier)
            with Image.open(root / str(source['image'])) as original:
                # Different pixels and resolution; fixed, mild transformation.
                transformed = ImageEnhance.Brightness(original).enhance(.97).resize((224, 224))
                transformed.save(path)
    if not (queries / 'corrupt.png').exists() or force:
        (queries / 'corrupt.png').write_bytes(b'Intentional invalid image fixture for robustness evaluation.\n')
    write_json(root / 'data/orders.json', [
        {'order_id': 'O001', 'customer_id': 'C001', 'date': '2026-09-29', 'status': 'Shipped', 'total': 150.0},
        {'order_id': 'O002', 'customer_id': 'C002', 'date': '2026-09-28', 'status': 'Delivered', 'total': 80.0},
        {'order_id': 'O003', 'customer_id': 'C001', 'date': '2026-10-01', 'status': 'Processing', 'total': 95.0},
    ], force)
    write_json(root / 'data/dataset_metadata.json', {'origin': 'Original synthetic Pillow illustrations authored for this assignment; not product photographs.', 'brands': 'Names are educational sample metadata; no brand affiliation implied.', 'generator': 'scripts/prepare_dataset.py', 'deterministic': True, 'currency': 'USD', 'products': len(products), 'query_transform': 'brightness 0.97, resize 224x224', 'corrupt_fixture': 'data/queries/corrupt.png intentionally invalid'}, force)
    return len(products)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--force', action='store_true', help='explicitly regenerate and overwrite dataset')
    args = parser.parse_args()
    print(f'Prepared {prepare(force=args.force)} products; existing outputs preserved unless --force.')
