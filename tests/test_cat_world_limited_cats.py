import os
import unittest

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session


os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")

from app.database import Base
from app.main import (
    CAT_WORLD_BLIND_BOX_SERIES_BY_KEY,
    CAT_WORLD_CURRENT_BLIND_BOX_SERIES_KEY,
    CAT_WORLD_SHOP_BY_ID,
    cat_world_blind_box_catalog_payload,
    seed_cat_world_limited_cat_stock,
)
from app.models import CatWorldLimitedCatStock, CatWorldState


class CatWorldLimitedCatTest(unittest.TestCase):
    def test_japanese_bobtail_is_the_current_limited_series(self):
        self.assertEqual(CAT_WORLD_CURRENT_BLIND_BOX_SERIES_KEY, "japan-bobtail-2026-01")
        self.assertEqual(
            CAT_WORLD_SHOP_BY_ID["limited-cat-blind-box"]["seriesKey"],
            CAT_WORLD_CURRENT_BLIND_BOX_SERIES_KEY,
        )

        series = CAT_WORLD_BLIND_BOX_SERIES_BY_KEY[CAT_WORLD_CURRENT_BLIND_BOX_SERIES_KEY]
        self.assertEqual(series["region"], "日本")
        self.assertEqual(len(series["cats"]), 1)
        self.assertEqual(series["cats"][0]["cat"]["id"], "japanese-bobtail")
        self.assertEqual(series["cats"][0]["cat"]["rarity"], "SSR")

    def test_japanese_series_stock_is_seeded_once_and_visible(self):
        engine = create_engine("sqlite+pysqlite:///:memory:")
        Base.metadata.create_all(engine)
        with Session(engine) as db:
            seed_cat_world_limited_cat_stock(db)
            seed_cat_world_limited_cat_stock(db)

            rows = db.scalars(
                select(CatWorldLimitedCatStock).where(
                    CatWorldLimitedCatStock.series_key == CAT_WORLD_CURRENT_BLIND_BOX_SERIES_KEY
                )
            ).all()
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0].cat_id, "japanese-bobtail")
            self.assertEqual(rows[0].total_stock, 100)

            state = CatWorldState(phone="13900000000")
            catalog = cat_world_blind_box_catalog_payload(db, state, [])
            current = next(
                series
                for series in catalog["series"]
                if series["key"] == catalog["currentSeriesKey"]
            )
            series_keys = {series["key"] for series in catalog["series"]}
        engine.dispose()

        self.assertIn("china-heritage-2026-01", series_keys)
        self.assertEqual(current["region"], "日本")
        self.assertEqual(current["remainingStock"], 100)
        self.assertEqual(current["cats"][0]["oddsPercent"], 100.0)


if __name__ == "__main__":
    unittest.main()
