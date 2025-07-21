import argparse
import os
import sys
import math

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

def print_values(current_rtt, estimated_rtt, deviation_rtt, time_period, time_period_mul_rtt_sum, time_period_sum, rtt_sum, time_period_squared_sum, linear_coefficient, slope_coefficient, trend, calculated_phi, timeout): 
  print(f"current_rtt = {current_rtt}")
  print(f"estimated_rtt = {estimated_rtt}")
  print(f"deviation_rtt = {deviation_rtt}")
  print(f"time_period = {time_period}")
  print(f"time_period_mul_rtt_sum = {time_period_mul_rtt_sum}")
  print(f"time_period_sum = {time_period_sum}")
  print(f"rtt_sum = {rtt_sum}")
  print(f"time_period_squared_sum = {time_period_squared_sum}")
  print(f"linear_coefficient = {linear_coefficient}")
  print(f"slope_coefficient = {slope_coefficient:.2f}")
  print(f"trend = {trend}")
  print(f"calculated_phi = {calculated_phi}")
  print(f"timeout = {timeout}\n")

parser = argparse.ArgumentParser(description="Recebe um valor phi inicial (float) e o path para um arquivo existente de dados.")

parser.add_argument("start_phi", type=float, help="Um número em ponto flutuante representando o valor inicial de phi.")
parser.add_argument("filepath", type=str, help="Caminho para um arquivo existente de dados.")

args = parser.parse_args()

if not os.path.isfile(args.filepath):
  print("Erro: o caminho fornecido não é um arquivo válido ou não existe.")
  sys.exit(1)

start_phi = args.start_phi
filepath = args.filepath

print(f"O valor definido para start_phi foi de: {start_phi}")
print(f"O caminho do arquivo fornecido foi: {filepath}\n")

estimated_rtt = -1
deviation_rtt = -1
current_rtt = -1
time_period = 0.0
time_period_mul_rtt_sum = 0.0
time_period_sum = 0.0
rtt_sum = 0.0 
time_period_squared_sum = 0.0

with open(filepath, "r") as file:
  for i, line in enumerate(file, start=1):
    try:
      current_rtt = float(line.strip())
      estimated_rtt, deviation_rtt = update_estimated_an_deviation_rtt(estimated_rtt, deviation_rtt, current_rtt)

      time_period += 1.0
      time_period_mul_rtt_sum += time_period * current_rtt
      time_period_sum += time_period
      rtt_sum += current_rtt
      time_period_squared_sum += time_period * time_period
      
      divisor = ((time_period * time_period_squared_sum) - (time_period_sum * time_period_sum))
      linear_coefficient = -1
      if math.isclose(divisor, 0.0): 
        linear_coefficient = 0.0
      else:
        linear_coefficient = ((time_period * time_period_mul_rtt_sum) - (time_period_sum * rtt_sum)) / float(divisor)

      slope_coefficient = (rtt_sum - (linear_coefficient * time_period_sum)) / float(time_period)
      trend = linear_coefficient + (slope_coefficient * time_period)
      
      calculated_phi = -1
      if math.isclose(deviation_rtt, 0.0):
        calculated_phi = start_phi
      else:
        calculated_phi = math.ceil(abs(((trend + deviation_rtt) - estimated_rtt) / float(deviation_rtt)))
      
      timeout = calculate_timeout(estimated_rtt, deviation_rtt, calculated_phi)

      print_values(current_rtt, estimated_rtt, deviation_rtt, time_period, time_period_mul_rtt_sum, time_period_sum, rtt_sum, time_period_squared_sum, linear_coefficient, slope_coefficient, trend, calculated_phi, timeout)
    except ValueError:
      print(f"Erro: linha {i} não contém um número válido: {line.strip()}")
      sys.exit(1)

timeout = calculate_timeout(estimated_rtt, deviation_rtt, calculated_phi)

print_estimated_deviation_timeout(estimated_rtt, deviation_rtt, timeout)

while 1:
  current_rtt = float(input("Informe um novo valor de RTT. Digite -1 caso queira encerrar o programa: "))
  if current_rtt == -1: break
  
  estimated_rtt, deviation_rtt = update_estimated_an_deviation_rtt(estimated_rtt, deviation_rtt, current_rtt)
  timeout = calculate_timeout(estimated_rtt, deviation_rtt, phi)
  
  print_estimated_deviation_timeout(estimated_rtt, deviation_rtt, timeout)



