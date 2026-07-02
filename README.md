# Tech Challenge — Fase 2

## Projeto 2: Otimização de Rotas para Distribuição de Medicamentos e Insumos

Sistema de otimização de rotas hospitalares usando Algoritmo Genético (TSP), com cenários randomizados, visualização interativa via Pygame e Folium, integração com LLM (Groq) para relatórios e Q&A, e persistência de histórico em JSON.

---

## Arquitetura do sistema

```
┌─────────────────────────────────────────────────────────┐
│                    ENTRADA DE DADOS                     │
│  hospital_data.py  │  scenario_randomizer.py  │  Sliders│
└──────────────┬─────────────────┬──────────────┬─────────┘
               │                 │              │
               ▼                 ▼              ▼
┌─────────────────────────────────────────────────────────┐
│                  genetic_algorithm.py                   │
│   População inicial │ Fitness │ Crossover │ Mutação     │
│              ◄──── loop gerações ────►                  │
└───────────────────────────┬─────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────┐
│                    tsp_hospital.py                      │
│         Loop principal · elitismo · parada              │
└──────┬──────────────┬───────────────┬────────────┬──────┘
       │              │               │            │
       ▼              ▼               ▼            ▼
draw_functions   Mapas Folium      hist.py    report_cli.py
  Pygame +      baseline +       JSON +        Menu +
 Matplotlib      otimizado     indicadores     período
                                    │            │
                                    └─────┬──────┘
                                          ▼
                              ┌───────────────────────┐
                              │   llm_integration.py  │
                              │       Groq API        │
                              │  Instruções │ Exec.   │
                              │  motoristas │ report  │
                              │         Q&A           │
                              └───────────┬───────────┘
                                          ▼
                                      reports/
                                  relatórios .txt
```

---

## Arquivos do projeto

| Arquivo | Responsabilidade |
|---|---|
| `tsp_hospital.py` | Arquivo principal — executa o GA, Pygame e gera as saídas |
| `genetic_algorithm.py` | População inicial, fitness, crossover, mutação e ordenação |
| `hospital_data.py` | Coordenadas, nomes, prioridades, pesos e janelas de horário |
| `scenario_randomizer.py` | Randomização de prioridades, pesos e janelas de horário |
| `draw_functions.py` | Visualização Pygame, Matplotlib e exportação Folium |
| `hist.py` | Persistência de execuções em JSON e carregamento por período |
| `llm_integration.py` | Integração com Groq — relatórios e Q&A |
| `report_cli.py` | Menu interativo de relatórios e Q&A via terminal |
| `test_tsp_hospital.py` | Suite de testes automatizados (pytest) |

---

## Como executar

**1. Criar e ativar o ambiente virtual**

```bash
python3 -m venv venv

# Windows
venv\Scripts\activate

# Linux/macOS
source venv/bin/activate
```

**2. Instalar dependências**

```bash
pip install -r requirements.txt
```

**3. Configurar a chave da LLM**

Crie um arquivo `.env` na raiz do projeto:

```
GROQ_API_KEY=sua-chave-aqui
```

Ou exporte no terminal:

```bash
# Windows
set GROQ_API_KEY=sua-chave-aqui

# Linux/macOS
export GROQ_API_KEY=sua-chave-aqui
```

