# Tech Challenge Fase 2

## Projeto 2: Otimizacao de Rotas para Distribuicao de Medicamentos e Insumos

Este projeto implementa um sistema de otimizacao de rotas hospitalares usando Algoritmo Genetico, com base no exemplo de TSP estudado em aula.

A versao atual utiliza coordenadas aproximadas de hospitais e unidades da regiao central/expandida de Sao Paulo e gera tambem um mapa HTML interativo usando Folium/OpenStreetMap.

## Melhorias desta versao

Esta versao foi ajustada para obter uma melhoria mais significativa e uma comparacao mais justa:

- compara a rota otimizada contra uma rota baseline sem otimizacao;
- usa mutacao por inversao de trecho, melhor para TSP do que apenas trocar dois pontos;
- aumenta populacao e geracoes para melhorar a exploracao;
- prompt LLM gerados ao final.

## Objetivo

Encontrar uma rota otimizada para entrega de medicamentos e insumos entre unidades hospitalares, considerando:

- distancia geografica aproximada em km;
- prioridade das entregas;
- capacidade maxima do veiculo;
- autonomia maxima permitida;
- janelas de horario;
- visualizacao da evolucao com Pygame;
- geracao de prompt para LLM.

## Arquivos do projeto

- `hospital_data.py`: dados das unidades hospitalares, coordenadas, prioridades, pesos e janelas de horario.
- `genetic_algorithm.py`: populacao inicial, distancia geografica, fitness, crossover, mutacao, 2-opt e ordenacao.
- `draw_functions.py`: funcoes de desenho com Pygame e Matplotlib.
- `llm_report.py`: gera o prompt para LLM a partir da rota otimizada.
- `tsp_hospital.py`: arquivo principal que executa o algoritmo, mostra a visualizacao e gera os arquivos finais.

## Como executar

Instale as dependencias:

```bash
pip install -r requirements.txt
```

Execute:

```bash
python tsp_hospital.py
```

Para sair da tela do Pygame, pressione `Q`.

## Saidas geradas

Ao final da execucao, o programa gera:

```text
prompt_llm.txt
```

O arquivo `prompt_llm.txt` pode ser copiado para ChatGPT, Gemini, LLaMA ou outra LLM.

## Parametros principais

No arquivo `tsp_hospital.py`:

```python
POPULATION_SIZE = 120
N_GENERATIONS = 600
MUTATION_PROBABILITY = 0.25
VEHICLE_CAPACITY = 160
MAX_DISTANCE = 35
TOURNAMENT_SIZE = 7
```

## Funcao fitness

A funcao fitness hospitalar considera:

```text
custo = distancia + penalidade_prioridade + penalidade_capacidade + penalidade_autonomia + penalidade_janela_horario
```

Quanto menor o custo, melhor a rota.

## Operadores geneticos

- Selecao por torneio;
- Crossover ordenado;
- Mutacao por inversao de trecho;
- Elitismo, mantendo o melhor individuo da geracao anterior.

## Comparacao de melhoria

A melhoria agora e calculada contra uma rota baseline, que e a rota original na ordem do arquivo `hospital_data.py`.

Isso e mais adequado para o relatorio, pois compara:

```text
rota sem otimizacao x rota otimizada pelo algoritmo genetico
```

## Observacao academica

As coordenadas usadas sao aproximadas e servem para simulacao academica. Para uso real, seria necessario integrar dados oficiais, condicoes de transito, restricoes viarias e APIs de roteamento.
