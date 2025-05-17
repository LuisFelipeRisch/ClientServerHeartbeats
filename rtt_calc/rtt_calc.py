import argparse
import os
import sys

ALPHA = 0.9

def update_estimated_an_deviation_rtt(estimated_rtt, deviation_rtt, current_rtt):
  if estimated_rtt == -1 and deviation_rtt == -1:
    estimated_rtt = current_rtt
    deviation_rtt = 0
  else:
    deviation_rtt = ALPHA * deviation_rtt + (1 - ALPHA) * abs(estimated_rtt - current_rtt)
    estimated_rtt = ALPHA * estimated_rtt + (1 - ALPHA) * current_rtt
    
  return estimated_rtt, deviation_rtt

def calculate_timeout(estimated_rtt, deviation_rtt, phi): 
  return estimated_rtt + phi * deviation_rtt

def print_estimated_deviation_timeout(estimated_rtt, deviation_rtt, timeout): 
  print(f"RTT_medio = {estimated_rtt}")
  print(f"Desvio_medio = {deviation_rtt}")
  print(f"Timeout = {timeout}\n")

parser = argparse.ArgumentParser(description="Recebe um valor phi (float) e o path para um arquivo existente de dados.")

parser.add_argument("phi", type=float, help="Um número em ponto flutuante representando o valor de phi.")
parser.add_argument("filepath", type=str, help="Caminho para um arquivo existente de dados.")

args = parser.parse_args()

if not os.path.isfile(args.filepath):
  print("Erro: o caminho fornecido não é um arquivo válido ou não existe.")
  sys.exit(1)

phi = args.phi
filepath = args.filepath

print(f"O valor definido para phi foi de: {phi}")
print(f"O caminho do arquivo fornecido foi: {filepath}\n")

estimated_rtt = -1
deviation_rtt = -1
current_rtt = -1

with open(filepath, "r") as file:
  for i, line in enumerate(file, start=1):
    try:
      current_rtt = float(line.strip())
      estimated_rtt, deviation_rtt = update_estimated_an_deviation_rtt(estimated_rtt, deviation_rtt, current_rtt)
    except ValueError:
      print(f"Erro: linha {i} não contém um número válido: {line.strip()}")
      sys.exit(1)

timeout = calculate_timeout(estimated_rtt, deviation_rtt, phi)

print_estimated_deviation_timeout(estimated_rtt, deviation_rtt, timeout)

while 1:
  current_rtt = float(input("Informe um novo valor de RTT. Digite -1 caso queira encerrar o programa: "))
  if current_rtt == -1: break
  
  estimated_rtt, deviation_rtt = update_estimated_an_deviation_rtt(estimated_rtt, deviation_rtt, current_rtt)
  timeout = calculate_timeout(estimated_rtt, deviation_rtt, phi)
  
  print_estimated_deviation_timeout(estimated_rtt, deviation_rtt, timeout)



