import csv
import math
import os
import random
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

# --- Constantes Globais ---

SERVER_RECEIVED_AT_INDEX = 3
SEQUENCE_NUMBER_INDEX    = 4

# --- Funções Utilitárias ---

def save_mistakes_to_csv(filename, data, headers):
  """Salva uma lista de dicionários em um arquivo CSV."""
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

# --- Classes de Cálculo de Timeout (Refatoradas) ---

class BaseTimeoutCalculator:
  """
  Classe base para calcular timeouts. Contém a lógica comum de
  atualização de estatísticas (hits/misses), logging e cálculo
  de RTT estimado e desvio (Jacobson).
  """
  ALPHA = 0.9
  LOCAL_ZONE = ZoneInfo("America/Sao_Paulo")
  UTC_ZONE = ZoneInfo("UTC")

  def __init__(self, name):
    self.name = name
    self.estimated_rtt           = -1
    self.deviation_rtt           = -1
    self.last_server_received_at = -1
    self.amount_misses           = 0
    self.amount_hits             = 0
    self.calculated_timeouts_at  = []
    self.time_mistakes           = []

  @staticmethod
  def _format_time(timestamp_ns):
    """Converte um timestamp em nanossegundos para uma string formatada no fuso local."""
    unix_seconds = timestamp_ns / 1_000_000_000
    utc_time = datetime.fromtimestamp(unix_seconds, tz=BaseTimeoutCalculator.UTC_ZONE)
    local_time = utc_time.astimezone(BaseTimeoutCalculator.LOCAL_ZONE)
    return local_time.strftime('%Y-%m-%d %H:%M:%S %Z')

  def _on_miss(self, timeout_at, server_received_at, sequence_number_received):
    """Lógica base executada quando um timeout é perdido (miss)."""
    time_mistake_dict = {
      "sequence_number": sequence_number_received,
      "time_taken_to_correct_s": (server_received_at - timeout_at) / 1_000_000_000
    }
    self.time_mistakes.append(time_mistake_dict)

    local_time_timeout_at = self._format_time(timeout_at)
    local_time_server_received_at = self._format_time(server_received_at)

    print(
      f"[TIMEOUT - {self.name}] - Expected to receive message of sequence number "
      f"{sequence_number_received} at least until {local_time_timeout_at}, "
      f"but it was received at {local_time_server_received_at}"
    )

  # --- CORREÇÃO: Renomeado de __update_statistics para _update_statistics ---
  def _update_statistics(self, server_received_at, sequence_number_received):
    """Atualiza as estatísticas de acertos (hits) e erros (misses)."""
    if not self.calculated_timeouts_at:
      return
    
    timeout_at = self.calculated_timeouts_at[-1]

    if int(timeout_at) >= server_received_at:
      self.amount_hits += 1
    else:
      self.amount_misses += 1
      # Chama o método _on_miss (que pode ser sobrescrito)
      self._on_miss(timeout_at, server_received_at, sequence_number_received)

  # --- CORREÇÃO: Renomeado de __update_estimated_an_deviation_rtt para _update_estimated_an_deviation_rtt ---
  def _update_estimated_an_deviation_rtt(self, server_received_at):
    """
    Atualiza o RTT estimado e o desvio (algoritmo de Jacobson).
    Esta versão base (para Jacobson e NewRTO) usa uma variável 'interval' local.
    """
    if self.last_server_received_at != -1:
      interval = server_received_at - self.last_server_received_at # 'interval' é local

      if self.estimated_rtt == -1 and self.deviation_rtt == -1:
        self.estimated_rtt = interval
        self.deviation_rtt = 0
      else:
        self.deviation_rtt = self.ALPHA * self.deviation_rtt + (1 - self.ALPHA) * abs(self.estimated_rtt - interval)
        self.estimated_rtt = self.ALPHA * self.estimated_rtt + (1 - self.ALPHA) * interval

  def _calculate_and_store_timeout(self, server_received_at):
    """Método 'template' a ser implementado pelas subclasses."""
    raise NotImplementedError("Subclasses devem implementar este método.")

  def calculate_timeout_at(self, server_received_at, sequence_number_received):
    """Ponto de entrada principal. Executa o template de cálculo."""
    
    # --- CORREÇÃO: Chamadas renomeadas para usar um underscore ---
    self._update_statistics(server_received_at, sequence_number_received)
    self._update_estimated_an_deviation_rtt(server_received_at) # Agora chamará o método correto (com override)

    self.last_server_received_at = server_received_at

    if self.estimated_rtt == -1 and self.deviation_rtt == -1:
      return # Ainda não inicializado

    self._calculate_and_store_timeout(server_received_at)