Obtenha uma chave gratuita em [console.groq.com](https://console.groq.com).

**4. Executar o algoritmo**

```bash
python tsp_hospital.py
```

Pressione `Q` para encerrar a visualização do Pygame.

**5. Relatórios e Q&A (sessão separada)**

```bash
python report_cli.py
```

**6. Executar os testes**

```bash
pytest test_tsp_hospital.py -v
```

---

## Tela de configuração

Ao iniciar, uma tela Pygame permite ajustar os parâmetros antes de executar:

| Parâmetro | Padrão | Descrição |
|---|---|---|
| Veículos | 3 | Número de veículos (divide a rota entre eles) |
| População | 80 | Tamanho da população do GA |
| Gerações máximas | 1000 | Limite de iterações |
| Sem melhora | 250 | Critério de parada por estagnação |

---

## Cenários randomizados

O `scenario_randomizer.py` gera variações de dificuldade a cada execução, mantendo os dados do `hospital_data.py` como âncora.

**O que é randomizado:**

- **Prioridades** — oscilam ±2 em torno dos valores originais; garante ao menos 2 hospitais com prioridade 10
- **Pesos de carga** — variam ±30% em torno dos valores base (5–40 kg por entrega)
- **Janelas de horário** — geradas para 65% dos hospitais, priorizando os de maior urgência

Para reproduzir um cenário específico, use o parâmetro `seed`:

```python
priorities, weights = randomize_scenario(hospital_locations, seed=42)
```

---

## Função fitness

```
custo = distância
      + penalidade_prioridade
      + penalidade_capacidade
      + penalidade_autonomia
      + penalidade_janela_horário
      + penalidade_tráfego
```

**Penalidade de prioridade** — baseada no tempo real decorrido até cada hospital (não na posição na rota). O fator de urgência é normalizado para manter a penalidade na mesma ordem de grandeza que a distância (~ratio 1:1), evitando que um componente domine o fitness:

```python
priority_penalty += elapsed_time * urgency * 0.2
```

**Velocidade de tráfego** — randomizada por segmento de rota em faixas por distância:

```python
if distance <= 5:   return random.uniform(10.0, 25.0)  # vias locais
if distance <= 15:  return random.uniform(18.0, 35.0)  # vias intermediárias
return              random.uniform(25.0, 50.0)          # vias expressas
```

---

## Operadores genéticos

| Operador | Implementação |
|---|---|
| Seleção | Torneio (`TOURNAMENT_SIZE = 7`) |
| Crossover | Order Crossover (OX) |
| Mutação | Inversão de trecho (`inversion_mutate`) |
| Elitismo | Melhor indivíduo preservado entre gerações |

**Por que inversão de trecho?** Mantém intactas as conexões externas ao segmento e reconsidera apenas a direção interna — equivalente ao 2-opt, uma das heurísticas clássicas mais eficazes para TSP.

**Estratégias de inicialização disponíveis** em `genetic_algorithm.py`:

- `generate_random_population` — totalmente aleatória
- `generate_random_population_with_pre_ordering` — metade pré-ordenada por Nearest Neighbor, metade aleatória
- `generate_pre_ordering_population` — toda a população inicializada pelo vizinho mais próximo

---

## Saídas geradas

Após cada execução:

```
mapa_baseline.html      → rota original sem otimização (Folium/OpenStreetMap)
mapa_otimizado.html     → melhor rota encontrada pelo GA (Folium/OpenStreetMap)
hist/YYYY-MM-DD.json    → dados da execução para relatórios
```

Os mapas HTML exibem:
- Marcadores numerados por hospital com popup (nome, prioridade, peso, veículo)
- Cor do marcador por nível de prioridade (verde = início/fim, vermelho = parada)
- Linha da rota com tooltip

---

## Relatórios e Q&A com LLM

O menu interativo `report_cli.py` oferece:

```
[1] Instruções para motoristas     → instruções operacionais por veículo
[2] Relatório executivo            → KPIs e análise para a diretoria
[3] Perguntas sobre as rotas (Q&A) → conversa multi-turn com contexto do histórico
[4] Ver histórico disponível       → lista execuções com indicadores
```

**Seleção de período:**
- Hoje / últimos 7 dias / últimos 30 dias
- Data específica ou intervalo de datas
- Seleção manual de dias do histórico

Relatórios gerados são salvos em `reports/` com timestamp.

**Modelo LLM:** `openai/gpt-oss-20b` via Groq.

---

## Histórico de execuções

Cada execução salva em `hist/YYYY-MM-DD.json`:

```json
{
  "data": "2026-06-23",
  "timestamp": "2026-06-23T19:25:52",
  "indicadores": {
    "baseline_fitness": 58655.94,
    "best_fitness": 52000.00,
    "improvement_pct": 11.34,
    "final_distance_km": 134.21,
    "n_vehicles": 3
  },
  "parametros_ga": { "population_size": 80, "n_generations": 1000, "mutation_probability": 0.25 },
  "rotas": { "otimizada": [...], "baseline": [...] }
}
```

Múltiplas execuções no mesmo dia ficam na mesma lista.

---

## Testes automatizados

Suite com **54 testes** cobrindo todos os módulos principais:

```bash
pytest test_tsp_hospital.py -v
```

| Módulo | O que é testado |
|---|---|
| `calculate_distance` | Simetria, zero na mesma posição, distâncias conhecidas, desigualdade triangular |
| `calculate_fitness` | Rota vazia, um ponto, dois pontos, rota fechada |
| `calculate_hospital_fitness` | Penalidades de prioridade, capacidade, autonomia e janela de horário |
| `order_crossover` | Tamanho, genes preservados, sem duplicatas |
| `mutate / inversion_mutate` | Genes preservados, probabilidade zero, imutabilidade do original |
| `sort_population` | Ordenação crescente, alinhamento população/fitness |
| `split_route_by_vehicles` | Distribuição round-robin, preservação de pontos |
| `generate_*_population` | Tamanho, completude, pré-ordenação consistente |
| `calculate_multi_vehicle_fitness` | Custo positivo, equivalência com 1 veículo |
| `scenario_randomizer` | Ranges, garantia de críticos, reprodutibilidade por seed |
| `hist` | Criação de arquivo, JSON válido, múltiplas execuções, carregar por intervalo, deserialização, resumo de período |

---

## Comparação de melhoria

```
improvement = (baseline_fitness - best_fitness) / baseline_fitness × 100
```

O baseline é a rota na ordem original do `hospital_data.py`. Valores positivos indicam que o GA encontrou uma rota mais eficiente. O fitness considera distância, prioridade de atendimento, respeito às janelas de horário e condições de tráfego — tornando a comparação mais realista que uma comparação puramente geográfica.

---

## Observação acadêmica

As coordenadas e dados utilizados são aproximados e servem para simulação acadêmica. Para uso em produção seria necessário integrar dados oficiais de tráfego, restrições viárias reais, APIs de roteamento (Google Maps, OSRM) e dados operacionais das unidades hospitalares.
