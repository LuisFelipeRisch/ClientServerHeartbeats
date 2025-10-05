import pandas as pd
from pathlib import Path

def calculate_stats(file_path, column_name):
    """
    Calcula a média e o desvio padrão de uma coluna específica em um arquivo CSV.
    Retorna uma tupla (mean, std_dev) ou (None, None) em caso de erro.
    """
    try:
        # Verifica se o arquivo existe e não está vazio
        if not file_path.is_file() or file_path.stat().st_size == 0:
            print(f"Aviso: Arquivo não encontrado ou vazio: {file_path}")
            return None, None
            
        df = pd.read_csv(file_path)

        if column_name not in df.columns:
            print(f"Aviso: Coluna '{column_name}' não encontrada em {file_path}. Colunas disponíveis: {list(df.columns)}")
            return None, None

        # Garante que a coluna seja numérica, convertendo erros em 'NaN' que serão ignorados pelos cálculos
        df[column_name] = pd.to_numeric(df[column_name], errors='coerce')
        
        # Remove linhas onde a coluna alvo é NaN
        df.dropna(subset=[column_name], inplace=True)
        
        if df.empty:
            print(f"Aviso: Nenhuma entrada numérica válida encontrada para a coluna '{column_name}' em {file_path}.")
            return None, None

        mean_value = df[column_name].mean()
        std_dev_value = df[column_name].std()

        return mean_value, std_dev_value

    except Exception as e:
        print(f"Erro inesperado ao processar o arquivo {file_path}: {e}")
        return None, None

def main():
    """
    Função principal para percorrer os diretórios e gerar os arquivos de estatísticas.
    """
    root_dir = Path('csvs')
    
    files_to_process = {
        'estimated.csv': 'Estimated',
        'jac.csv': 'Jac',
        'tun_phi.csv': 'Tun Phi'
    }

    leaf_dirs = [d for d in root_dir.glob('*/*/*') if d.is_dir()]

    if not leaf_dirs:
        print("Nenhum diretório encontrado na estrutura esperada 'csvs/*/*/*'. Verifique a estrutura de pastas.")
        return

    print("Iniciando processamento...")

    for leaf_dir in leaf_dirs:
        print(f"\nProcessando diretório: {leaf_dir}")
        
        # --- LÓGICA PARA SELECIONAR A COLUNA ALVO ---
        path_str = str(leaf_dir)
        target_column = None
        
        if 'time_detection' in path_str:
            target_column = 'time_to_detect_s'
        elif 'time_mistake' in path_str:
            target_column = 'time_taken_to_correct_s'
        else:
            print(f"  -> Aviso: Não foi possível determinar a coluna alvo para o diretório. Pulando.")
            continue # Pula para o próximo diretório

        print(f"  -> Coluna alvo selecionada: '{target_column}'")

        output_content = []
        stats_file_path = leaf_dir / 'stats.txt'

        for filename, title in files_to_process.items():
            csv_path = leaf_dir / filename
            
            # Passa a coluna alvo determinada dinamicamente
            mean_val, std_val = calculate_stats(csv_path, target_column)
            
            if mean_val is not None and std_val is not None:
                content = (
                    f"---- {title} ----\n\n"
                    f"Mean: {mean_val}\n"
                    f"Standard Deviation: {std_val}"
                )
                output_content.append(content)
            else:
                print(f"  -> Falha ao calcular estatísticas para {csv_path}")

        if output_content:
            try:
                with open(stats_file_path, 'w', encoding='utf-8') as f:
                    f.write('\n\n'.join(output_content))
                print(f"  -> Arquivo '{stats_file_path}' gerado com sucesso!")
            except Exception as e:
                print(f"  -> Erro ao escrever o arquivo '{stats_file_path}': {e}")
        else:
            print(f"  -> Nenhum dado processado para o diretório {leaf_dir}. O arquivo 'stats.txt' não foi gerado.")

    print("\nProcesso concluído! ✅")

if __name__ == "__main__":
    main()