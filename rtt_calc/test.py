import random
import math

# --- Parâmetros da Simulação ---

# Nome do arquivo de saída
NOME_ARQUIVO = "data.txt"

# Número de mensagens a serem recebidas (e linhas no arquivo)
NUM_LINHAS = 100

# O intervalo de tempo fixo (em ms) com que o Host A envia as mensagens.
# Este é o nosso valor de referência.
INTERVALO_BASE = 30.0

# O "jitter" normal da rede. Usamos um desvio padrão para simular
# pequenas variações em torno do intervalo base. Um valor maior aqui
# significa uma rede com mais flutuações constantes.
JITTER_NORMAL_STD_DEV = 2.0

# Simula picos de latência esporádicos na rede.
# 5% de chance de um pico de latência ocorrer.
PROBABILIDADE_PICO_LATENCIA = 0.05
# Atraso extra adicionado durante um pico (entre 15ms e 40ms)
PICO_LATENCIA_ADICIONAL_MIN = 15.0
PICO_LATENCIA_ADICIONAL_MAX = 40.0


def gerar_dados_rtt():
    """
    Simula e gera uma lista de intervalos de chegada de pacotes.
    """
    intervalos = []
    for _ in range(NUM_LINHAS):
        # Começa com o intervalo de envio fixo do Host A
        intervalo_chegada = INTERVALO_BASE

        # 1. Adiciona o jitter normal da rede (pequenas flutuações)
        # Usamos random.gauss para uma distribuição normal, que é mais realista.
        jitter = random.gauss(0, JITTER_NORMAL_STD_DEV)
        intervalo_chegada += jitter

        # 2. Verifica se ocorreu um pico de latência esporádico
        if random.random() < PROBABILIDADE_PICO_LATENCIA:
            atraso_extra = random.uniform(PICO_LATENCIA_ADICIONAL_MIN, PICO_LATENCIA_ADICIONAL_MAX)
            intervalo_chegada += atraso_extra

        # Garante que o intervalo não seja negativo (o que é impossível)
        # e arredonda para o número inteiro mais próximo.
        intervalo_final = max(1, math.ceil(intervalo_chegada))
        intervalos.append(intervalo_final)
        
    return intervalos

def salvar_em_arquivo(dados, nome_arquivo):
    """
    Salva a lista de dados em um arquivo de texto, um item por linha.
    """
    try:
        with open(nome_arquivo, 'w') as file:
            for item in dados:
                file.write(str(item) + '\n')
        print(f"Arquivo '{nome_arquivo}' gerado com sucesso com {len(dados)} linhas.")
    except IOError as e:
        print(f"Erro ao escrever no arquivo '{nome_arquivo}': {e}")


# --- Execução Principal ---
if __name__ == "__main__":
    dados_simulados = gerar_dados_rtt()
    salvar_em_arquivo(dados_simulados, NOME_ARQUIVO)