"""
llm_integration.py

Integracao com a API da OpenAI para geracao de relatorios e Q&A sobre rotas.

Divide as responsabilidades em 3 chamadas especializadas:
  1. instrucoes_motoristas  — instrucoes operacionais por veiculo
  2. relatorio_executivo    — KPIs, analise e recomendacoes para gestao
  3. responder_pergunta     — Q&A livre sobre rotas e historico

Cada funcao retorna o texto gerado ou lanca LLMError em caso de falha.
"""

import os
from typing import Dict, List, Optional, Tuple

from groq import Groq

from dotenv import load_dotenv
load_dotenv()

Point = Tuple[float, float]
Route = List[Point]

# ---------------------------------------------------------------------------
# Cliente OpenAI — usa OPENAI_API_KEY do ambiente
# ---------------------------------------------------------------------------

def _get_client():
    client = Groq(
        api_key=os.environ.get("GROQ_API_KEY"),
    )
    return client


class LLMError(Exception):
    pass


# ---------------------------------------------------------------------------
# Helpers internos
# ---------------------------------------------------------------------------

def _formatar_rotas_por_veiculo(
    route: Route,
    hospital_names: Dict[Point, str],
    priorities: Dict[Point, int],
    weights: Dict[Point, int],
    n_vehicles: int,
) -> str:
    """Formata a rota dividida por veiculo em texto estruturado."""
    vehicle_routes: List[List[Point]] = [[] for _ in range(n_vehicles)]
    for idx, city in enumerate(route):
        vehicle_routes[idx % n_vehicles].append(city)

    texto = ""
    for v_idx, v_route in enumerate(vehicle_routes, start=1):
        texto += f"\nVEICULO {v_idx}\n" + "-" * 32 + "\n"
        total_peso = 0
        for stop, city in enumerate(v_route, start=1):
            nome      = hospital_names.get(city, str(city))
            prioridade = priorities.get(city, 1)
            peso       = weights.get(city, 0)
            total_peso += peso
            texto += f"  {stop}. {nome} | Prioridade: {prioridade} | Peso: {peso}kg\n"
        texto += f"  Carga total: {total_peso}kg\n"

    return texto