class JacobsonTimeoutCalculator(BaseTimeoutCalculator):
  """Implementação padrão de Jacobson."""
  PHI = 4.0

  def __init__(self):
    super().__init__("Jacobson")

  def _calculate_and_store_timeout(self, server_received_at):
    timeout_at = server_received_at + (self.estimated_rtt + self.PHI * self.deviation_rtt)
    self.calculated_timeouts_at.append(timeout_at)

class NewRTOTimeoutCalculator(BaseTimeoutCalculator):
  """Implementação de Jacobson com adição de 'mean_mistake'."""
  PHI = 4.0

  def __init__(self):
    super().__init__("NewRTO")
    self.mean_mistake = -1

  def _on_miss(self, timeout_at, server_received_at, sequence_number_received):
    """Sobrescreve _on_miss para calcular o mean_mistake."""
    mistake = server_received_at - timeout_at
    if self.mean_mistake == -1:
      self.mean_mistake = mistake
    else:
      self.mean_mistake = (self.ALPHA * self.mean_mistake) + (1 - self.ALPHA) * mistake
    
    # Chama a implementação base para logging e appen
    super()._on_miss(timeout_at, server_received_at, sequence_number_received)

  def _calculate_and_store_timeout(self, server_received_at):
    timeout_at = server_received_at + (self.estimated_rtt + self.PHI * self.deviation_rtt)
    if self.mean_mistake != -1:
      timeout_at += self.mean_mistake
    self.calculated_timeouts_at.append(timeout_at)

class TrendBasedCalculator(BaseTimeoutCalculator):
  """
  Classe base intermediária para calculadoras que usam análise
  de tendência (Regressão Linear).
  """
  PHI_MAX = 4
  PHI_MIN = 1

  def __init__(self, name):
    super().__init__(name)
    self.time_period             = 0.0
    self.time_period_mul_rtt_sum = 0.0
    self.time_period_sum         = 0.0
    self.rtt_sum                 = 0.0
    self.time_period_squared_sum = 0.0
    self.interval                = -1 # Precisa de 'self.interval'

  # --- CORREÇÃO: Renomeado de __update_estimated_an_deviation_rtt para _update_estimated_an_deviation_rtt ---
  def _update_estimated_an_deviation_rtt(self, server_received_at):
    """
    Sobrescreve o método base para salvar self.interval,
    que é necessário para os cálculos de tendência.
    """
    if self.last_server_received_at != -1:
      # A principal diferença: salva o intervalo como 'self.interval'
      self.interval = server_received_at - self.last_server_received_at # <--- AGORA VAI FUNCIONAR

      if self.estimated_rtt == -1 and self.deviation_rtt == -1:
        self.estimated_rtt = self.interval
        self.deviation_rtt = 0
      else:
        self.deviation_rtt = self.ALPHA * self.deviation_rtt + (1 - self.ALPHA) * abs(self.estimated_rtt - self.interval)
        self.estimated_rtt = self.ALPHA * self.estimated_rtt + (1 - self.ALPHA) * self.interval
    
    # Se self.last_server_received_at == -1, self.interval permanece -1 (correto para a primeira iteração)

  def _calculate_trend(self):
    """
    Calcula e retorna a tendência (trend) usando regressão linear
    nos intervalos de RTT (self.interval).
    """
    self.time_period             += 1.0
    self.time_period_mul_rtt_sum += self.time_period * self.interval
    self.time_period_sum         += self.time_period
    self.rtt_sum                 += self.interval
    self.time_period_squared_sum += self.time_period * self.time_period

    divisor = ((self.time_period * self.time_period_squared_sum) - (self.time_period_sum * self.time_period_sum))
    
    slope_coefficient = -1 # Mantendo a lógica original
    
    if math.isclose(divisor, 0.0):
      slope_coefficient = 0.0
    else:
      slope_coefficient = ((self.time_period * self.time_period_mul_rtt_sum) - (self.time_period_sum * self.rtt_sum)) / float(divisor)

    linear_coefficient = (self.rtt_sum - (slope_coefficient * self.time_period_sum)) / float(self.time_period)
    trend = linear_coefficient + (slope_coefficient * (self.time_period + 1))
    return trend

