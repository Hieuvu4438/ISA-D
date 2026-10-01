"""Build the same 88-dimensional encoder for catalogue and query images."""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from application.image_service import ImageService
from data.product_repository import ProductRepository
from data.vector_index import source_fingerprint


def build(root=ROOT):
    root = Path(root)
    products = ProductRepository(root=root).all_products()
    encoder = ImageService()
    output = {'encoder': encoder.encoder, 'descriptor_blocks': {'rgb_histogram': 24, 'grayscale_thumbnail': 64, 'block_norms': 'L2; equal block weight then final L2'}, 'source_sha256': source_fingerprint(products, root), 'vectors': {str(p['product_id']): encoder.encode(root / p['image']) for p in products}}
    path = root / 'data/embeddings.json'
    serialized = json.dumps(output, indent=2, allow_nan=False) + '\n'
    if not path.exists() or path.read_text(encoding='utf-8') != serialized:
        path.write_text(serialized, encoding='utf-8')
        status = 'rebuilt'
    else:
        status = 'unchanged'
    return {'products': len(products), 'encoder': encoder.encoder, 'status': status}


if __name__ == '__main__':
    print(json.dumps(build(), indent=2))