def _chamar_groq(
    client: Groq,
    system: str,
    user: str,
    model: str = "openai/gpt-oss-20b",
    temperature: float = 0.4,
    max_tokens: int = 1500,
) -> str:
    """Wrapper de chamada a API com tratamento de erro centralizado."""
    try:
        response = client.chat.completions.create(
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            messages=[
                {"role": "system", "content": system},
                {"role": "user",   "content": user},
            ],
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        raise LLMError(f"Erro na chamada a OpenAI: {e}") from e


# ---------------------------------------------------------------------------
# 1. Instruções por motorista
# ---------------------------------------------------------------------------

SYSTEM_MOTORISTAS = """
Voce e um coordenador logistico de um hospital universitario.
Sua tarefa e transformar dados de rota em instrucoes claras e diretas para motoristas.

Regras:
- Use linguagem simples e objetiva — motoristas precisam entender rapidamente.
- Destaque em negrito os hospitais com prioridade 9 ou 10.
- Inclua alerta especial para medicamentos criticos (prioridade >= 9).
- Mantenha a ordem exata da rota ao listar as paradas.
- Finalize cada veiculo com o peso total e um aviso se ultrapassar 150kg.
- Responda SOMENTE em portugues brasileiro.
"""

def instrucoes_motoristas(
    route: Route,
    hospital_names: Dict[Point, str],
    priorities: Dict[Point, int],
    weights: Dict[Point, int],
    n_vehicles: int,
    baseline_fitness: float,
    best_fitness: float,
    final_distance: float,
) -> str:
    """
    Gera instrucoes operacionais separadas por veiculo.
    Chamada focada — resposta mais precisa e acionavel.
    """
    client = _get_client()

    rotas_texto = _formatar_rotas_por_veiculo(
        route, hospital_names, priorities, weights, n_vehicles
    )

    improvement = (
        ((baseline_fitness - best_fitness) / baseline_fitness) * 100
        if baseline_fitness > 0 else 0.0
    )

    user_prompt = f"""
Gere instrucoes de entrega para cada motorista com base nas rotas abaixo.

ROTAS DO DIA:
{rotas_texto}

INDICADORES:
- Distancia total: {round(final_distance, 2)} km
- Melhoria em relacao a rota padrao: {round(improvement, 2)}%

Para cada veiculo:
1. Liste as paradas em ordem com nome do hospital, prioridade e peso.
2. Destaque hospitais de prioridade 9 e 10 como PRIORITARIOS.
3. Adicione instrucoes de cuidado para cargas acima de 20kg por entrega.
4. Inclua um resumo final com carga total e distancia estimada.
"""
    return _chamar_groq(client, SYSTEM_MOTORISTAS, user_prompt, max_tokens=1800)


# ---------------------------------------------------------------------------
# 2. Relatório executivo
# ---------------------------------------------------------------------------

SYSTEM_EXECUTIVO = """
Voce e um analista de operacoes logisticas hospitalares.
Seu publico e a diretoria do hospital — pessoas que querem numeros, tendencias e decisoes.

Regras:
- Seja direto: comece pelos resultados, depois a analise.
- Use dados quantitativos sempre que disponivel.
- Aponte melhorias concretas e mensuráveis.
- Estruture em secoes: Resumo Executivo / Analise de Desempenho / Recomendacoes.
- Responda SOMENTE em portugues brasileiro.
"""

def relatorio_executivo(
    baseline_fitness: float,
    best_fitness: float,
    final_distance: float,
    n_vehicles: int,
    resumo_periodo: Optional[dict] = None,
) -> str:
    """
    Gera relatorio executivo para a diretoria.

    Se resumo_periodo for fornecido (dict de historico.resumo_periodo),
    gera um relatorio de periodo (semanal/mensal) em vez de execucao unica.
    """
    client = _get_client()

    improvement = (
        ((baseline_fitness - best_fitness) / baseline_fitness) * 100
        if baseline_fitness > 0 else 0.0
    )

    if resumo_periodo:
        p = resumo_periodo
        dados = f"""
RELATORIO DE PERIODO: {p['periodo']['inicio']} a {p['periodo']['fim']}
Total de execucoes: {p['total_execucoes']}

CUSTO DAS ROTAS:
- Media: {p['custo']['media']}
- Melhor resultado: {p['custo']['minimo']} (em {p['melhor_execucao']['data']})
- Pior resultado:   {p['custo']['maximo']} (em {p['pior_execucao']['data']})

MELHORIA vs BASELINE:
- Media do periodo: {p['melhoria_pct']['media']}%
- Melhor melhoria:  {p['melhoria_pct']['maxima']}%
- Pior melhoria:    {p['melhoria_pct']['minima']}%

DISTANCIA PERCORRIDA:
- Media: {p['distancia_km']['media']} km/dia
- Minima: {p['distancia_km']['minima']} km
- Maxima: {p['distancia_km']['maxima']} km

Baseline medio do periodo: {p['baseline_medio']}
"""
        user_prompt = f"""
Gere um relatorio executivo de periodo para a diretoria do hospital.

{dados}

Inclua:
1. Resumo executivo (3-4 linhas com os principais resultados).
2. Analise de tendencia: o algoritmo esta melhorando ao longo do periodo?
3. Dia de melhor e pior desempenho com possivel justificativa.
4. Recomendacoes para otimizar as proximas operacoes.
5. Economia estimada em relacao ao uso da rota padrao (baseline).
"""
    else:
        user_prompt = f"""
Gere um relatorio executivo de operacao diaria para a diretoria.

INDICADORES DA EXECUCAO:
- Custo baseline (rota padrao): {round(baseline_fitness, 2)}
- Custo otimizado (Algoritmo Genetico): {round(best_fitness, 2)}
- Melhoria obtida: {round(improvement, 2)}%
- Distancia total percorrida: {round(final_distance, 2)} km
- Numero de veiculos: {n_vehicles}

Inclua:
1. Resumo executivo com os principais numeros.
2. Analise do ganho obtido pelo algoritmo genetico vs rota padrao.
3. Impacto operacional (tempo estimado de economia, combustivel).
4. Recomendacoes para a proxima operacao.
"""

    return _chamar_groq(
        client, SYSTEM_EXECUTIVO, user_prompt,
        temperature=0.3, max_tokens=1500
    )


# ---------------------------------------------------------------------------
# 3. Q&A sobre rotas e histórico
# ---------------------------------------------------------------------------

SYSTEM_QA = """
Voce e um assistente especializado em logistica hospitalar.
Voce tem acesso ao historico de rotas otimizadas por um Algoritmo Genetico,
incluindo o detalhamento de paradas, prioridade e peso por veiculo em cada execucao.

Regras:
- Responda APENAS com base nos dados fornecidos no contexto.
- Se a informacao nao estiver disponivel, diga claramente.
- Seja conciso: responda a pergunta diretamente antes de elaborar.
- Para perguntas sobre um veiculo especifico, use o bloco "Veiculo N" do registro correspondente.
- Para perguntas comparativas, use os dados de todos os registros disponíveis.
- Responda SOMENTE em portugues brasileiro.
"""

def responder_pergunta(
    pergunta: str,
    historico_registros: List[dict],
    conversa: Optional[List[dict]] = None,
    incluir_detalhe_veiculos: bool = True,
) -> Tuple[str, List[dict]]:
    """
    Responde uma pergunta sobre as rotas usando o historico como contexto.

    Mantém o historico de mensagens para perguntas encadeadas (multi-turn).

    Retorna:
        (resposta: str, conversa_atualizada: List[dict])
    """
    client = _get_client()

    # Monta contexto compacto do historico
    contexto = _formatar_contexto_historico(
        historico_registros, incluir_detalhe_veiculos=incluir_detalhe_veiculos
    )

    # Inicializa ou continua a conversa
    if conversa is None:
        conversa = [
            {
                "role": "system",
                "content": SYSTEM_QA + f"\n\nCONTEXTO DO HISTORICO:\n{contexto}",
            }
        ]

    conversa.append({"role": "user", "content": pergunta})

    try:
        response = client.chat.completions.create(
            model="openai/gpt-oss-20b",
            temperature=0.3,
            max_tokens=800,
            messages=conversa,
        )
        resposta = response.choices[0].message.content.strip()
    except Exception as e:
        raise LLMError(f"Erro na chamada a OpenAI: {e}") from e

    conversa.append({"role": "assistant", "content": resposta})

    return resposta, conversa

def _formatar_veiculos_contexto(registro: dict) -> str:
    """Formata o detalhamento por veiculo de um registro para uso como contexto do Q&A."""
    veiculos = registro.get("rotas", {}).get("por_veiculo")
    if not veiculos:
        return "  (detalhamento por veiculo nao disponivel para este registro)"

    linhas = []
    for v in veiculos:
        linhas.append(
            f"  Veiculo {v['veiculo']}: {v['n_paradas']} paradas, "
            f"{v['peso_total_kg']}kg de carga total"
        )
        for parada in v["paradas"]:
            linhas.append(
                f"    {parada['ordem']}. {parada['hospital']} "
                f"(prioridade {parada['prioridade']}, {parada['peso_kg']}kg)"
            )
    return "\n".join(linhas)

def _formatar_contexto_historico(
    registros: List[dict], incluir_detalhe_veiculos: bool = True
) -> str:
    """Formata registros do historico em texto compacto para o contexto da LLM."""
    if not registros:
        return "Nenhum dado de historico disponivel."

    blocos = []
    for r in registros:
        ind = r.get("indicadores", {})
        params = r.get("parametros_ga", {})
        cabecalho = (
            f"Data: {r['data']} | "
            f"Timestamp: {r.get('timestamp', 'N/A')} | "
            f"Custo GA: {ind.get('best_fitness', 'N/A')} | "
            f"Baseline: {ind.get('baseline_fitness', 'N/A')} | "
            f"Melhoria: {ind.get('improvement_pct', 'N/A')}% | "
            f"Distancia: {ind.get('final_distance_km', 'N/A')} km | "
            f"Veiculos: {ind.get('n_vehicles', 'N/A')} | "
            f"Populacao GA: {params.get('population_size', 'N/A')} | "
            f"Geracoes: {params.get('n_generations', 'N/A')}"
        )
        if incluir_detalhe_veiculos:
            cabecalho += "\n" + _formatar_veiculos_contexto(r)
        blocos.append(cabecalho)

    return "\n\n".join(blocos)