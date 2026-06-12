"""
llm_report.py

Este arquivo gera o prompt que sera enviado para uma LLM, como ChatGPT, Gemini,
LLaMA ou Falcon.

Nesta versao, o prompt foi adaptado para o problema VRP:
- uma rota por veiculo;
- instrucoes separadas para cada motorista;
- relatorio executivo comparando baseline e solucao otimizada.
"""

from genetic_algorithm import split_route_by_vehicles


def generate_llm_prompt(
    best_solution,
    hospital_names,
    priorities,
    weights,
    best_fitness,
    initial_fitness,
    final_distance,
    n_vehicles=3,
):
    """
    Monta um prompt em portugues com os dados da melhor solucao encontrada.

    O prompt inclui:
    - rotas separadas por veiculo;
    - prioridade de cada entrega;
    - peso de cada entrega;
    - custo inicial;
    - custo final;
    - distancia final aproximada;
    - melhoria percentual;
    - pedido de instrucoes para os motoristas.
    """

    vehicle_routes = split_route_by_vehicles(best_solution, n_vehicles)

    route_text = ""

    for vehicle_id, route in enumerate(vehicle_routes, start=1):
        route_text += f"\nVEICULO {vehicle_id}\n"
        route_text += "-" * 30 + "\n"

        total_weight = 0

        for stop_index, city in enumerate(route, start=1):
            total_weight += weights[city]

            route_text += (
                f"{stop_index}. {hospital_names[city]} "
                f"- Prioridade: {priorities[city]} "
                f"- Peso: {weights[city]}kg\n"
            )

        route_text += f"Peso total estimado do veiculo {vehicle_id}: {total_weight}kg\n"

    improvement = (
        ((initial_fitness - best_fitness) / initial_fitness) * 100
        if initial_fitness
        else 0
    )

    prompt = f"""
Voce e um coordenador logistico hospitalar.

O sistema utilizou um Algoritmo Genetico para resolver um problema de roteirizacao
com multiplos veiculos, conhecido como VRP (Vehicle Routing Problem).

Com base nas rotas otimizadas abaixo, gere:

1. Instrucoes claras e separadas para cada motorista.
2. Alertas sobre entregas prioritarias.
3. Cuidados no transporte de medicamentos e insumos hospitalares.
4. Relatorio executivo para a administracao do hospital.
5. Sugestoes de melhoria para proximas entregas.
6. Resposta curta para a pergunta: por que essa solucao e melhor que a rota baseline?

Rotas otimizadas por veiculo:

{route_text}

Indicadores da otimizacao:
- Quantidade de veiculos: {n_vehicles}
- Custo baseline aproximado: {round(initial_fitness, 2)}
- Custo final calculado pelo algoritmo genetico: {round(best_fitness, 2)}
- Distancia total aproximada: {round(final_distance, 2)} km
- Melhoria percentual aproximada: {round(improvement, 2)}%

Contexto operacional:
- Entregas de maior prioridade devem ser atendidas mais cedo.
- Cada veiculo possui limite de carga.
- Algumas unidades possuem janela de horario para atendimento.
- O uso de multiplos veiculos busca reduzir o tempo total da operacao.
- Medicamentos criticos exigem orientacao clara para a equipe de entrega.

Responda em portugues, de forma objetiva, profissional e organizada por veiculo.
"""

    return prompt