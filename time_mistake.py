import math
from datetime import datetime
from zoneinfo import ZoneInfo
import random
import csv
import sys
import os

SERVER_RECEIVED_AT_INDEX = 3
SEQUENCE_NUMBER_INDEX    = 4
NS_TO_INCREASE           = 2000000000 
PHI_MULTIPLIER           = 1

def save_mistakes_to_csv(filename, data, headers):
    try:
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=headers)
            writer.writeheader()
            for row in data:
                writer.writerow(row)
        print(f"Dados salvos com sucesso em '{filename}'")
    except IOError:
        print(f"Erro de I/O: Não foi possível escrever no arquivo '{filename}'.")
    except Exception as e:
        print(f"Ocorreu um erro inesperado ao escrever em '{filename}': {e}")

def chance(perc):
  return False
  # sorteio = random.uniform(0, 100)
  # return sorteio < perc

class JacobsonTimeoutCalculator:
  ALPHA = 0.9
  PHI   = 4.0

  def __init__(self):
    self.estimated_rtt           = -1
    self.deviation_rtt           = -1
    self.last_server_received_at = -1
    self.amount_misses           = 0
    self.amount_hits             = 0
    self.calculated_timeouts_at  = []
    self.time_mistakes           = []

  def __update_statistics(self, server_received_at, sequence_number_received): 
    if len(self.calculated_timeouts_at) == 0: return
    timeout_at = self.calculated_timeouts_at[-1]

    if int(timeout_at) >= server_received_at: 
      self.amount_hits += 1
      return
    
    self.amount_misses += 1
    time_mistake_dict  = {
      "sequence_number": sequence_number_received, 
      "time_taken_to_correct_s": (server_received_at - timeout_at) / 1_000_000_000
    }

    self.time_mistakes.append(time_mistake_dict)

    unix_seconds_timeout_at         = timeout_at / 1_000_000_000 
    unix_seconds_server_received_at = server_received_at / 1_000_000_000

    utc_time_timeout_at         = datetime.fromtimestamp(unix_seconds_timeout_at, tz=ZoneInfo("UTC"))
    utc_time_server_received_at = datetime.fromtimestamp(unix_seconds_server_received_at, tz=ZoneInfo("UTC"))

    local_zone = ZoneInfo("America/Sao_Paulo")

    local_time_timeout_at         = utc_time_timeout_at.astimezone(local_zone)
    local_time_server_received_at = utc_time_server_received_at.astimezone(local_zone)

    print(f"[TIMEOUT - Jacobson] - Expected to receive message of sequence number {sequence_number_received} at least until {local_time_timeout_at.strftime('%Y-%m-%d %H:%M:%S %Z')}, but it was received at {local_time_server_received_at.strftime('%Y-%m-%d %H:%M:%S %Z')}")

  def __update_estimated_an_deviation_rtt(self, server_received_at): 
    if self.last_server_received_at != -1: 
      interval = server_received_at - self.last_server_received_at

      if self.estimated_rtt == -1 and self.deviation_rtt == -1: 
        self.estimated_rtt = interval
        self.deviation_rtt = 0
      else: 
        self.deviation_rtt = self.ALPHA * self.deviation_rtt + (1 - self.ALPHA) * abs(self.estimated_rtt - interval)
        self.estimated_rtt = self.ALPHA * self.estimated_rtt + (1 - self.ALPHA) * interval
    
  def calculate_timeout_at(self, server_received_at, sequence_number_received):
    self.__update_statistics(server_received_at, sequence_number_received)
    self.__update_estimated_an_deviation_rtt(server_received_at)

    self.last_server_received_at = server_received_at

    if self.estimated_rtt == -1 and self.deviation_rtt == -1: 
      return -1
    
    timeout_at = server_received_at + (self.estimated_rtt + self.PHI * self.deviation_rtt)

    self.calculated_timeouts_at.append(timeout_at)

