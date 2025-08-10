import sys
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import math

class JacobsonTimeoutCalculator:
  ALPHA = 0.9
  PHI   = 4.0

  def __init__(self):
    self.estimated_rtt      = -1
    self.deviation_rtt      = -1
    self.amount_hits        = 0
    self.amount_misses      = 0
    self.timeouts_over_time = []
  
  def __update_estimated_an_deviation_rtt(self, current_rtt): 
    if self.estimated_rtt == -1 and self.deviation_rtt == -1: 
      self.estimated_rtt = current_rtt
      self.deviation_rtt = 0
    else:
      self.deviation_rtt = self.ALPHA * self.deviation_rtt + (1 - self.ALPHA) * abs(self.estimated_rtt - current_rtt)
      self.estimated_rtt = self.ALPHA * self.estimated_rtt + (1 - self.ALPHA) * current_rtt

  def __update_statistics(self, current_rtt): 
    if len(self.timeouts_over_time) == 0: return

    last_timeout = self.timeouts_over_time[-1]
    if last_timeout > current_rtt or math.isclose(last_timeout, current_rtt): 
      self.amount_hits += 1
    else:
      self.amount_misses += 1
  
  def print_statistics(self):
    print("Jacobson statistics:")
    print(f"\t--> Amount of Hits: #{self.amount_hits}")
    print(f"\t--> Amount of Misses: #{self.amount_misses}\n")
    
  def calculate_timeout(self, current_rtt):
    self.__update_statistics(current_rtt)
    self.__update_estimated_an_deviation_rtt(current_rtt)
    self.timeouts_over_time.append(self.estimated_rtt + self.PHI * self.deviation_rtt)
      
class TuningPhiTimeoutCalculator: 
  ALPHA     = 0.9
  START_PHI = 4.0

  def __init__(self):
    self.time_period             = 0.0
    self.time_period_mul_rtt_sum = 0.0
    self.time_period_sum         = 0.0
    self.rtt_sum                 = 0.0 
    self.time_period_squared_sum = 0.0
    self.estimated_rtt           = -1
    self.deviation_rtt           = -1
    self.amount_hits             = 0
    self.amount_misses           = 0
    self.timeouts_over_time      = []
  
  def __update_estimated_an_deviation_rtt(self, current_rtt): 
    if self.estimated_rtt == -1 and self.deviation_rtt == -1: 
      self.estimated_rtt = current_rtt
      self.deviation_rtt = 0
    else:
      self.deviation_rtt = self.ALPHA * self.deviation_rtt + (1 - self.ALPHA) * abs(self.estimated_rtt - current_rtt)
      self.estimated_rtt = self.ALPHA * self.estimated_rtt + (1 - self.ALPHA) * current_rtt
  
  def __update_statistics(self, current_rtt): 
    if len(self.timeouts_over_time) == 0: return

    last_timeout = self.timeouts_over_time[-1]
    if last_timeout > current_rtt or math.isclose(last_timeout, current_rtt): 
      self.amount_hits += 1
    else:
      self.amount_misses += 1
  
  def print_statistics(self):
    print("Tuning Phi statistics:")
    print(f"\t--> Amount of Hits: #{self.amount_hits}")
    print(f"\t--> Amount of Misses: #{self.amount_misses}\n")
  
  def calculate_timeout(self, current_rtt):
    self.__update_statistics(current_rtt)
    self.__update_estimated_an_deviation_rtt(current_rtt)

    self.time_period             += 1.0
    self.time_period_mul_rtt_sum += self.time_period * current_rtt
    self.time_period_sum         += self.time_period
    self.rtt_sum                 += current_rtt
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
      calculated_phi = self.START_PHI
    else:
      calculated_phi = math.ceil(abs(((trend + self.deviation_rtt) - self.estimated_rtt) / float(self.deviation_rtt)))

    self.timeouts_over_time.append(self.estimated_rtt + calculated_phi * self.deviation_rtt)

