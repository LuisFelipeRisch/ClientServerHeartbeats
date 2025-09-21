import pandas as pd
import sys

def calculate_stats_from_csv(file_path, column_name):
  try:
    df = pd.read_csv(file_path)

    if column_name not in df.columns:
      print(f"Error: Column '{column_name}' not found in the CSV file.")
      print(f"Available columns are: {list(df.columns)}")
      return

    mean_value = df[column_name].mean()
    std_dev_value = df[column_name].std()

    print(f"--- Statistics for column '{column_name}' ---")
    print(f"Mean: {mean_value:.2f}")
    print(f"Standard Deviation: {std_dev_value:.2f}")

  except FileNotFoundError:
    print(f"Error: The file '{file_path}' was not found.")
  except Exception as e:
    print(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
      csv_file_path = sys.argv[1]
    else:
      print("Usage: python script_name.py <path_to_csv_file>")
      sys.exit(1)

    target_column = 'time_taken_to_correct_ns'
    
    calculate_stats_from_csv(csv_file_path, target_column)