class NewRTOTimeoutCalculator:
  ALPHA = 0.9
  PHI   = 4.0

  def __init__(self):
    self.estimated_rtt           = -1
    self.deviation_rtt           = -1
    self.last_server_received_at = -1
    self.amount_misses           = 0
    self.amount_hits             = 0
    self.calculated_timeouts_at  = []
    self.time_mistakes           = []
    self.mean_mistake            = -1

  def __update_statistics(self, server_received_at, sequence_number_received): 
    if len(self.calculated_timeouts_at) == 0: return
    timeout_at = self.calculated_timeouts_at[-1]

    if int(timeout_at) >= server_received_at: 
      self.amount_hits += 1
      return
    
    self.amount_misses += 1
    time_mistake_dict  = {
      "sequence_number": sequence_number_received, 
      "time_taken_to_correct_s": (server_received_at - timeout_at) / 1_000_000_000
    }

    if self.mean_mistake == -1:
      self.mean_mistake = server_received_at - timeout_at
    else: 
      self.mean_mistake = (self.ALPHA * self.mean_mistake) + (1 - self.ALPHA) * (server_received_at - timeout_at)

    self.time_mistakes.append(time_mistake_dict)

    unix_seconds_timeout_at         = timeout_at / 1_000_000_000 
    unix_seconds_server_received_at = server_received_at / 1_000_000_000

    utc_time_timeout_at         = datetime.fromtimestamp(unix_seconds_timeout_at, tz=ZoneInfo("UTC"))
    utc_time_server_received_at = datetime.fromtimestamp(unix_seconds_server_received_at, tz=ZoneInfo("UTC"))

    local_zone = ZoneInfo("America/Sao_Paulo")

    local_time_timeout_at         = utc_time_timeout_at.astimezone(local_zone)
    local_time_server_received_at = utc_time_server_received_at.astimezone(local_zone)

    print(f"[TIMEOUT - NewRTO] - Expected to receive message of sequence number {sequence_number_received} at least until {local_time_timeout_at.strftime('%Y-%m-%d %H:%M:%S %Z')}, but it was received at {local_time_server_received_at.strftime('%Y-%m-%d %H:%M:%S %Z')}")

  def __update_estimated_an_deviation_rtt(self, server_received_at): 
    if self.last_server_received_at != -1: 
      interval = server_received_at - self.last_server_received_at

      if self.estimated_rtt == -1 and self.deviation_rtt == -1: 
        self.estimated_rtt = interval
        self.deviation_rtt = 0
      else: 
        self.deviation_rtt = self.ALPHA * self.deviation_rtt + (1 - self.ALPHA) * abs(self.estimated_rtt - interval)
        self.estimated_rtt = self.ALPHA * self.estimated_rtt + (1 - self.ALPHA) * interval
    
  def calculate_timeout_at(self, server_received_at, sequence_number_received):
    self.__update_statistics(server_received_at, sequence_number_received)
    self.__update_estimated_an_deviation_rtt(server_received_at)

    self.last_server_received_at = server_received_at

    if self.estimated_rtt == -1 and self.deviation_rtt == -1: 
      return -1
    
    timeout_at = server_received_at + (self.estimated_rtt + self.PHI * self.deviation_rtt)
    if self.mean_mistake != -1: 
      timeout_at += self.mean_mistake

    self.calculated_timeouts_at.append(timeout_at)
  
