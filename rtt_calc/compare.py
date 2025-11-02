import sys
import math
from abc import ABC, abstractmethod
from typing import List, Tuple

class BaseTimeoutCalculator(ABC):
  
  ALPHA = 0.9
  INITIAL_RTT = -1.0
  INITIAL_DEV = -1.0
  
  def __init__(self, name: str, *args, **kwargs):
    super().__init__(*args, **kwargs)
    self.name = name
    self.estimated_rtt = self.INITIAL_RTT
    self.deviation_rtt = self.INITIAL_DEV
    self.amount_hits = 0
    self.amount_misses = 0
    self.timeouts_over_time: List[float] = []

  def _update_rtt_estimates(self, current_rtt: float):
    if self.estimated_rtt == self.INITIAL_RTT:
      self.estimated_rtt = current_rtt
      self.deviation_rtt = 0.0
    else:
      self.deviation_rtt = (self.ALPHA * self.deviation_rtt) + \
                           (1 - self.ALPHA) * abs(self.estimated_rtt - current_rtt)
      self.estimated_rtt = (self.ALPHA * self.estimated_rtt) + \
                           (1 - self.ALPHA) * current_rtt
  
  def _update_statistics(self, current_rtt: float):
    if not self.timeouts_over_time:
      return

    last_timeout = self.timeouts_over_time[-1]
    
    if last_timeout > current_rtt or math.isclose(last_timeout, current_rtt): 
      self.amount_hits += 1
    else:
      self.amount_misses += 1

  def print_statistics(self):
    print(f"Estatísticas de {self.name}:")
    print(f"\t--> Acertos (Hits):   #{self.amount_hits}")
    print(f"\t--> Erros (Misses): #{self.amount_misses}\n")
  
  @abstractmethod
  def calculate_timeout(self, current_rtt: float):
    pass

class _TrendCalculatorMixin(object):
  def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs) 
    self.time_period = 0.0
    self.time_period_mul_rtt_sum = 0.0
    self.time_period_sum = 0.0
    self.rtt_sum = 0.0 
    self.time_period_squared_sum = 0.0

  def _calculate_trend(self, current_rtt: float) -> float:
    self.time_period += 1.0
    self.time_period_mul_rtt_sum += self.time_period * current_rtt
    self.time_period_sum += self.time_period
    self.rtt_sum += current_rtt
    self.time_period_squared_sum += self.time_period * self.time_period

    divisor = (self.time_period * self.time_period_squared_sum) - \
              (self.time_period_sum * self.time_period_sum)
    
    slope_coefficient = 0.0
    if not math.isclose(divisor, 0.0): 
      slope_coefficient = ((self.time_period * self.time_period_mul_rtt_sum) - 
                           (self.time_period_sum * self.rtt_sum)) / float(divisor)

    linear_coefficient = (self.rtt_sum - (slope_coefficient * self.time_period_sum)) / \
                         float(self.time_period)
    
    trend = linear_coefficient + (slope_coefficient * (self.time_period + 1))
    return trend

class JacobsonTimeoutCalculator(BaseTimeoutCalculator):
  PHI = 4.0

  def __init__(self, *args, **kwargs):
    super().__init__(name="Jacobson", *args, **kwargs)
  
  def calculate_timeout(self, current_rtt: float):
    self._update_statistics(current_rtt)
    self._update_rtt_estimates(current_rtt)
    
    timeout = self.estimated_rtt + self.PHI * self.deviation_rtt
    self.timeouts_over_time.append(timeout)

class RTOTimeoutCalculator(BaseTimeoutCalculator):
  PHI = 4.0
  INITIAL_MISTAKE = -1.0

  def __init__(self, *args, **kwargs):
    if 'name' not in kwargs:
      kwargs['name'] = "NOVO RTO"
        
    super().__init__(kwargs.pop('name'), *args, **kwargs)
    
    self.mean_mistake = self.INITIAL_MISTAKE
  
  def _update_statistics(self, current_rtt: float):
    if not self.timeouts_over_time:
      return

    last_timeout = self.timeouts_over_time[-1]
    if last_timeout > current_rtt or math.isclose(last_timeout, current_rtt): 
      self.amount_hits += 1
    else:
      self.amount_misses += 1
      mistake = current_rtt - last_timeout
      
      if self.mean_mistake == self.INITIAL_MISTAKE:
        self.mean_mistake = mistake
      else: 
        self.mean_mistake = (self.ALPHA * self.mean_mistake) + \
                            (1 - self.ALPHA) * mistake

  def calculate_timeout(self, current_rtt: float):
    self._update_statistics(current_rtt)
    self._update_rtt_estimates(current_rtt)

    timeout = self.estimated_rtt + self.PHI * self.deviation_rtt
    
    if self.mean_mistake != self.INITIAL_MISTAKE: 
      timeout += self.mean_mistake

    self.timeouts_over_time.append(timeout)
      
