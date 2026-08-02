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
    cat_world_cat_favorite_decor_ids,
    cat_world_collection_catalog_payload,
    seed_cat_world_limited_cat_stock,
)
from app.models import CatWorldLimitedCatStock, CatWorldState


class CatWorldLimitedCatTest(unittest.TestCase):
    def test_turkish_cats_are_the_current_limited_series(self):
        self.assertEqual(CAT_WORLD_CURRENT_BLIND_BOX_SERIES_KEY, "turkey-water-2026-01")
        self.assertEqual(
            CAT_WORLD_SHOP_BY_ID["limited-cat-blind-box"]["seriesKey"],
            CAT_WORLD_CURRENT_BLIND_BOX_SERIES_KEY,
        )

        series = CAT_WORLD_BLIND_BOX_SERIES_BY_KEY[CAT_WORLD_CURRENT_BLIND_BOX_SERIES_KEY]
        self.assertEqual(series["region"], "土耳其")
        self.assertEqual(len(series["cats"]), 2)
        self.assertEqual(
            [(row["cat"]["id"], row["cat"]["rarity"], row["totalStock"]) for row in series["cats"]],
            [("turkish-van", "SR", 80), ("turkish-angora", "SSR", 20)],
        )

    def test_turkish_series_stock_is_seeded_once_and_visible(self):
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
            self.assertEqual(len(rows), 2)
            self.assertEqual(
                {(row.cat_id, row.total_stock) for row in rows},
                {("turkish-van", 80), ("turkish-angora", 20)},
            )

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
        self.assertIn("japan-bobtail-2026-01", series_keys)
        self.assertEqual(current["region"], "土耳其")
        self.assertEqual(current["remainingStock"], 100)
        self.assertEqual(
            {row["id"]: row["oddsPercent"] for row in current["cats"]},
            {"turkish-van": 80.0, "turkish-angora": 20.0},
        )
        collection = cat_world_collection_catalog_payload(catalog, [])
        turkey_section = next(section for section in collection["sections"] if section["region"] == "土耳其")
        self.assertEqual(
            [cat["id"] for cat in turkey_section["cats"]],
            ["turkish-van", "turkish-angora"],
        )

    def test_turkish_cats_have_region_specific_decor_preferences(self):
        self.assertEqual(
            set(cat_world_cat_favorite_decor_ids("turkish-van")),
            {"mini-fountain", "bubble-bathtub", "sea-window"},
        )
        self.assertEqual(
            set(cat_world_cat_favorite_decor_ids("turkish-angora")),
            {"sun-window", "book-shelf", "snow-window"},
        )


if __name__ == "__main__":
    unittest.main()