class TuningPhiTimeoutCalculator: 
  ALPHA   = 0.9
  PHI_MAX = 4
  PHI_MIN = 1

  def __init__(self):
    self.time_period             = 0.0
    self.time_period_mul_rtt_sum = 0.0
    self.time_period_sum         = 0.0
    self.rtt_sum                 = 0.0 
    self.time_period_squared_sum = 0.0
    self.estimated_rtt           = -1
    self.deviation_rtt           = -1
    self.mean_mistake            = -1
    self.last_server_received_at = -1
    self.interval                = -1 
    self.amount_misses           = 0
    self.amount_hits             = 0
    self.calculated_timeouts_at  = []
    self.time_mistakes           = []

  def __update_statistics(self, server_received_at, sequence_number_received): 
    if len(self.calculated_timeouts_at) == 0: return

    timeout_at = self.calculated_timeouts_at[-1]

    if int(timeout_at) >= server_received_at: 
      self.amount_hits += 1
      return
    
    self.amount_misses += 1
    time_mistake_dict  = {
      "sequence_number": sequence_number_received, 
      "time_taken_to_correct_s": (server_received_at - timeout_at) / 1_000_000_000
    }

    if self.mean_mistake == -1:
      self.mean_mistake = server_received_at - timeout_at
    else: 
      self.mean_mistake = (self.ALPHA * self.mean_mistake) + (1 - self.ALPHA) * (server_received_at - timeout_at)

    self.time_mistakes.append(time_mistake_dict)

    unix_seconds_timeout_at         = timeout_at / 1_000_000_000 
    unix_seconds_server_received_at = server_received_at / 1_000_000_000

    utc_time_timeout_at         = datetime.fromtimestamp(unix_seconds_timeout_at, tz=ZoneInfo("UTC"))
    utc_time_server_received_at = datetime.fromtimestamp(unix_seconds_server_received_at, tz=ZoneInfo("UTC"))

    local_zone = ZoneInfo("America/Sao_Paulo")

    local_time_timeout_at         = utc_time_timeout_at.astimezone(local_zone)
    local_time_server_received_at = utc_time_server_received_at.astimezone(local_zone)

    print(f"[TIMEOUT - TuningPhi] - Expected to receive message of sequence number {sequence_number_received} at least until {local_time_timeout_at.strftime('%Y-%m-%d %H:%M:%S %Z')}, but it was received at {local_time_server_received_at.strftime('%Y-%m-%d %H:%M:%S %Z')}")

  def __update_estimated_an_deviation_rtt(self, server_received_at): 
    if self.last_server_received_at != -1: 
      self.interval = server_received_at - self.last_server_received_at

      if self.estimated_rtt == -1 and self.deviation_rtt == -1: 
        self.estimated_rtt = self.interval
        self.deviation_rtt = 0
      else: 
        self.deviation_rtt = self.ALPHA * self.deviation_rtt + (1 - self.ALPHA) * abs(self.estimated_rtt - self.interval)
        self.estimated_rtt = self.ALPHA * self.estimated_rtt + (1 - self.ALPHA) * self.interval

  def calculate_timeout_at(self, server_received_at, sequence_number_received):
    self.__update_statistics(server_received_at, sequence_number_received)
    self.__update_estimated_an_deviation_rtt(server_received_at)

    self.last_server_received_at = server_received_at

    if self.estimated_rtt == -1 and self.deviation_rtt == -1: 
      return -1
    
    self.time_period             += 1.0
    self.time_period_mul_rtt_sum += self.time_period * self.interval
    self.time_period_sum         += self.time_period
    self.rtt_sum                 += self.interval
    self.time_period_squared_sum += self.time_period * self.time_period

    divisor = ((self.time_period * self.time_period_squared_sum) - (self.time_period_sum * self.time_period_sum))
    slope_coefficient = -1
    if math.isclose(divisor, 0.0): 
      slope_coefficient = 0.0
    else:
      slope_coefficient = ((self.time_period * self.time_period_mul_rtt_sum) - (self.time_period_sum * self.rtt_sum)) / float(divisor)

    linear_coefficient = (self.rtt_sum - (slope_coefficient * self.time_period_sum)) / float(self.time_period)
    trend              = linear_coefficient + (slope_coefficient * (self.time_period + 1))

    calculated_phi = -1
    if math.isclose(self.deviation_rtt, 0.0):
      calculated_phi = random.randint(self.PHI_MIN, self.PHI_MAX)
    else:
      calculated_phi = math.ceil(abs(((trend + self.deviation_rtt) - self.estimated_rtt) / float(self.deviation_rtt)))

    calculated_phi = max(1.0, calculated_phi)
    calculated_phi = min(4.0, calculated_phi)

    timeout_at = server_received_at + (self.estimated_rtt + (PHI_MULTIPLIER * calculated_phi) * self.deviation_rtt)
       
    self.calculated_timeouts_at.append(timeout_at)

