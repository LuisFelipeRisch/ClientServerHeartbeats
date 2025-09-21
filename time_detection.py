import math
from datetime import datetime
from zoneinfo import ZoneInfo
import random
import csv
import sys

SERVER_RECEIVED_AT_INDEX = 3
SEQUENCE_NUMBER_INDEX    = 4

if len(sys.argv) < 2:
  raise ValueError("Nenhum valor para BREAK_ON_SEQUENCE_NB foi fornecido. Por favor, passe um número como argumento de linha de comando.")

try:
  BREAK_ON_SEQUENCE_NB = int(sys.argv[1])
  print(f"Using BREAK_ON_SEQUENCE_NB from command line: {BREAK_ON_SEQUENCE_NB}")
except ValueError:
  raise ValueError(f"O argumento fornecido '{sys.argv[1]}' não é um número válido. Por favor, passe um número inteiro.")

def add_row_to_csv(file_path, sequence_number, time_to_detect_ns):
  headers = ['sequence_number', 'time_to_detect_ns']
  new_row = {
    'sequence_number': sequence_number,
    'time_to_detect_ns': time_to_detect_ns
  }

  try:
    with open(file_path, 'a', newline='') as csvfile:
      writer = csv.DictWriter(csvfile, fieldnames=headers)
    
      writer.writerow(new_row)
      print(f"Successfully added row to '{file_path}': {new_row}")

  except FileNotFoundError:
    print(f"Error: The directory for file '{file_path}' was not found.")
  except IOError as e:
    print(f"I/O Error: Could not write to file '{file_path}'. Details: {e}")
  except Exception as e:
    print(f"An unexpected error occurred: {e}")

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
    self.time_detection          = -1

  def __update_statistics(self, server_received_at, sequence_number_received): 
    if len(self.calculated_timeouts_at) == 0: return

    timeout_at = self.calculated_timeouts_at[-1]

    if timeout_at > server_received_at or math.isclose(timeout_at, server_received_at): 
      self.amount_hits += 1
      return
    
    self.amount_misses += 1
    time_mistake_dict  = {
      "sequence_number": sequence_number_received, 
      "time_taken_to_correct_ns": server_received_at - timeout_at
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

    if sequence_number_received == BREAK_ON_SEQUENCE_NB: 
      self.time_detection = timeout_at - server_received_at
  
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
    self.last_server_received_at = -1
    self.interval                = -1 
    self.amount_misses           = 0
    self.amount_hits             = 0
    self.calculated_timeouts_at  = []
    self.time_mistakes           = []
    self.time_detection          = -1 

  def __update_statistics(self, server_received_at, sequence_number_received): 
    if len(self.calculated_timeouts_at) == 0: return

    timeout_at = self.calculated_timeouts_at[-1]

    if timeout_at > server_received_at or math.isclose(timeout_at, server_received_at): 
      self.amount_hits += 1
      return
    
    self.amount_misses += 1
    time_mistake_dict  = {
      "sequence_number": sequence_number_received, 
      "time_taken_to_correct_ns": server_received_at - timeout_at
    }

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

    timeout_at = server_received_at + (self.estimated_rtt + (4 * calculated_phi) * self.deviation_rtt)

    self.calculated_timeouts_at.append(timeout_at)

    if sequence_number_received == BREAK_ON_SEQUENCE_NB: 
      self.time_detection = timeout_at - server_received_at

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
    self.time_detection          = -1

  def __update_statistics(self, server_received_at, sequence_number_received): 
    if len(self.calculated_timeouts_at) == 0: return

    timeout_at = self.calculated_timeouts_at[-1]

    if timeout_at > server_received_at or math.isclose(timeout_at, server_received_at): 
      self.amount_hits += 1
      return
    
    self.amount_misses += 1
    time_mistake_dict  = {
      "sequence_number": sequence_number_received, 
      "time_taken_to_correct_ns": server_received_at - timeout_at
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

    if sequence_number_received == BREAK_ON_SEQUENCE_NB: 
      self.time_detection = timeout_at - server_received_at

jac_timeout_calculator = JacobsonTimeoutCalculator()
tun_phi_calculator     = TuningPhiTimeoutCalculator()
estimated_calculator   = EstimatedTimeoutCalculator()

should_stop = False

for i in range(0, 18): 
  if should_stop: break

  with open(f"./traces_ufpr_ufsm_week_day/raw/log_{i}.txt") as file:
    for x, line in enumerate(file, start=1):
      if x == 1: 
        continue
      
      splitted_line = line.split(';')
      
      server_received_at       = float(splitted_line[SERVER_RECEIVED_AT_INDEX])
      sequence_number_received = int(splitted_line[SEQUENCE_NUMBER_INDEX])

      jac_timeout_calculator.calculate_timeout_at(server_received_at, sequence_number_received)
      tun_phi_calculator.calculate_timeout_at(server_received_at, sequence_number_received)
      estimated_calculator.calculate_timeout_at(server_received_at, sequence_number_received)

      if sequence_number_received == BREAK_ON_SEQUENCE_NB: 
        should_stop = True
        break

add_row_to_csv('csvs/week_day/time_detection/tun_phi_4/jac.csv', sequence_number_received, jac_timeout_calculator.time_detection)
add_row_to_csv('csvs/week_day/time_detection/tun_phi_4/tun_phi.csv', sequence_number_received, tun_phi_calculator.time_detection)
add_row_to_csv('csvs/week_day/time_detection/tun_phi_4/estimated.csv', sequence_number_received, estimated_calculator.time_detection)