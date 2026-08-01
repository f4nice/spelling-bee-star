import os
import unittest

from fastapi import HTTPException
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session


os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")

from app.database import Base
from app.main import (
    CAT_WORLD_LIMITED_GIFT_INITIAL_STOCK,
    CAT_WORLD_LIMITED_GIFT_ITEM_ID,
    CAT_WORLD_SHOP_BY_ID,
    cat_world_limited_item_stock_payload,
    claim_cat_world_limited_item_stock,
    seed_cat_world_limited_item_stock,
)
from app.models import CatWorldLimitedItemStock


class CatWorldLimitedItemTest(unittest.TestCase):
    def test_limited_gift_has_initial_price_and_account_limit(self):
        item = CAT_WORLD_SHOP_BY_ID[CAT_WORLD_LIMITED_GIFT_ITEM_ID]

        self.assertEqual(item["category"], "toy")
        self.assertEqual(item["cost"], 100)
        self.assertEqual(item["maxOwned"], 1)
        self.assertTrue(item["limited"])

    def test_limited_gift_stock_is_seeded_once_and_claimed_once(self):
        engine = create_engine("sqlite+pysqlite:///:memory:")
        Base.metadata.create_all(engine)
        with Session(engine) as db:
            seed_cat_world_limited_item_stock(db)
            seed_cat_world_limited_item_stock(db)

            rows = db.scalars(select(CatWorldLimitedItemStock)).all()
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0].total_stock, CAT_WORLD_LIMITED_GIFT_INITIAL_STOCK)

            claim_cat_world_limited_item_stock(db, CAT_WORLD_LIMITED_GIFT_ITEM_ID)
            db.commit()
            stock = cat_world_limited_item_stock_payload(db, CAT_WORLD_LIMITED_GIFT_ITEM_ID)

        engine.dispose()
        self.assertEqual(stock["claimedCount"], 1)
        self.assertEqual(stock["remainingStock"], CAT_WORLD_LIMITED_GIFT_INITIAL_STOCK - 1)

    def test_sold_out_or_paused_gift_does_not_increment_stock(self):
        engine = create_engine("sqlite+pysqlite:///:memory:")
        Base.metadata.create_all(engine)
        with Session(engine) as db:
            row = CatWorldLimitedItemStock(
                item_id=CAT_WORLD_LIMITED_GIFT_ITEM_ID,
                total_stock=1,
                claimed_count=1,
                is_active=True,
            )
            db.add(row)
            db.commit()

            with self.assertRaises(HTTPException) as sold_out:
                claim_cat_world_limited_item_stock(db, CAT_WORLD_LIMITED_GIFT_ITEM_ID)
            self.assertEqual(sold_out.exception.status_code, 409)
            self.assertEqual(row.claimed_count, 1)

            row.claimed_count = 0
            row.is_active = False
            db.commit()
            with self.assertRaises(HTTPException) as paused:
                claim_cat_world_limited_item_stock(db, CAT_WORLD_LIMITED_GIFT_ITEM_ID)
            self.assertEqual(paused.exception.status_code, 409)
            self.assertEqual(row.claimed_count, 0)

        engine.dispose()


if __name__ == "__main__":
    unittest.main()