class EstimatedTimeoutCalculator: 
  ALPHA   = 0.9
  PHI_MAX = 4
  PHI_MIN = 1

  def __init__(self):
    self.time_period             = 0.0
    self.time_period_mul_rtt_sum = 0.0
    self.time_period_sum         = 0.0
    self.rtt_sum                 = 0.0 
    self.time_period_squared_sum = 0.0
    self.estimated_rtt           = -1
    self.deviation_rtt           = -1
    self.last_server_received_at = -1
    self.interval                = -1 
    self.amount_misses           = 0
    self.amount_hits             = 0
    self.calculated_timeouts_at  = []
    self.time_mistakes           = []

  def __update_statistics(self, server_received_at, sequence_number_received): 
    if len(self.calculated_timeouts_at) == 0: return

    timeout_at = self.calculated_timeouts_at[-1]

    if int(timeout_at) >= server_received_at: 
      self.amount_hits += 1
      return
    
    self.amount_misses += 1
    time_mistake_dict  = {
      "sequence_number": sequence_number_received, 
      "time_taken_to_correct_s": (server_received_at - timeout_at) / 1_000_000_000
    }

    self.time_mistakes.append(time_mistake_dict)

    unix_seconds_timeout_at         = timeout_at / 1_000_000_000 
    unix_seconds_server_received_at = server_received_at / 1_000_000_000

    utc_time_timeout_at         = datetime.fromtimestamp(unix_seconds_timeout_at, tz=ZoneInfo("UTC"))
    utc_time_server_received_at = datetime.fromtimestamp(unix_seconds_server_received_at, tz=ZoneInfo("UTC"))

    local_zone = ZoneInfo("America/Sao_Paulo")

    local_time_timeout_at         = utc_time_timeout_at.astimezone(local_zone)
    local_time_server_received_at = utc_time_server_received_at.astimezone(local_zone)

    print(f"[TIMEOUT - Estimated] - Expected to receive message of sequence number {sequence_number_received} at least until {local_time_timeout_at.strftime('%Y-%m-%d %H:%M:%S %Z')}, but it was received at {local_time_server_received_at.strftime('%Y-%m-%d %H:%M:%S %Z')}")

  def __update_estimated_an_deviation_rtt(self, server_received_at): 
    if self.last_server_received_at != -1: 
      self.interval = server_received_at - self.last_server_received_at

      if self.estimated_rtt == -1 and self.deviation_rtt == -1: 
        self.estimated_rtt = self.interval
        self.deviation_rtt = 0
      else: 
        self.deviation_rtt = self.ALPHA * self.deviation_rtt + (1 - self.ALPHA) * abs(self.estimated_rtt - self.interval)
        self.estimated_rtt = self.ALPHA * self.estimated_rtt + (1 - self.ALPHA) * self.interval
  
  def calculate_timeout_at(self, server_received_at, sequence_number_received):
    self.__update_statistics(server_received_at, sequence_number_received)
    self.__update_estimated_an_deviation_rtt(server_received_at)

    self.last_server_received_at = server_received_at

    if self.estimated_rtt == -1 and self.deviation_rtt == -1: 
      return -1
    
    self.time_period             += 1.0
    self.time_period_mul_rtt_sum += self.time_period * self.interval
    self.time_period_sum         += self.time_period
    self.rtt_sum                 += self.interval
    self.time_period_squared_sum += self.time_period * self.time_period

    divisor = ((self.time_period * self.time_period_squared_sum) - (self.time_period_sum * self.time_period_sum))
    slope_coefficient = -1
    if math.isclose(divisor, 0.0): 
      slope_coefficient = 0.0
    else:
      slope_coefficient = ((self.time_period * self.time_period_mul_rtt_sum) - (self.time_period_sum * self.rtt_sum)) / float(divisor)

    linear_coefficient = (self.rtt_sum - (slope_coefficient * self.time_period_sum)) / float(self.time_period)
    trend              = linear_coefficient + (slope_coefficient * (self.time_period + 1))

    timeout_at = server_received_at + trend

    self.calculated_timeouts_at.append(timeout_at)

