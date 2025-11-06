import math
from datetime import datetime
from zoneinfo import ZoneInfo
import random
import csv
import sys
import os

# --- Constantes Globais ---
SERVER_RECEIVED_AT_INDEX = 3
SEQUENCE_NUMBER_INDEX    = 4

# --- Funções Utilitárias ---

def add_row_to_csv(file_path, sequence_number, time_to_detect_ns):
  """
  Adiciona uma ÚNICA linha a um arquivo CSV, criando-o se não existir.
  """
  headers = ['sequence_number', 'time_to_detect_ms']
  
  # Lógica para tratar caso 'time_to_detect_ns' seja inválido (ex: -1)
  time_ms = 'N/A'
  if time_to_detect_ns is not None and time_to_detect_ns >= 0:
    time_ms = time_to_detect_ns / 1_000_000
  
  new_row = {
    'sequence_number': sequence_number,
    'time_to_detect_ms': time_ms
  }
  
  # Garante que o diretório exista
  try:
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
  except OSError as e:
    print(f"Erro ao criar diretório para '{file_path}': {e}")
    return

  # Verifica se o arquivo é novo para adicionar cabeçalhos
  file_exists = os.path.isfile(file_path)

  try:
    with open(file_path, 'a', newline='') as csvfile:
      writer = csv.DictWriter(csvfile, fieldnames=headers)
      
      if not file_exists:
        writer.writeheader() # Escreve o cabeçalho se for um arquivo novo
    
      writer.writerow(new_row)
      print(f"Successfully added row to '{file_path}': {new_row}")

  except IOError as e:
    print(f"I/O Error: Could not write to file '{file_path}'. Details: {e}")
  except Exception as e:
    print(f"An unexpected error occurred: {e}")

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
    self.time_detection          = -1 # Valor padrão

  @staticmethod
  def _format_time(timestamp_ns):
    """Converte um timestamp em nanossegundos para uma string formatada no fuso local."""
    try:
      unix_seconds = timestamp_ns / 1_000_000_000
      utc_time = datetime.fromtimestamp(unix_seconds, tz=BaseTimeoutCalculator.UTC_ZONE)
      local_time = utc_time.astimezone(BaseTimeoutCalculator.LOCAL_ZONE)
      return local_time.strftime('%Y-%m-%d %H:%M:%S %Z')
    except Exception:
      return f"[Timestamp Inválido: {timestamp_ns}]"

  def _on_miss(self, timeout_at, server_received_at, sequence_number_received):
    """Lógica base executada quando um timeout é perdido (miss)."""
    time_mistake_dict = {
      "sequence_number": sequence_number_received,
      "time_taken_to_correct_ns": server_received_at - timeout_at
    }
    self.time_mistakes.append(time_mistake_dict)
    
    local_time_timeout_at = self._format_time(timeout_at)
    local_time_server_received_at = self._format_time(server_received_at)

    return

    print(
      f"[TIMEOUT - {self.name}] - Expected to receive message of sequence number "
      f"{sequence_number_received} at least until {local_time_timeout_at}, "
      f"but it was received at {local_time_server_received_at}"
    )

  def _update_statistics(self, server_received_at, sequence_number_received):
    """Atualiza as estatísticas de acertos (hits) e erros (misses)."""
    if not self.calculated_timeouts_at:
      return
    
    timeout_at = self.calculated_timeouts_at[-1]

    if int(timeout_at) >= server_received_at:
      self.amount_hits += 1
    else:
      self.amount_misses += 1
      self._on_miss(timeout_at, server_received_at, sequence_number_received)

  def _update_estimated_an_deviation_rtt(self, server_received_at):
    """
    Atualiza o RTT estimado e o desvio (algoritmo de Jacobson).
    """
    if self.last_server_received_at != -1:
      interval = server_received_at - self.last_server_received_at

      if self.estimated_rtt == -1 and self.deviation_rtt == -1:
        self.estimated_rtt = interval
        self.deviation_rtt = 0
      else:
        self.deviation_rtt = self.ALPHA * self.deviation_rtt + (1 - self.ALPHA) * abs(self.estimated_rtt - interval)
        self.estimated_rtt = self.ALPHA * self.estimated_rtt + (1 - self.ALPHA) * interval

  def _calculate_timeout_at_impl(self, server_received_at):
    """Método 'template' a ser implementado pelas subclasses."""
    raise NotImplementedError("Subclasses devem implementar este método.")

  def calculate_timeout_at(self, server_received_at, sequence_number_received, break_on_sequence_nb):
    """Ponto de entrada principal. Executa o template de cálculo."""
    self._update_statistics(server_received_at, sequence_number_received)
    self._update_estimated_an_deviation_rtt(server_received_at) 

    self.last_server_received_at = server_received_at

    if self.estimated_rtt == -1 and self.deviation_rtt == -1:
      return # Ainda não inicializado

    timeout_at = self._calculate_timeout_at_impl(server_received_at)
    
    if timeout_at is not None:
      self.calculated_timeouts_at.append(timeout_at)

      # Lógica de detecção do tempo de parada
      if sequence_number_received == break_on_sequence_nb:
        self.time_detection = timeout_at - server_received_at

