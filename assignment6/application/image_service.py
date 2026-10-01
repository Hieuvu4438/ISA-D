"""Deterministic pixel descriptors, not learned semantic embeddings."""
from pathlib import Path

import numpy as np
from PIL import Image, ImageOps, UnidentifiedImageError

from application.query_service import ENCODER


class ImageService:
    encoder = ENCODER

    def encode(self, image_path):
        try:
            with Image.open(Path(image_path)) as original:
                if original.width * original.height > 20_000_000:
                    raise ValueError('image exceeds 20 million pixels')
                image = ImageOps.exif_transpose(original).convert('RGB')
                pixels = np.asarray(image.resize((128, 128)), dtype=float)
                histogram = np.concatenate([np.histogram(pixels[:, :, channel], bins=8, range=(0, 256))[0] for channel in range(3)]).astype(float)
                histogram /= np.linalg.norm(histogram)
                thumbnail = np.asarray(image.convert('L').resize((8, 8)), dtype=float).flatten() / 255
                norm = np.linalg.norm(thumbnail)
                if norm:
                    thumbnail /= norm
                # Each block contributes half of squared norm before final L2 normalization.
                descriptor = np.concatenate([histogram, thumbnail])
                descriptor /= np.linalg.norm(descriptor)
                return descriptor.tolist()
        except (OSError, UnidentifiedImageError, Image.DecompressionBombError) as exc:
            raise ValueError(f'cannot read image: {image_path}') from exc
