import math
from datetime import datetime
from zoneinfo import ZoneInfo
import random


SERVER_RECEIVED_AT_INDEX = 3
SEQUENCE_NUMBER_INDEX    = 4

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

    timeout_at = server_received_at + (self.estimated_rtt + calculated_phi * self.deviation_rtt)

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

jac_timeout_calculator = JacobsonTimeoutCalculator()
tun_phi_calculator     = TuningPhiTimeoutCalculator()
estimated_calculator   = EstimatedTimeoutCalculator()

for i in range(0, 18): 
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

print(jac_timeout_calculator.time_mistakes)
print(tun_phi_calculator.time_mistakes)
print(estimated_calculator.time_mistakes)