class TuningPhiTimeoutCalculator(RTOTimeoutCalculator, _TrendCalculatorMixin): 
  START_PHI = 4.0

  def __init__(self, *args, **kwargs):
    super().__init__(name="Tuning Phi", *args, **kwargs)

  def calculate_timeout(self, current_rtt: float):
    self._update_statistics(current_rtt) 
    self._update_rtt_estimates(current_rtt) 
  
    trend = self._calculate_trend(current_rtt) 

    calculated_phi = 0.0
    if math.isclose(self.deviation_rtt, 0.0):
      calculated_phi = self.START_PHI
    else:
      phi_float = abs(((trend + self.deviation_rtt) - self.estimated_rtt) / \
                      float(self.deviation_rtt))
      calculated_phi = math.ceil(phi_float) 

    calculated_phi = max(1.0, calculated_phi)
    calculated_phi = min(4.0, calculated_phi)

    timeout = self.estimated_rtt + calculated_phi * self.deviation_rtt
    self.timeouts_over_time.append(timeout)

class EstimatedTimeoutCalculator(BaseTimeoutCalculator, _TrendCalculatorMixin): 
  def __init__(self, *args, **kwargs):
    super().__init__(name="Estimado", *args, **kwargs)

  def calculate_timeout(self, current_rtt: float):
    self._update_statistics(current_rtt)
    
    trend = self._calculate_trend(current_rtt)
    self.timeouts_over_time.append(trend)

def read_rtt_data(filename: str) -> Tuple[List[int], List[float]]:
  times: List[int] = []
  rtts: List[float] = []
  
  try:
    with open(filename) as file: 
      for i, line in enumerate(file, start=1): 
        try:
          current_rtt = float(line.strip())
          times.append(i)
          rtts.append(current_rtt)
        except ValueError: 
          print(f"Erro: linha {i} não contém um número válido: {line.strip()}")
          sys.exit(1)
  except FileNotFoundError:
    print(f"Erro: Arquivo '{filename}' não encontrado.")
    sys.exit(1)
      
  return times, rtts

def main():  
  if len(sys.argv) < 2:
    print(f"Erro: Forneça o caminho do arquivo de dados como argumento.")
    print(f"Uso: python {sys.argv[0]} <caminho_para_o_arquivo>")
    sys.exit(1)
      
  input_filename = sys.argv[1]
  
  times, rtts = read_rtt_data(input_filename)
  
  if not rtts:
    print(f"Arquivo '{input_filename}' está vazio ou não pôde ser lido.")
    return

  calculators = [
    JacobsonTimeoutCalculator(),
    TuningPhiTimeoutCalculator(),
    RTOTimeoutCalculator(),
    EstimatedTimeoutCalculator()
  ]
  
  for rtt in rtts:
    for calc in calculators:
      calc.calculate_timeout(rtt)
  
  jac_calc = calculators[0]
  tun_phi_calc = calculators[1]
  rto_calc = calculators[2]

  print("Resultados por medição (RTT | Jacobson | Tuning Phi | Novo RTO):")
  
  print(f'RTT: {rtts[0]:>6.2f} | TIMEOUT JAC: {"-":>11} | TIMEOUT Tun Phi: {"-":>15} | TIMEOUT Novo RTO: {"-":>14}')
  
  for x in range(1, len(rtts)):
    print(f'RTT: {rtts[x]:>6.2f} | '
          f'TIMEOUT JAC: {jac_calc.timeouts_over_time[x - 1]:>11.2f} | '
          f'TIMEOUT Tun Phi: {tun_phi_calc.timeouts_over_time[x - 1]:>15.2f} | '
          f'TIMEOUT Novo RTO: {rto_calc.timeouts_over_time[x - 1]:>14.2f}')

  print("\n" + "="*30 + " Estatísticas Finais " + "="*30 + "\n")

  for calc in calculators:
    calc.print_statistics()

if __name__ == "__main__":
  main()