class JacobsonTimeoutCalculator(BaseTimeoutCalculator):
  """Implementação padrão de Jacobson."""
  PHI = 4.0

  def __init__(self):
    super().__init__("Jacobson")

  def _calculate_timeout_at_impl(self, server_received_at):
    return server_received_at + (self.estimated_rtt + self.PHI * self.deviation_rtt)

class NewRTOTimeoutCalculator(BaseTimeoutCalculator):
  """
  Implementação de Jacobson com adição de 'mean_mistake'.
  (Análogo ao 'NewRTO' do script de exemplo).
  """
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
    
    # Chama a implementação base para logging e append
    super()._on_miss(timeout_at, server_received_at, sequence_number_received)

  def _calculate_timeout_at_impl(self, server_received_at):
    timeout_at = server_received_at + (self.estimated_rtt + self.PHI * self.deviation_rtt)
    if self.mean_mistake != -1:
      timeout_at += self.mean_mistake
    return timeout_at

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
    self.interval                = -1

  def _update_estimated_an_deviation_rtt(self, server_received_at):
    """
    Sobrescreve o método base para salvar 'self.interval',
    que é necessário para os cálculos de tendência.
    """
    if self.last_server_received_at != -1:
      self.interval = server_received_at - self.last_server_received_at 

      if self.estimated_rtt == -1 and self.deviation_rtt == -1:
        self.estimated_rtt = self.interval
        self.deviation_rtt = 0
      else:
        self.deviation_rtt = self.ALPHA * self.deviation_rtt + (1 - self.ALPHA) * abs(self.estimated_rtt - self.interval)
        self.estimated_rtt = self.ALPHA * self.estimated_rtt + (1 - self.ALPHA) * self.interval
    
  def _calculate_trend(self):
    """
    Calcula e retorna a tendência (trend) usando regressão linear
    nos intervalos de RTT (self.interval).
    """
    if self.interval == -1:
      return 0.0 

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

    # Evita divisão por zero se time_period for 0
    if math.isclose(self.time_period, 0.0):
      linear_coefficient = 0.0
    else:
      linear_coefficient = (self.rtt_sum - (slope_coefficient * self.time_period_sum)) / float(self.time_period)
        
    trend = linear_coefficient + (slope_coefficient * (self.time_period + 1))
    return trend

class TuningPhiTimeoutCalculator(TrendBasedCalculator):
  """
  Calculadora que ajusta o PHI dinamicamente (baseado no script original)
  e também adiciona um 'mean_mistake'.
  """
  # Multiplicador PHI fixado em 1 (comportamento padrão original)
  PHI_MULTIPLIER = 1

  def __init__(self):
    super().__init__("TuningPhi")
    self.mean_mistake = -1

  def _calculate_timeout_at_impl(self, server_received_at):
    trend = self._calculate_trend()

    calculated_phi = -1
    if math.isclose(self.deviation_rtt, 0.0):
      calculated_phi = random.randint(self.PHI_MIN, self.PHI_MAX)
    else:
      calculated_phi = math.ceil(abs(((trend + self.deviation_rtt) - self.estimated_rtt) / float(self.deviation_rtt)))

    calculated_phi = max(1.0, calculated_phi)
    calculated_phi = min(4.0, calculated_phi)

    timeout_at = server_received_at + (self.estimated_rtt + (self.PHI_MULTIPLIER * calculated_phi) * self.deviation_rtt)
      
    return timeout_at

class EstimatedTimeoutCalculator(TrendBasedCalculator):
  """Calculadora que usa a tendência (trend) diretamente como timeout."""
  
  def __init__(self):
    super().__init__("Estimated")

  def _calculate_timeout_at_impl(self, server_received_at):
    trend = self._calculate_trend()
    return server_received_at + trend

