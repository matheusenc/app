"""
scenario_randomizer.py

Gera variacoes aleatorias dos dados do problema para cada execucao:
  - Pesos das entregas por hospital
  - Prioridades dos hospitais


Os dados base do hospital_data.py sao usados como ancora: os valores
randomizados oscilam em torno dos originais dentro de faixas plausíveis,
mantendo a coerencia do cenario hospitalar.

Uso:
    from scenario_randomizer import randomize_scenario

    priorities, weights = randomize_scenario(
        hospital_locations, seed=42  # seed opcional para reproducibilidade
    )
"""

import random
from typing import Dict, List, Optional, Tuple

Point = Tuple[float, float]

# ---------------------------------------------------------------------------
# Faixas de randomizacao
# ---------------------------------------------------------------------------

# Prioridade: 1 (baixa) a 10 (critica)
PRIORITY_MIN = 1
PRIORITY_MAX = 10

# Peso por entrega em kg
WEIGHT_MIN = 5
WEIGHT_MAX = 40

# Janela de horario: abertura e duracao minima da janela
WINDOW_OPEN_MIN  = 0    # minutos apos inicio da operacao
WINDOW_OPEN_MAX  = 120
WINDOW_DURATION_MIN = 60   # janela minima de atendimento
WINDOW_DURATION_MAX = 240

# Percentual de hospitais que recebem janela de horario (0.0 a 1.0)
TIME_WINDOW_COVERAGE = 0.65


# ---------------------------------------------------------------------------
# Funcao principal
# ---------------------------------------------------------------------------

def randomize_scenario(
    hospital_locations: List[Point],
    base_priorities: Optional[Dict[Point, int]] = None,
    base_weights: Optional[Dict[Point, int]] = None,
    base_time_windows: Optional[Dict[Point, Tuple[int, int]]] = None,
    seed: Optional[int] = None,
) -> Tuple[
    Dict[Point, int],           # priorities
    Dict[Point, int],           # weights
    ]:
    """
    Gera um cenario aleatorio de dificuldade para o problema.

    Parametros
    ----------
    hospital_locations : lista de coordenadas (lat, lon)
    base_priorities    : prioridades originais do hospital_data (ancora)
    base_weights       : pesos originais do hospital_data (ancora)
    base_time_windows  : janelas originais do hospital_data (ancora)
    seed               : semente para reproducibilidade (None = aleatorio)

    Retorna
    -------
    priorities, weights
    """

    rng = random.Random(seed)
    n = len(hospital_locations)

    # --- Prioridades ---
    priorities: Dict[Point, int] = {}
    for point in hospital_locations:
        if base_priorities and point in base_priorities:
            base = base_priorities[point]
            # Oscila +-2 em torno do valor original, respeitando os limites
            delta = rng.randint(-2, 2)
            value = max(PRIORITY_MIN, min(PRIORITY_MAX, base + delta))
        else:
            value = rng.randint(PRIORITY_MIN, PRIORITY_MAX)
        priorities[point] = value

    # Garante pelo menos 2 hospitais criticos (prioridade 10) e 2 baixos (<=7)
    pontos = list(hospital_locations)
    rng.shuffle(pontos)
    for p in pontos[:2]:
        priorities[p] = 10
    for p in pontos[-2:]:
        priorities[p] = max(PRIORITY_MIN, min(7, priorities[p]))

    # --- Pesos ---
    weights: Dict[Point, int] = {}
    for point in hospital_locations:
        if base_weights and point in base_weights:
            base = base_weights[point]
            # Oscila +-30% em torno do valor original
            delta_pct = rng.uniform(-0.3, 0.3)
            value = int(round(base * (1 + delta_pct)))
            value = max(WEIGHT_MIN, min(WEIGHT_MAX, value))
        else:
            value = rng.randint(WEIGHT_MIN, WEIGHT_MAX)
        weights[point] = value

    # --- Janelas de horario ---
    time_windows: Dict[Point, Tuple[int, int]] = {}
    n_with_window = max(2, int(n * TIME_WINDOW_COVERAGE))

    # Hospitais com maior prioridade tem preferencia para receber janela
    sorted_by_priority = sorted(
        hospital_locations,
        key=lambda p: priorities[p],
        reverse=True,
    )
    hospitals_with_window = sorted_by_priority[:n_with_window]

    for point in hospitals_with_window:
        open_time = rng.randint(WINDOW_OPEN_MIN, WINDOW_OPEN_MAX)
        duration  = rng.randint(WINDOW_DURATION_MIN, WINDOW_DURATION_MAX)
        close_time = open_time + duration
        time_windows[point] = (open_time, close_time)

    # Se havia janelas originais, preserva as de prioridade 10 (criticos)
    if base_time_windows:
        for point, window in base_time_windows.items():
            if priorities.get(point, 0) == 10:
                time_windows[point] = window


    return priorities, weights