class TuningPhiV2TimeoutCalculator: 
  ALPHA     = 0.9

  def __init__(self):
    self.time_period             = 0.0
    self.time_period_mul_rtt_sum = 0.0
    self.time_period_sum         = 0.0
    self.rtt_sum                 = 0.0 
    self.time_period_squared_sum = 0.0
    self.amount_hits             = 0
    self.amount_misses           = 0
    self.timeouts_over_time      = []
  
  def __update_statistics(self, current_rtt): 
    if len(self.timeouts_over_time) == 0: return

    last_timeout = self.timeouts_over_time[-1]
    if last_timeout > current_rtt or math.isclose(last_timeout, current_rtt): 
      self.amount_hits += 1
    else:
      self.amount_misses += 1
  
  def print_statistics(self):
    print("Tuning Phi V2 statistics:")
    print(f"\t--> Amount of Hits: #{self.amount_hits}")
    print(f"\t--> Amount of Misses: #{self.amount_misses}\n")
  
  def calculate_timeout(self, current_rtt):
    self.__update_statistics(current_rtt)

    self.time_period             += 1.0
    self.time_period_mul_rtt_sum += self.time_period * current_rtt
    self.time_period_sum         += self.time_period
    self.rtt_sum                 += current_rtt
    self.time_period_squared_sum += self.time_period * self.time_period

    divisor = ((self.time_period * self.time_period_squared_sum) - (self.time_period_sum * self.time_period_sum))
    slope_coefficient = -1
    if math.isclose(divisor, 0.0): 
      slope_coefficient = 0.0
    else:
      slope_coefficient = ((self.time_period * self.time_period_mul_rtt_sum) - (self.time_period_sum * self.rtt_sum)) / float(divisor)

    linear_coefficient = (self.rtt_sum - (slope_coefficient * self.time_period_sum)) / float(self.time_period)
    trend              = linear_coefficient + (slope_coefficient * (self.time_period + 1))

    self.timeouts_over_time.append(trend)

jac_timeout_calculator        = JacobsonTimeoutCalculator()
tun_phi_timeout_calculator    = TuningPhiTimeoutCalculator()
tun_phi_v2_timeout_calculator = TuningPhiV2TimeoutCalculator()
times                         = []
rtts                          = []

with open("./data.txt") as file: 
  for i, line in enumerate(file, start=1): 
    try:
      current_rtt = float(line.strip())
      times.append(i)
      rtts.append(current_rtt)

      jac_timeout_calculator.calculate_timeout(current_rtt)
      tun_phi_timeout_calculator.calculate_timeout(current_rtt)
      tun_phi_v2_timeout_calculator.calculate_timeout(current_rtt)
    except ValueError: 
      print(f"Erro: linha {i} não contém um número válido: {line.strip()}")
      sys.exit(1)

jac_timeout_calculator.print_statistics()
tun_phi_timeout_calculator.print_statistics()
tun_phi_v2_timeout_calculator.print_statistics()

plt.plot(times, rtts, marker='o', linestyle='--', color='b', label='Actual Rtt')
plt.plot([t + 1 for t in times], jac_timeout_calculator.timeouts_over_time, marker='s', linestyle='-', color='g', label='Timeout by Jac')
plt.plot([t + 1 for t in times], tun_phi_timeout_calculator.timeouts_over_time, marker='^', linestyle=':', color='r', label='Timeout By Tun Phi')
plt.plot([t + 1 for t in times], tun_phi_v2_timeout_calculator.timeouts_over_time, marker='d', linestyle='-.', color='m', label='Timeout By Tun Phi V2')

plt.title("Jacobson X Tuning PHI X Tuning PHI V2")
plt.xlabel("Time")
plt.ylabel("Rtt")

ax = plt.gca() 
ax.xaxis.set_major_locator(ticker.MaxNLocator(integer=True))

plt.grid(True)
plt.legend()
plt.show()

