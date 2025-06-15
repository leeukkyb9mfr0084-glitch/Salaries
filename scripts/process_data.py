import pandas as pd


def process_data(filepath):
    """
    Reads a CSV file, calculates the sum of the 'value' column,
    and returns the sum.
    """
    df = pd.read_csv(filepath)
    total_value = df["value"].sum()
    return total_value


if __name__ == "__main__":
    filepath = "data/raw_data.csv"
    sum_of_values = process_data(filepath)
    print(f"The sum of values is: {sum_of_values}")
