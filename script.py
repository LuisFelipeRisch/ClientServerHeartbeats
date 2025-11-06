import subprocess
import random
import sys
import os

# 1. Verificação de argumento: Agora espera exatamente 2 
# (o nome do script e o path da pasta)
if len(sys.argv) != 2:
  print("Uso: python seu_script.py <path_da_pasta>")
  sys.exit(1)

# 2. O único argumento é o path da pasta
folder_path = sys.argv[1]

# Verificação se o path é um diretório válido
if not os.path.isdir(folder_path):
  print(f"Erro: O path '{folder_path}' não é um diretório válido.")
  sys.exit(1)

script_to_call = f'time_detection.py'

num_iterations = 30

print(f"Starting loop with {num_iterations} iterations...")
print(f"Target folder path: {folder_path}")

for i in range(num_iterations):
  random_int = random.randint(1, 863999)
  
  print(f"\n--- Iteration {i+1}/{num_iterations} ---")
  print(f"Generated random integer: {random_int}")
  
  try:
    params = [
      sys.executable, 
      script_to_call, 
      str(random_int),
      folder_path, 
    ]

    result = subprocess.run(
      params,
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