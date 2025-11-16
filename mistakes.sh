#!/bin/bash

# --- 1. Defina sua lista de CAMINHOS RELATIVOS aqui ---
LISTA_DE_CAMINHOS=(
    "traces/traces_toquio_uk/raw"
    "traces/traces_toquio_usa/raw"
    "traces/traces_uk_toquio/raw" 
    "traces/traces_uk_usa/raw"
    "traces/traces_usa_toquio/raw"
    "traces/traces_usa_uk/raw"
)

# 2. Defina o nome do seu script Python
SCRIPT_PYTHON="time_mistake.py"

echo "Iniciando processamento com lista de caminhos relativos..."

# 3. O Loop
for caminho in "${LISTA_DE_CAMINHOS[@]}"; do
    
    # 4. Verificação de segurança: checa se o caminho existe E é um diretório
    if [ -d "$caminho" ]; then
        
        # 5. Mensagem de log
        echo "Processando: $caminho"
        
        # 6. Executa o script Python
        # As aspas "$caminho" são essenciais para caminhos com espaços!
        python3 "$SCRIPT_PYTHON" "$caminho"
        
    else
        # 7. Aviso se o caminho da lista não for encontrado
        echo "Aviso: Caminho '$caminho' não encontrado ou não é um diretório. Pulando."
    fi
done

echo "Processamento concluído."