# --- Lógica Principal do Script ---

def main():
  """Função principal para executar o processamento do trace."""
  
  # --- 1. Parseamento de Argumentos (Refatorado) ---
  # Agora espera 3 argumentos no total (nome_script, seq_nb, input_dir)
  if len(sys.argv) != 3:
    print("Uso: python seu_script.py <BREAK_ON_SEQUENCE_NB> <diretorio_de_entrada>")
    print("Exemplo: python seu_script.py 1000 ./traces_ufpr_sydney_week_day/raw")
    sys.exit(1)

  try:
    BREAK_ON_SEQUENCE_NB = int(sys.argv[1])
  except ValueError:
    print(f"Erro: O argumento <BREAK_ON_SEQUENCE_NB> ('{sys.argv[1]}') não é um número inteiro.")
    sys.exit(1)

  input_directory = sys.argv[2]
  
  if not os.path.isdir(input_directory):
    print(f"Erro: O diretório de entrada não foi encontrado: '{input_directory}'")
    sys.exit(1)

  # --- Diretório de saída derivado do de entrada ---
  # Constrói o caminho: {input_directory}/../csvs/time_detection
  output_csv_directory = os.path.normpath(
    os.path.join(input_directory, '..', 'csvs', 'time_detection')
  )
  
  print(f"Iniciando processamento.")
  print(f"Parar no N. de Sequência: {BREAK_ON_SEQUENCE_NB}")
  print(f"Lendo de: {input_directory}")
  print(f"Salvando CSVs em: {output_csv_directory}") # <-- Caminho agora é calculado

  # --- 2. Instanciação dos Calculadores ---
  
  calculators = {
    "jac": JacobsonTimeoutCalculator(),
    "tun_phi": TuningPhiTimeoutCalculator(),
    "estimated": EstimatedTimeoutCalculator(),
    "new_rto": NewRTOTimeoutCalculator()
  }
  
  # --- 3. Processamento do Arquivo de Trace ---
  
  should_stop = False
  sequence_number_reached = -1 # Guarda o número de seq. para salvar no CSV

  # Loop fixo de 0 a 17 (arquivos log_0.txt a log_17.txt)
  for i in range(0, 18): 
    if should_stop: break
    
    file_path = os.path.join(input_directory, f"log_{i}.txt")
    if not os.path.exists(file_path):
      print(f"Aviso: Arquivo não encontrado '{file_path}', pulando.")
      continue
    
    print(f"Processando arquivo: {file_path}")
    with open(file_path, 'r', encoding='utf-8') as file:
      for x, line in enumerate(file, start=1):
        if x == 1: # Pula cabeçalho
          continue
        
        try:
          splitted_line = line.strip().split(';')
          if len(splitted_line) <= max(SERVER_RECEIVED_AT_INDEX, SEQUENCE_NUMBER_INDEX):
            continue # Linha mal formada
              
          server_received_at = int(splitted_line[SERVER_RECEIVED_AT_INDEX])
          sequence_number_received = int(splitted_line[SEQUENCE_NUMBER_INDEX])

          for calculator in calculators.values():
            calculator.calculate_timeout_at(server_received_at, sequence_number_received, BREAK_ON_SEQUENCE_NB)

          if sequence_number_received == BREAK_ON_SEQUENCE_NB: 
            should_stop = True
            sequence_number_reached = sequence_number_received
            print(f"--- BREAK_ON_SEQUENCE_NB ({BREAK_ON_SEQUENCE_NB}) encontrado. ---")
            break
            
        except (IndexError, ValueError) as e:
          print(f"Erro ao processar linha {x}: {line.strip()} | Erro: {e}")
        except Exception as e:
          print(f"Erro inesperado na linha {x}: {e}")

  # --- 4. Salvamento dos Resultados ---
  
  if not should_stop:
    print(f"Aviso: BREAK_ON_SEQUENCE_NB ({BREAK_ON_SEQUENCE_NB}) não foi encontrado nos traces.")
  elif sequence_number_reached != -1:
    print("Salvando resultados do time_detection...")
    
    for name, calculator in calculators.items():
      csv_path = os.path.join(output_csv_directory, f'{name}.csv')
      add_row_to_csv(csv_path, sequence_number_reached, calculator.time_detection)
  
  print("Processamento concluído.")

if __name__ == "__main__":
  main()