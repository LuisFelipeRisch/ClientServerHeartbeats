import os
import pandas as pd

def calcular_estatisticas(df, coluna_alvo, filename):
  """Calcula um conjunto de estatísticas para uma coluna do DataFrame."""
  try:
    if df.empty:
      return f"Arquivo: {filename}\n  AVISO: CSV vazio.\n"
      
    if coluna_alvo not in df.columns:
      return f"Arquivo: {filename}\n  ERRO: Coluna '{coluna_alvo}' não encontrada.\n"

    # Cálculos
    coluna_dados = df[coluna_alvo]
    media = coluna_dados.mean()
    desvio_padrao = coluna_dados.std()
    qtd_linhas = len(df)
    mediana = coluna_dados.median()
    
    # --- NOVO: Max e Min ---
    valor_max = coluna_dados.max()
    valor_min = coluna_dados.min()
    # --- FIM NOVO ---
    
    # IQR (Intervalo Interquartil)
    q1 = coluna_dados.quantile(0.25)
    q3 = coluna_dados.quantile(0.75)
    iqr = q3 - q1
    
    # Moda
    modas = coluna_dados.mode()
    if modas.empty:
      moda_str = "N/A (nenhuma)"
    else:
      # Converte todas as modas para string e as une com vírgula
      moda_str = ", ".join(modas.astype(str).values)

    # Formata a string de saída
    linha_stats = (
      f"Arquivo: {filename}\n"
      f"  Coluna: {coluna_alvo}\n"
      f"  Quantidade de Linhas (dados): {qtd_linhas}\n"
      f"  Média: {media}\n"
      f"  Mediana: {mediana}\n"
      f"  Moda(s): {moda_str}\n"
      f"  Desvio Padrão: {desvio_padrao}\n"
      f"  Máximo: {valor_max}\n"   # <-- ADICIONADO
      f"  Mínimo: {valor_min}\n"   # <-- ADICIONADO
      f"  Intervalo Interquartil (IQR): {iqr} (Q1: {q1}, Q3: {q3})\n"
    )
    return linha_stats
    
  except Exception as e:
    # Captura de erro específica para este CSV
    return f"Arquivo: {filename}\n  ERRO INESPERADO no cálculo: {e}\n"

def processar_diretorios(root_dir='traces'):
  """
  Percorre o diretório 'traces' e calcula estatísticas para os CSVs
  encontrados em 'time_detection' e 'time_mistake'.
  """
  print(f"Iniciando varredura no diretório: {root_dir}")
  
  # os.walk percorre a árvore de diretórios de cima para baixo
  for dirpath, dirnames, filenames in os.walk(root_dir):
    
    # Pega o nome final do diretório atual (ex: 'time_detection')
    current_dir_name = os.path.basename(dirpath)
    
    # Listas para guardar as estatísticas de todos os CSVs neste diretório
    stats_para_salvar = []
    
    # --- Lógica para 'time_detection' ---
    if current_dir_name == 'time_detection':
      print(f"\n--- Processando Diretório [DETECTION]: {dirpath}")
      coluna_alvo = 'time_to_detect_ms'
      
      for filename in filenames:
        if filename.endswith('.csv'):
          csv_path = os.path.join(dirpath, filename)
          try:
            df = pd.read_csv(csv_path)
            
            # NOVO: Chama a função de cálculo unificada
            estatisticas_str = calcular_estatisticas(df, coluna_alvo, filename)
            stats_para_salvar.append(estatisticas_str)
              
          except Exception as e:
            # Este 'except' agora pega erros ao LER o CSV
            print(f"  [ERRO] Falha ao LER {filename}: {e}")
            stats_para_salvar.append(f"Arquivo: {filename}\n  ERRO AO LER: {e}\n")

    # --- Lógica para 'time_mistake' ---
    elif current_dir_name == 'time_mistake':
      print(f"\n--- Processando Diretório [MISTAKE]: {dirpath}")
      coluna_alvo = 'time_taken_to_correct_ms'
      
      for filename in filenames:
        if filename.endswith('.csv'):
          csv_path = os.path.join(dirpath, filename)
          try:
            df = pd.read_csv(csv_path)
            
            # NOVO: Chama a função de cálculo unificada
            estatisticas_str = calcular_estatisticas(df, coluna_alvo, filename)
            stats_para_salvar.append(estatisticas_str)
              
          except Exception as e:
            # Este 'except' agora pega erros ao LER o CSV
            print(f"  [ERRO] Falha ao LER {filename}: {e}")
            stats_para_salvar.append(f"Arquivo: {filename}\n  ERRO AO LER: {e}\n")

    # --- Salvando o arquivo de estatísticas ---
    if stats_para_salvar:
      # --- NOVO: Lógica para extrair Metadados ---
      try:
        # Pega o caminho relativo (ex: "trace_01/csvs/time_detection")
        rel_path = os.path.relpath(dirpath, root_dir)
        # Divide o caminho (ex: ["trace_01", "csvs", "time_detection"])
        path_parts = rel_path.split(os.path.sep)
        
        # O nome do trace é a primeira pasta depois de 'traces'
        trace_name = path_parts[0] if path_parts else 'Trace Desconhecido'
        # O tipo de estatística é a pasta atual
        estatistica_tipo = current_dir_name
      except Exception:
        # Fallback caso algo dê errado na extração do nome
        trace_name = "N/A"
        estatistica_tipo = current_dir_name
      # --- Fim da Lógica de Metadados ---

      output_txt_path = os.path.join(dirpath, 'estatisticas_calculadas.txt')
      try:
        with open(output_txt_path, 'w', encoding='utf-8') as f:
          # --- NOVO: Cabeçalho com Metadados ---
          f.write(f"Relatório de Estatísticas\n")
          f.write("="*40 + "\n")
          f.write(f"Trace: {trace_name}\n")
          f.write(f"Tipo de Análise: {estatistica_tipo}\n")
          f.write(f"Caminho Completo: {dirpath}\n")
          f.write("="*40 + "\n\n")
          # --- Fim do Cabeçalho ---
          
          f.write("\n" + "-"*20 + "\n\n".join(stats_para_salvar))
        print(f"  [OK] Relatório salvo em: {output_txt_path}")
      except Exception as e:
        print(f"  [ERRO] Falha ao salvar relatório em {output_txt_path}: {e}")

  print("\nProcessamento concluído.")

if __name__ == "__main__":
  # Define o diretório raiz onde o script vai começar a procurar
  # Altere 'traces' se o seu diretório principal tiver outro nome
  # ou estiver em outro lugar.
  diretorio_raiz = 'traces' 
  
  # Verifica se o diretório existe antes de rodar
  if not os.path.isdir(diretorio_raiz):
    print(f"Erro: O diretório '{diretorio_raiz}' não foi encontrado.")
    print("Por favor, execute este script no mesmo nível do diretório 'traces',")
    print("ou ajuste a variável 'diretorio_raiz' no código.")
  else:
    processar_diretorios(diretorio_raiz)