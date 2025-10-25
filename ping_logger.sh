#!/bin/bash

# --- Validação dos Argumentos ---
# Agora esperamos 3 argumentos obrigatórios e 1 opcional
if [ "$#" -lt 3 ] || [ "$#" -gt 4 ]; then
    echo "Erro: Número incorreto de argumentos."
    echo "Uso: $0 <IP_ALVO> <LIMITE_LINHAS> <CONTAGEM_PINGS> [FLAG_VERBOSE]"
    echo ""
    echo "  <IP_ALVO>: O endereço de IP para pingar."
    echo "  <LIMITE_LINHAS>: O número de linhas por arquivo de log."
    echo "  <CONTAGEM_PINGS>: O número total de pings a serem enviados."
    echo "  [FLAG_VERBOSE]: (Opcional) Qualquer valor (ex: '-v') para habilitar feedback."
    echo ""
    echo "Exemplo (Modo Silencioso): $0 8.8.8.8 100 500"
    echo "Exemplo (Modo Verbose):   $0 8.8.8.8 100 500 -v"
    exit 1
fi

IP_ALVO="$1"
LIMITE_LINHAS="$2"
CONTAGEM_PINGS="$3"
ARG_VERBOSE="$4"

# --- Define o Modo Verbose ---
# Verifica se o quarto argumento ($ARG_VERBOSE) não está vazio
VERBOSE=false
if [ -n "$ARG_VERBOSE" ]; then
    VERBOSE=true
fi

# --- Função Auxiliar de Log ---
# Esta função só imprimirá uma mensagem se VERBOSE for true
log() {
    if [ "$VERBOSE" = true ]; then
        # "$@" permite que todos os argumentos passados para log() sejam impressos
        echo "$@"
    fi
}

# --- Validação dos Limites Numéricos ---
# Verifica se LIMITE_LINHAS é um número inteiro e positivo
if ! [[ "$LIMITE_LINHAS" =~ ^[0-9]+$ ]] || [ "$LIMITE_LINHAS" -le 0 ]; then
    echo "Erro: O limite de linhas ($LIMITE_LINHAS) deve ser um número inteiro positivo."
    exit 1
fi

# Verifica se CONTAGEM_PINGS é um número inteiro e positivo
if ! [[ "$CONTAGEM_PINGS" =~ ^[0-9]+$ ]] || [ "$CONTAGEM_PINGS" -le 0 ]; then
    echo "Erro: A contagem de pings ($CONTAGEM_PINGS) deve ser um número inteiro positivo."
    exit 1
fi

# --- Configuração Inicial ---
NOME_ARQUIVO_BASE="ping_log"
contador_arquivo=1
contador_linha=0
NOME_ARQUIVO_ATUAL="${NOME_ARQUIVO_BASE}_${contador_arquivo}.txt"

# Usa a função log para todo feedback
log "Iniciando ping para $IP_ALVO. Total de $CONTAGEM_PINGS pings."
log "Limite de $LIMITE_LINHAS linhas por arquivo."
log "Salvando em $NOME_ARQUIVO_ATUAL..."

# --- Loop Principal ---

# Adicionamos a opção '-c $CONTAGEM_PINGS' ao comando ping.
# Isso diz ao 'ping' para parar automaticamente após enviar essa contagem.
# 'stdbuf -oL' força a saída linha por linha.
stdbuf -oL ping -c "$CONTAGEM_PINGS" "$IP_ALVO" | while read -r linha; do
    
    # 1. Exibe a saída do ping ao vivo (apenas em modo verbose)
    log "$linha"
    
    # 2. Salva a linha no arquivo de log atual (sempre acontece)
    echo "$linha" >> "$NOME_ARQUIVO_ATUAL"
    
    # 3. Incrementa o contador de linhas
    contador_linha=$((contador_linha + 1))
    
    # 4. Verifica se o limite de linhas foi atingido
    # NOTA: As estatísticas finais do ping (as últimas linhas) também contam
    # e podem acionar a troca de arquivo.
    if [ "$contador_linha" -ge "$LIMITE_LINHAS" ]; then
        log "--------------------------------------------------------"
        log "Atingido o limite de $LIMITE_LINHAS linhas."
        
        # Reseta o contador
        contador_linha=0
        
        # Incrementa o contador de arquivo
        contador_arquivo=$((contador_arquivo + 1))
        
        # Define novo nome de arquivo
        NOME_ARQUIVO_ATUAL="${NOME_ARQUIVO_BASE}_${contador_arquivo}.txt"
        
        log "Criando novo arquivo de log: $NOME_ARQUIVO_ATUAL"
        log "--------------------------------------------------------"
    fi
done

# O 'while loop' termina quando o 'ping -c' termina
log "--------------------------------------------------------"
log "Ping concluído. Total de $CONTAGEM_PINGS pings enviados."
log "Logs salvos em ${NOME_ARQUIVO_BASE}_*.txt"
log "--------------------------------------------------------"