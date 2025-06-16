import unittest
import pandas as pd
from scripts.process_data import process_data


class TestProcessData(unittest.TestCase):

    def test_process_data(self):
        # Create a dummy CSV file for testing
        dummy_data = {
            "id": [1, 2, 3],
            "name": ["feat_a", "feat_b", "feat_c"],
            "value": [10, 20, 30],
        }
        dummy_df = pd.DataFrame(dummy_data)
        dummy_filepath = "tests/dummy_data.csv"
        dummy_df.to_csv(dummy_filepath, index=False)

        # Test the process_data function
        self.assertEqual(process_data(dummy_filepath), 60)


if __name__ == "__main__":
    unittest.main()
