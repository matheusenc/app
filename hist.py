"""
hist.py

Responsavel por persistir cada execucao do algoritmo genetico em disco (JSON)
e carregar registros por data ou intervalo para geracao de relatorios.

Estrutura de arquivos:
    hist/
        2025-06-20.json
        2025-06-21.json
        ...

Cada arquivo pode conter multiplas execucoes no mesmo dia (lista de registros).
"""

import json
import os
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional, Tuple

Point = Tuple[float, float]

HISTORICO_DIR = "hist"


# ---------------------------------------------------------------------------
# Serialização / Deserialização
# ---------------------------------------------------------------------------

def _point_to_key(point: Point) -> str:
    """Converte tupla (lat, lon) para string usável como chave JSON."""
    return f"{point[0]},{point[1]}"


def _key_to_point(key: str) -> Point:
    """Converte string 'lat,lon' de volta para tupla."""
    lat, lon = key.split(",")
    return (float(lat), float(lon))


def _serialize_route(route: List[Point]) -> List[List[float]]:
    return [[p[0], p[1]] for p in route]


def _deserialize_route(raw: List[List[float]]) -> List[Point]:
    return [tuple(p) for p in raw]


def _serialize_point_dict(d: Dict[Point, object]) -> Dict[str, object]:
    return {_point_to_key(k): v for k, v in d.items()}


def _deserialize_point_dict(d: Dict[str, object]) -> Dict[Point, object]:
    return {_key_to_point(k): v for k, v in d.items()}


# ---------------------------------------------------------------------------
# Salvar execução
# ---------------------------------------------------------------------------

def salvar_execucao(
    best_solution: List[Point],
    baseline_route: List[Point],
    hospital_names: Dict[Point, str],
    priorities: Dict[Point, int],
    weights: Dict[Point, int],
    baseline_fitness: float,
    best_fitness: float,
    final_distance: float,
    n_vehicles: int,
    population_size: int,
    n_generations: int,
    mutation_probability: float,
    data: Optional[date] = None,
) -> str:
    """
    Salva os dados da execucao atual em hist/YYYY-MM-DD.json.

    Retorna o caminho do arquivo salvo.
    """
    os.makedirs(HISTORICO_DIR, exist_ok=True)

    if data is None:
        data = date.today()

    filepath = os.path.join(HISTORICO_DIR, f"{data.isoformat()}.json")

    improvement = (
        ((baseline_fitness - best_fitness) / baseline_fitness) * 100
        if baseline_fitness > 0
        else 0.0
    )

    registro = {
        "data": data.isoformat(),
        "timestamp": datetime.now().isoformat(),
        "indicadores": {
            "baseline_fitness": round(baseline_fitness, 4),
            "best_fitness": round(best_fitness, 4),
            "improvement_pct": round(improvement, 4),
            "final_distance_km": round(final_distance, 4),
            "n_vehicles": n_vehicles,
        },
        "parametros_ga": {
            "population_size": population_size,
            "n_generations": n_generations,
            "mutation_probability": mutation_probability,
        },
        "rotas": {
            "otimizada": _serialize_route(best_solution),
            "baseline": _serialize_route(baseline_route),
            "por_veiculo": _dividir_por_veiculo(
                best_solution, hospital_names, priorities, weights, n_vehicles
            ),
        },
        "hospital_names": _serialize_point_dict(hospital_names),
        "priorities": _serialize_point_dict(priorities),
        "weights": _serialize_point_dict(weights),
    }

    # Arquivo pode ter múltiplas execuções no mesmo dia (lista)
    execucoes = []
    if os.path.exists(filepath):
        with open(filepath, "r", encoding="utf-8") as f:
            existente = json.load(f)
            # Suporta tanto lista quanto objeto único (legado)
            execucoes = existente if isinstance(existente, list) else [existente]

    execucoes.append(registro)

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(execucoes, f, ensure_ascii=False, indent=2)

    print(f"Execucao salva em: {filepath}")
    return filepath


def _dividir_por_veiculo(
    route: List[Point],
    hospital_names: Dict[Point, str],
    priorities: Dict[Point, int],
    weights: Dict[Point, int],
    n_vehicles: int,
) -> List[dict]:
    """Divide a rota otimizada em blocos por veiculo, com paradas detalhadas."""
    veiculos: List[List[Point]] = [[] for _ in range(n_vehicles)]
    for idx, ponto in enumerate(route):
        veiculos[idx % n_vehicles].append(ponto)

    resultado = []
    for v_idx, paradas in enumerate(veiculos, start=1):
        stops = []
        peso_total = 0
        for ordem, ponto in enumerate(paradas, start=1):
            peso = weights.get(ponto, 0)
            peso_total += peso
            stops.append({
                "ordem": ordem,
                "hospital": hospital_names.get(ponto, str(ponto)),
                "prioridade": priorities.get(ponto, 1),
                "peso_kg": peso,
                "ponto": _point_to_key(ponto),
            })
        resultado.append({
            "veiculo": v_idx,
            "n_paradas": len(paradas),
            "peso_total_kg": peso_total,
            "paradas": stops,
        })
    return resultado

