import subprocess
import random
import sys

script_to_call = 'time_detection.py'

num_iterations = 30

print(f"Starting loop with {num_iterations} iterations...")

for i in range(num_iterations):
  random_int = random.randint(1, 863999)
  
  print(f"\n--- Iteration {i+1}/{num_iterations} ---")
  print(f"Generated random integer: {random_int}")
  
  try:
    result = subprocess.run(
      [sys.executable, script_to_call, str(random_int)],
      check=True,
      capture_output=True,
      text=True
    )
  
    print("Output from called script:")
    print(result.stdout)
      
  except FileNotFoundError:
    print(f"Error: The script '{script_to_call}' was not found.")
  except subprocess.CalledProcessError as e:
    print(f"Error: The script '{script_to_call}' failed.")
    print("Error output:")
    print(e.stderr)
  except Exception as e:
    print(f"An unexpected error occurred: {e}")

print("\nLoop finished.")