if len(sys.argv) < 3 or len(sys.argv) > 4:
  print("Uso: python seu_script.py <week_day|weekend> <fonte_trace> [tun_phi_2|tun_phi_4]")
  print("Exemplo: python seu_script.py week_day ufpr_sydney tun_phi_4")
  sys.exit(1)

day_type = sys.argv[1]
trace_source = sys.argv[2] 

if day_type not in ['week_day', 'weekend']:
  print("Erro: O primeiro parâmetro deve ser 'week_day' ou 'weekend'.")
  sys.exit(1)

phi_type = 'tun_phi_normal'
if len(sys.argv) == 4:
  optional_param = sys.argv[3]
  if optional_param not in ['tun_phi_2', 'tun_phi_4']:
      print("Aviso: O terceiro parâmetro opcional é inválido. Usando o valor padrão 'tun_phi_normal'.")
  else:
      phi_type = optional_param

if phi_type == 'tun_phi_2':
  PHI_MULTIPLIER = 2
elif phi_type == 'tun_phi_4':
  PHI_MULTIPLIER = 4

jac_timeout_calculator = JacobsonTimeoutCalculator()
tun_phi_calculator     = TuningPhiTimeoutCalculator()
estimated_calculator   = EstimatedTimeoutCalculator()
new_rto_calculator     = NewRTOTimeoutCalculator()

trace_directory = f"./traces_{trace_source}_{day_type}/raw"

for i in range(0, 1):
  file_path = os.path.join(trace_directory, f"log_{i}.txt")

  with open(file_path) as file:
    for x, line in enumerate(file, start=1):
      if x == 1:
        continue

      splitted_line = line.strip().split(';')

      server_received_at       = int(splitted_line[SERVER_RECEIVED_AT_INDEX])
      sequence_number_received = int(splitted_line[SEQUENCE_NUMBER_INDEX])

      if chance(0.01):
        server_received_at += NS_TO_INCREASE

      jac_timeout_calculator.calculate_timeout_at(server_received_at, sequence_number_received)
      tun_phi_calculator.calculate_timeout_at(server_received_at, sequence_number_received)
      estimated_calculator.calculate_timeout_at(server_received_at, sequence_number_received)
      new_rto_calculator.calculate_timeout_at(server_received_at, sequence_number_received)

csv_output_dir = f'csvs/{trace_source}/{day_type}/time_mistake/{phi_type}'

os.makedirs(csv_output_dir, exist_ok=True)

csv_filename_jac = os.path.join(csv_output_dir, 'jac.csv')
csv_filename_tun = os.path.join(csv_output_dir, 'tun_phi.csv')
csv_filename_est = os.path.join(csv_output_dir, 'estimated.csv')
csv_filename_new = os.path.join(csv_output_dir, 'new_rto.csv')

column_headers = ['sequence_number', 'time_taken_to_correct_s']

save_mistakes_to_csv(csv_filename_jac, jac_timeout_calculator.time_mistakes, column_headers)
save_mistakes_to_csv(csv_filename_tun, tun_phi_calculator.time_mistakes, column_headers)
save_mistakes_to_csv(csv_filename_est, estimated_calculator.time_mistakes, column_headers)
save_mistakes_to_csv(csv_filename_new, new_rto_calculator.time_mistakes, column_headers)