class TuningPhiTimeoutCalculator(TrendBasedCalculator):
  """Calculadora que ajusta o PHI dinamicamente com base na tendência."""
  
  def __init__(self):
    super().__init__("TuningPhi")

  def _calculate_and_store_timeout(self, server_received_at):
    trend = self._calculate_trend()
    # breakpoint()

    calculated_phi = -1
    if math.isclose(self.deviation_rtt, 0.0):
      calculated_phi = random.randint(self.PHI_MIN, self.PHI_MAX)
    else:
      calculated_phi = math.ceil(abs(((trend + self.deviation_rtt) - self.estimated_rtt) / float(self.deviation_rtt)))

    calculated_phi = max(1.0, calculated_phi)
    calculated_phi = min(4.0, calculated_phi)

    timeout_at = server_received_at + (self.estimated_rtt + calculated_phi * self.deviation_rtt)
    self.calculated_timeouts_at.append(timeout_at)

class EstimatedTimeoutCalculator(TrendBasedCalculator):
  """Calculadora que usa a tendência (trend) diretamente como timeout."""
  
  def __init__(self):
    super().__init__("Estimated")

  def _calculate_and_store_timeout(self, server_received_at):
    trend = self._calculate_trend()
    timeout_at = server_received_at + trend
    self.calculated_timeouts_at.append(timeout_at)

# --- Lógica Principal do Script ---

def main():
  """Função principal para executar o processamento do trace."""
  
  # --- 1. Parseamento de Argumentos ---
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
  phi_multiplier_value = 1  # Valor padrão original
  
  if len(sys.argv) == 4:
    optional_param = sys.argv[3]
    if optional_param == 'tun_phi_2':
      phi_type = 'tun_phi_2'
      phi_multiplier_value = 2
    elif optional_param == 'tun_phi_4':
      phi_type = 'tun_phi_4'
      phi_multiplier_value = 4
    else:
      print("Aviso: O terceiro parâmetro opcional é inválido. Usando o valor padrão 'tun_phi_normal'.")
  
  # --- 2. Instanciação dos Calculadores ---
  
  # Usar um dicionário simplifica o processamento e salvamento
  calculators = {
    "jac": JacobsonTimeoutCalculator(),
    "tun_phi": TuningPhiTimeoutCalculator(),
    "estimated": EstimatedTimeoutCalculator(),
    "new_rto": NewRTOTimeoutCalculator()
  }
  
  # --- 3. Processamento do Arquivo de Trace ---
  trace_directory = f"./traces_{trace_source}_{day_type}/raw"
  
  # O loop original ia de 0 a 1 (só processava log_0.txt). Mantido.
  for i in range(0, 1):
    file_path = os.path.join(trace_directory, f"log_{i}.txt")
    
    if not os.path.exists(file_path):
      print(f"Erro: Arquivo de trace não encontrado em '{file_path}'")
      continue

    print(f"Processando arquivo: {file_path}")
    with open(file_path, 'r', encoding='utf-8') as file:
      for x, line in enumerate(file, start=1):
        if x == 1:  # Pula o cabeçalho
          continue

        try:
          splitted_line = line.strip().split(';')
          server_received_at = int(splitted_line[SERVER_RECEIVED_AT_INDEX])
          sequence_number_received = int(splitted_line[SEQUENCE_NUMBER_INDEX])
          
          # Itera sobre todos os calculadores de forma limpa
          for calculator in calculators.values():
            calculator.calculate_timeout_at(server_received_at, sequence_number_received)
            
        except (IndexError, ValueError) as e:
          print(f"Erro ao processar linha {x}: {line.strip()} | Erro: {e}")
        except Exception as e:
          print(f"Erro inesperado na linha {x}: {e}")

  # --- 4. Salvamento dos Resultados ---
  csv_output_dir = f'csvs/{trace_source}/{day_type}/time_mistake/{phi_type}'
  os.makedirs(csv_output_dir, exist_ok=True)
  
  column_headers = ['sequence_number', 'time_taken_to_correct_s']

  # Itera sobre o dicionário para salvar cada CSV
  for name, calculator in calculators.items():
    csv_filename = os.path.join(csv_output_dir, f'{name}.csv')
    save_mistakes_to_csv(csv_filename, calculator.time_mistakes, column_headers)

if __name__ == "__main__":
  main()