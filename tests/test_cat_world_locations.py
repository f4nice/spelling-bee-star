import json
import os
import unittest


os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")

from app.main import (
    CAT_WORLD_DECOR_DEFAULT_LAYOUT,
    CAT_WORLD_DEFAULT_SCENE_KEY,
    CAT_WORLD_SCENE_SEED_BY_KEY,
    CAT_WORLD_SHOP_BY_ID,
    CAT_WORLD_SPOT_MEMORY_MAX_STRENGTH,
    CAT_WORLD_STORAGE_LOCATION,
    cat_world_inventory_for_scene,
    cat_world_layout_item_allowed,
    cat_world_position_with_spot_memory,
    encode_cat_world_item_locations,
    encode_cat_world_scene_positions,
    normalize_cat_world_scene_position,
    parse_cat_world_item_locations,
    parse_cat_world_scene_positions,
)


class CatWorldLocationTest(unittest.TestCase):
    def test_five_new_window_ledges_are_complete_indoor_decor(self):
        window_ids = [
            "moon-window",
            "rain-window",
            "garden-window",
            "snow-window",
            "sea-window",
        ]

        self.assertEqual([CAT_WORLD_SHOP_BY_ID[item_id]["cost"] for item_id in window_ids], [240, 260, 280, 300, 320])
        self.assertTrue(all(CAT_WORLD_SHOP_BY_ID[item_id]["category"] == "decor" for item_id in window_ids))
        self.assertTrue(all(item_id in CAT_WORLD_DECOR_DEFAULT_LAYOUT for item_id in window_ids))

        yard_rules = CAT_WORLD_SCENE_SEED_BY_KEY["yard"]["itemRules"]
        self.assertTrue(all(not cat_world_layout_item_allowed(item_id, yard_rules) for item_id in window_ids))

    def test_old_inventory_defaults_furniture_and_toys_to_main_room(self):
        inventory = {
            "cloud-rug": 1,
            "rolling-ball": 1,
            "daily-kibble": 3,
        }

        locations = parse_cat_world_item_locations(None, inventory)

        self.assertEqual(
            locations,
            {
                "cloud-rug": CAT_WORLD_DEFAULT_SCENE_KEY,
                "rolling-ball": CAT_WORLD_DEFAULT_SCENE_KEY,
            },
        )
        self.assertEqual(
            cat_world_inventory_for_scene(inventory, locations, CAT_WORLD_DEFAULT_SCENE_KEY),
            inventory,
        )
        self.assertEqual(
            cat_world_inventory_for_scene(inventory, locations, "yard"),
            {"daily-kibble": 3},
        )

    def test_storage_and_scene_locations_filter_visual_items(self):
        inventory = {
            "cloud-rug": 1,
            "rolling-ball": 1,
            "daily-kibble": 2,
        }
        raw = encode_cat_world_item_locations(
            {
                "cloud-rug": "yard",
                "rolling-ball": CAT_WORLD_STORAGE_LOCATION,
            }
        )
        locations = parse_cat_world_item_locations(raw, inventory)

        self.assertEqual(
            cat_world_inventory_for_scene(inventory, locations, CAT_WORLD_DEFAULT_SCENE_KEY),
            {"daily-kibble": 2},
        )
        self.assertEqual(
            cat_world_inventory_for_scene(inventory, locations, "yard"),
            {"cloud-rug": 1, "daily-kibble": 2},
        )

    def test_scene_positions_are_clamped_and_invalid_values_are_discarded(self):
        self.assertEqual(
            normalize_cat_world_scene_position({"x": 128.456, "y": -9, "facing": -1}),
            {"x": 100.0, "y": 0.0, "facing": -1},
        )
        self.assertIsNone(normalize_cat_world_scene_position({"x": "nan", "y": 50}))

        encoded = encode_cat_world_scene_positions(
            {
                "main-room": {"x": 42.125, "y": 68.75, "facing": 1},
                "unknown-room": {"x": 10, "y": 20, "facing": 1},
            }
        )
        self.assertEqual(
            parse_cat_world_scene_positions(encoded),
            {"main-room": {"x": 42.12, "y": 68.75, "facing": 1}},
        )
        self.assertNotIn("unknown-room", json.loads(encoded))

    def test_scene_position_preserves_valid_spot_memory(self):
        encoded = encode_cat_world_scene_positions(
            {
                "main-room": {
                    "x": 42.125,
                    "y": 68.75,
                    "facing": 1,
                    "memoryItemId": "sun-window",
                    "memoryStrength": 3,
                }
            }
        )

        self.assertEqual(
            parse_cat_world_scene_positions(encoded)["main-room"],
            {
                "x": 42.12,
                "y": 68.75,
                "facing": 1,
                "memoryItemId": "sun-window",
                "memoryStrength": 3,
            },
        )

    def test_manual_furniture_placement_builds_individual_spot_memory(self):
        inventory = {"sun-window": 1, "cloud-rug": 1}
        room_layout = {"sun-window": {"x": 10, "y": 20}, "cloud-rug": {"x": 30, "y": 40}}
        position = {"x": 50, "y": 60, "facing": -1}

        first = cat_world_position_with_spot_memory(
            position, None, "sun-window", inventory, room_layout, {}
        )
        repeated = cat_world_position_with_spot_memory(
            position, first, "sun-window", inventory, room_layout, {}
        )
        changed = cat_world_position_with_spot_memory(
            position, repeated, "cloud-rug", inventory, room_layout, {}
        )

        self.assertEqual((first["memoryItemId"], first["memoryStrength"]), ("sun-window", 1))
        self.assertEqual((repeated["memoryItemId"], repeated["memoryStrength"]), ("sun-window", 2))
        self.assertEqual((changed["memoryItemId"], changed["memoryStrength"]), ("cloud-rug", 1))

    def test_spot_memory_is_capped_and_ordinary_walks_keep_it(self):
        inventory = {"sun-window": 1}
        room_layout = {"sun-window": {"x": 10, "y": 20}}
        previous = {
            "x": 10,
            "y": 20,
            "facing": 1,
            "memoryItemId": "sun-window",
            "memoryStrength": CAT_WORLD_SPOT_MEMORY_MAX_STRENGTH,
        }

        capped = cat_world_position_with_spot_memory(
            {"x": 30, "y": 40, "facing": -1},
            previous,
            "sun-window",
            inventory,
            room_layout,
            {},
        )
        walked = cat_world_position_with_spot_memory(
            {"x": 70, "y": 80, "facing": 1},
            capped,
            "",
            inventory,
            room_layout,
            {},
        )

        self.assertEqual(capped["memoryStrength"], CAT_WORLD_SPOT_MEMORY_MAX_STRENGTH)
        self.assertEqual((walked["memoryItemId"], walked["memoryStrength"]), ("sun-window", 5))

    def test_invalid_or_damaged_furniture_cannot_become_a_spot_memory(self):
        position = {"x": 50, "y": 60, "facing": 1}
        inventory = {"sun-window": 1, "cloud-rug": 1}
        room_layout = {"sun-window": {"x": 10, "y": 20}}

        not_in_room = cat_world_position_with_spot_memory(
            position, None, "cloud-rug", inventory, room_layout, {}
        )
        damaged = cat_world_position_with_spot_memory(
            position,
            {**position, "memoryItemId": "sun-window", "memoryStrength": 3},
            "sun-window",
            inventory,
            room_layout,
            {"sun-window": {"itemId": "sun-window"}},
        )

        self.assertNotIn("memoryItemId", not_in_room)
        self.assertNotIn("memoryItemId", damaged)


if __name__ == "__main__":
    unittest.main()
