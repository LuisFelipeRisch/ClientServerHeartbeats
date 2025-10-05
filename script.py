import subprocess
import random
import sys

if len(sys.argv) < 2 or len(sys.argv) > 3:
  print("Uso: python seu_script.py <week_day|weekend> [tun_phi_2|tun_phi_4]")
  sys.exit(1)

day_type = sys.argv[1]
if day_type not in ['week_day', 'weekend']:
  print("Erro: O primeiro parâmetro deve ser 'week_day' ou 'weekend'.")
  sys.exit(1)

phi_type = ''
if len(sys.argv) == 3:
  optional_param = sys.argv[2]
  if optional_param not in ['tun_phi_2', 'tun_phi_4']:
      print("Aviso: O segundo parâmetro opcional é inválido. Usando o valor padrão 'tun_phi_normal'.")
  else:
      phi_type = optional_param

script_to_call = f'time_detection.py'

num_iterations = 30

print(f"Starting loop with {num_iterations} iterations...")

for i in range(num_iterations):
  random_int = random.randint(1, 863999)
  
  print(f"\n--- Iteration {i+1}/{num_iterations} ---")
  print(f"Generated random integer: {random_int}")
  
  try:
    params = [sys.executable, script_to_call, str(random_int), day_type]
    if phi_type != '': 
      params.append(phi_type)
      
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