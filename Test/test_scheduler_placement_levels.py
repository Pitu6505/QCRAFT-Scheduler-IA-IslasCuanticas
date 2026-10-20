import unittest

from scheduler import placement_policy_name


class PlacementPolicyNameTests(unittest.TestCase):
    def test_maps_selected_levels_to_isolated_policy_queue(self):
        self.assertEqual(
            placement_policy_name("Islas_Cuanticas_Edges", [3, 2]),
            "Islas_Cuanticas_Edges_Niveles_2_3",
        )

    def test_preserves_existing_policy_when_levels_are_not_specified(self):
        self.assertEqual(
            placement_policy_name("Islas_Cuanticas_Edges", None),
            "Islas_Cuanticas_Edges",
        )

    def test_rejects_levels_for_unrelated_policy(self):
        with self.assertRaisesRegex(ValueError, "solo se puede usar"):
            placement_policy_name("time", [3])

    def test_rejects_empty_or_invalid_levels(self):
        for levels in ([], [0], [1, 1], [True], "3"):
            with self.subTest(levels=levels):
                with self.assertRaises(ValueError):
                    placement_policy_name("Islas_Cuanticas_Edges", levels)


if __name__ == "__main__":
    unittest.main()
