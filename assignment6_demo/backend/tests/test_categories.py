from typing import get_args

import pytest

from app.data.product_repository import CATEGORIES
from app.domain import CategoryCode, Filters


def test_catalog_and_wire_category_codes_agree():
    assert set(CATEGORIES) == set(get_args(CategoryCode))
    assert len(CATEGORIES) == 12


@pytest.mark.parametrize("category", get_args(CategoryCode))
def test_each_declared_category_is_accepted_without_coercion(category):
    assert Filters(category=category).category == category


def test_unknown_category_is_rejected():
    with pytest.raises(ValueError):
        Filters(category="invented_category")
