import asyncio
import json
import os
import unittest
from unittest.mock import patch

from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from starlette.requests import Request


os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")

from app import main as m
from app.database import Base
from app.main import (
    CAT_WORLD_REPAIR_HAMMER_ITEM_ID,
    cat_world_consume_repair_resources,
    encode_cat_world_damaged_items,
    encode_cat_world_inventory,
    parse_cat_world_inventory,
)
from app.models import CatWorldState


class CatWorldRepairTest(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite+pysqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.db = Session(self.engine, expire_on_commit=False)
        self.addCleanup(self.engine.dispose)
        self.addCleanup(self.db.close)

    @staticmethod
    def request_for(payload):
        body = json.dumps(payload).encode()

        async def receive():
            return {"type": "http.request", "body": body}

        return Request({"type": "http", "headers": []}, receive=receive)

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

    def test_purchase_charges_once_and_repair_only_consumes_hammer(self):
        m.seed_cat_world_scenes(self.db)
        state = CatWorldState(phone="13900000000", energy_spent=0)
        self.db.add(state)
        self.db.commit()
        payload = {"energy": {"earned": 1000, "available": 1000}}

        with patch.object(m, "require_cat_world_phone", return_value=state.phone), \
             patch.object(m, "serialize_cat_world_payload", return_value=payload):
            asyncio.run(m.vue_cat_world_purchase_api(
                self.request_for({"itemId": CAT_WORLD_REPAIR_HAMMER_ITEM_ID}),
                self.db,
            ))

        self.assertEqual(state.energy_spent, 100)
        inventory = parse_cat_world_inventory(state.inventory)
        self.assertEqual(inventory[CAT_WORLD_REPAIR_HAMMER_ITEM_ID], 1)

        inventory["book-shelf"] = 1
        state.inventory = encode_cat_world_inventory(inventory)
        state.damaged_items = encode_cat_world_damaged_items({
            "book-shelf": {
                "label": "英文书架",
                "catId": "mimi",
                "repairCost": 999,
            }
        })
        self.db.commit()

        payload = {"energy": {"earned": 100, "available": 0}}
        with patch.object(m, "require_cat_world_phone", return_value=state.phone), \
             patch.object(m, "cat_world_locked_state", return_value=state), \
             patch.object(m, "serialize_cat_world_payload", return_value=payload):
            result = asyncio.run(m.vue_cat_world_repair_api(
                self.request_for({"itemId": "book-shelf"}),
                self.db,
            ))

        self.assertEqual(state.energy_spent, 100)
        self.assertEqual(result["repair"]["cost"], 0)
        self.assertEqual(result["repair"]["hammerRemaining"], 0)
        self.assertNotIn(CAT_WORLD_REPAIR_HAMMER_ITEM_ID, parse_cat_world_inventory(state.inventory))
        self.assertNotIn("book-shelf", m.parse_cat_world_damaged_items(state.damaged_items))

        with patch.object(m, "require_cat_world_phone", return_value=state.phone), \
             patch.object(m, "cat_world_locked_state", return_value=state):
            with self.assertRaises(HTTPException) as repeated:
                asyncio.run(m.vue_cat_world_repair_api(
                    self.request_for({"itemId": "book-shelf"}), self.db,
                ))
        self.assertEqual(repeated.exception.status_code, 400)
        self.assertEqual(state.energy_spent, 100)
        self.assertNotIn(CAT_WORLD_REPAIR_HAMMER_ITEM_ID, parse_cat_world_inventory(state.inventory))


if __name__ == "__main__":
    unittest.main()
