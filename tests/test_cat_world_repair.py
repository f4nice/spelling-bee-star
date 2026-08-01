import os
import unittest

from fastapi import HTTPException


os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")

from app.main import CAT_WORLD_REPAIR_HAMMER_ITEM_ID, cat_world_consume_repair_resources


class CatWorldRepairTest(unittest.TestCase):
    def test_same_damaged_item_only_consumes_one_hammer(self):
        inventory = {CAT_WORLD_REPAIR_HAMMER_ITEM_ID: 2}
        damaged_items = {"reading-lamp": {"label": "阅读台灯", "repairCost": 63}}

        damaged, remaining = cat_world_consume_repair_resources(inventory, damaged_items, "reading-lamp")

        self.assertEqual(damaged["repairCost"], 63)
        self.assertEqual(remaining, 1)
        self.assertEqual(inventory[CAT_WORLD_REPAIR_HAMMER_ITEM_ID], 1)
        self.assertNotIn("reading-lamp", damaged_items)

        with self.assertRaises(HTTPException) as repeated:
            cat_world_consume_repair_resources(inventory, damaged_items, "reading-lamp")

        self.assertEqual(repeated.exception.status_code, 400)
        self.assertEqual(inventory[CAT_WORLD_REPAIR_HAMMER_ITEM_ID], 1)

    def test_missing_hammer_keeps_the_damaged_item(self):
        inventory = {}
        damaged_items = {"reading-lamp": {"label": "阅读台灯", "repairCost": 63}}

        with self.assertRaises(HTTPException) as missing_hammer:
            cat_world_consume_repair_resources(inventory, damaged_items, "reading-lamp")

        self.assertEqual(missing_hammer.exception.status_code, 400)
        self.assertIn("reading-lamp", damaged_items)


if __name__ == "__main__":
    unittest.main()