# ---------------------------------------------------------------------------
# Carregar registros
# ---------------------------------------------------------------------------

def _carregar_arquivo(filepath: str) -> List[dict]:
    """Carrega e normaliza um arquivo de historico."""
    if not os.path.exists(filepath):
        return []
    with open(filepath, "r", encoding="utf-8") as f:
        dados = json.load(f)
    return dados if isinstance(dados, list) else [dados]


def carregar_dia(data: date) -> List[dict]:
    """Retorna todas as execucoes de um dia especifico."""
    filepath = os.path.join(HISTORICO_DIR, f"{data.isoformat()}.json")
    return _carregar_arquivo(filepath)


def carregar_intervalo(data_inicio: date, data_fim: date) -> List[dict]:
    """
    Retorna todas as execucoes entre data_inicio e data_fim (inclusive).
    Ordenadas por timestamp crescente.
    """
    registros = []
    delta = (data_fim - data_inicio).days

    for i in range(delta + 1):
        dia = data_inicio + timedelta(days=i)
        registros.extend(carregar_dia(dia))

    registros.sort(key=lambda r: r.get("timestamp", ""))
    return registros


def carregar_ultimos_dias(n: int) -> List[dict]:
    """Atalho: retorna execucoes dos ultimos N dias."""
    hoje = date.today()
    inicio = hoje - timedelta(days=n - 1)
    return carregar_intervalo(inicio, hoje)


def listar_dias_disponiveis() -> List[str]:
    """Retorna lista de datas (YYYY-MM-DD) com historico disponivel."""
    if not os.path.exists(HISTORICO_DIR):
        return []
    arquivos = sorted(
        f.replace(".json", "")
        for f in os.listdir(HISTORICO_DIR)
        if f.endswith(".json")
    )
    return arquivos


# ---------------------------------------------------------------------------
# Deserialização para uso no relatório
# ---------------------------------------------------------------------------

def deserializar_registro(registro: dict) -> dict:
    """
    Converte as strings de chave de volta para tuplas Point,
    tornando o registro utilizavel pelas funcoes do projeto.
    """
    return {
        **registro,
        "rotas": {
            "otimizada": _deserialize_route(registro["rotas"]["otimizada"]),
            "baseline": _deserialize_route(registro["rotas"]["baseline"]),
            "por_veiculo": registro["rotas"].get("por_veiculo", []),
        },
        "hospital_names": _deserialize_point_dict(registro["hospital_names"]),
        "priorities": _deserialize_point_dict(registro["priorities"]),
        "weights": _deserialize_point_dict(registro["weights"]),
    }


# ---------------------------------------------------------------------------
# Resumo agregado para relatórios
# ---------------------------------------------------------------------------

def resumo_periodo(registros: List[dict]) -> dict:
    """
    Calcula métricas agregadas de um conjunto de registros.
    Usado para alimentar o prompt de relatório semanal/mensal.
    """
    if not registros:
        return {}

    indicadores = [r["indicadores"] for r in registros]

    best_fitnesses   = [i["best_fitness"]      for i in indicadores]
    improvements     = [i["improvement_pct"]   for i in indicadores]
    distances        = [i["final_distance_km"]  for i in indicadores]
    baselines        = [i["baseline_fitness"]   for i in indicadores]

    melhor_dia = registros[best_fitnesses.index(min(best_fitnesses))]
    pior_dia   = registros[best_fitnesses.index(max(best_fitnesses))]

    return {
        "total_execucoes": len(registros),
        "periodo": {
            "inicio": registros[0]["data"],
            "fim": registros[-1]["data"],
        },
        "custo": {
            "media":  round(sum(best_fitnesses) / len(best_fitnesses), 2),
            "minimo": round(min(best_fitnesses), 2),
            "maximo": round(max(best_fitnesses), 2),
        },
        "melhoria_pct": {
            "media":  round(sum(improvements) / len(improvements), 2),
            "minima": round(min(improvements), 2),
            "maxima": round(max(improvements), 2),
        },
        "distancia_km": {
            "media":  round(sum(distances) / len(distances), 2),
            "minima": round(min(distances), 2),
            "maxima": round(max(distances), 2),
        },
        "baseline_medio": round(sum(baselines) / len(baselines), 2),
        "melhor_execucao": {
            "data":       melhor_dia["data"],
            "timestamp":  melhor_dia["timestamp"],
            "custo":      melhor_dia["indicadores"]["best_fitness"],
            "melhoria":   melhor_dia["indicadores"]["improvement_pct"],
        },
        "pior_execucao": {
            "data":       pior_dia["data"],
            "timestamp":  pior_dia["timestamp"],
            "custo":      pior_dia["indicadores"]["best_fitness"],
            "melhoria":   pior_dia["indicadores"]["improvement_pct"],
        },
    }