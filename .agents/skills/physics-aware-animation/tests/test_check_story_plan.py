import copy
import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("check_story_plan", ROOT / "scripts/check_story_plan.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class StoryPlanTests(unittest.TestCase):
    def setUp(self):
        self.plan = json.loads((ROOT / "assets/scene-intent.example.json").read_text())

    def test_example_is_only_valid_intent(self):
        self.assertEqual(module.validate_plan(self.plan), [])

    def test_overlap_fails(self):
        self.plan["beats"][1]["target_window_s"] = [2.3, 3]
        self.assertTrue(module.validate_plan(self.plan))

    def test_gap_fails(self):
        self.plan["beats"][1]["target_window_s"] = [3, 3.5]
        self.assertTrue(module.validate_plan(self.plan))

    def test_collision_plus_bounce_tags_on_one_beat_is_not_two(self):
        self.plan["beats"] = [self.plan["beats"][1]]
        self.plan["beats"][0]["tags"] = ["collision", "bounce"]
        self.assertTrue(module.validate_plan(self.plan))

    def test_same_primary_kind_fails(self):
        for beat in self.plan["beats"]:
            beat["primary_kind"] = "acceleration"
        self.assertTrue(module.validate_plan(self.plan))

    def test_unknown_actor_fails(self):
        self.plan["beats"][0]["object_ids"] = ["ghost"]
        self.assertTrue(module.validate_plan(self.plan))

    def test_no_positive_gap_certificate_fails(self):
        del self.plan["beats"][2]["requires_positive_surface_gap"]
        self.assertTrue(module.validate_plan(self.plan))

    def test_moving_obstacle_exceeds_existing_analytic_scope(self):
        self.plan["objects"][3]["motion"] = "prescribed"
        self.assertTrue(module.validate_plan(self.plan))

    def test_two_spheres_exceed_existing_analytic_scope(self):
        self.plan["objects"].append({"id": "second", "role": "actor", "shape": "sphere", "motion": "dynamic", "scored": True})
        self.assertTrue(module.validate_plan(self.plan))

    def test_silent_support_cannot_be_scored(self):
        self.plan["objects"][1]["scored"] = True
        self.assertTrue(module.validate_plan(self.plan))

    def test_nan_window_fails(self):
        self.plan["beats"][0]["target_window_s"][0] = float("nan")
        self.assertTrue(module.validate_plan(self.plan))

    def test_duty_cycle_fails(self):
        self.plan["salience_policy"]["maximum_duty_cycle"] = 0.01
        self.assertTrue(module.validate_plan(self.plan))

    def test_boolean_duration_fails(self):
        self.plan["duration_s"] = True
        self.assertTrue(module.validate_plan(self.plan))

    def test_duplicate_ids_fail(self):
        self.plan["objects"].append(copy.deepcopy(self.plan["objects"][0]))
        self.assertTrue(module.validate_plan(self.plan))

    def test_invalid_document_fails(self):
        for invalid in [None, [], "foo", 5]:
            with self.subTest(invalid=invalid):
                self.assertTrue(module.validate_plan(invalid))

    def test_merge_requires_new_model(self):
        self.plan["beats"][1]["primary_kind"] = "merge"
        self.assertTrue(module.validate_plan(self.plan))

    def test_missing_cause_fails(self):
        del self.plan["beats"][0]["physical_cause"]
        self.assertTrue(module.validate_plan(self.plan))

    def test_two_speed_changes_alone_do_not_qualify(self):
        self.plan["beats"] = self.plan["beats"][:2]
        self.plan["beats"][1]["primary_kind"] = "deceleration"
        self.assertTrue(module.validate_plan(self.plan))


if __name__ == "__main__":
    unittest.main()
