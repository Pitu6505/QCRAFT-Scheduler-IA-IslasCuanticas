import unittest

from executeCircuitIBM import is_valid_physical_layout


class PhysicalLayoutValidationTests(unittest.TestCase):
    def test_accepts_unique_physical_qubit_indices(self):
        self.assertTrue(is_valid_physical_layout([15, 14, 13], 3, 156))

    def test_rejects_non_integer_layout_entries(self):
        self.assertFalse(
            is_valid_physical_layout([15, {"sentinel": []}, 13], 3, 156)
        )

    def test_rejects_duplicate_or_out_of_range_qubits(self):
        self.assertFalse(is_valid_physical_layout([15, 15], 2, 156))
        self.assertFalse(is_valid_physical_layout([15, 156], 2, 156))

    def test_rejects_layout_with_wrong_size(self):
        self.assertFalse(is_valid_physical_layout([15], 2, 156))


if __name__ == "__main__":
    unittest.main()
