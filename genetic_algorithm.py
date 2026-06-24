'''---------------------------------------------------------------------------------------
genetic_algorithm.py

Funcoes principais do Algoritmo Genetico usado no Tech Challenge.

Esta versao mantem a base do TSP estudado em aula, mas adiciona adaptacoes
para o problema de rotas hospitalares
---------------------------------------------------------------------------------------'''
import copy
import math
import random
from typing import Dict, List, Optional, Tuple
from sklearn.neighbors import NearestNeighbors
import numpy as np

Point = Tuple[float, float]
Route = List[Point]

def order_by_nearest(coords_rad, cities_coords, n):
    """
    Retorna as coordenadas das cidades ordenadas pela heurística do vizinho mais próximo.
    coords_rad: coordenadas em radianos (para haversine)
    cities_coords: coordenadas originais (para retornar na ordem correta)
    """
    nbrs = NearestNeighbors(n_neighbors=n, metric='haversine', algorithm='ball_tree').fit(coords_rad)

    visited = [False] * n
    order = [0]
    visited[0] = True
    current = 0

    for _ in range(n - 1):
        distances, indices = nbrs.kneighbors([coords_rad[current]])
        for idx in indices[0]:
            if not visited[idx]:
                visited[idx] = True
                order.append(idx)
                current = idx
                break

    # Retorna as coordenadas originais na ordem calculada
    return [cities_coords[i] for i in order]


'''------------------------------------------------------------------
Gera a populacao inicial do algoritmo genetico.
Cada individuo e uma rota com todos os hospitais em uma ordem aleatoria.
------------------------------------------------------------------'''
def generate_random_population_with_pre_ordering(
    cities_location: List[Point],
    population_size: int
) -> List[Route]:
    cities_location_len = len(cities_location)

    if cities_location_len > 1:
        mid = cities_location_len // 2
        cities_part_1 = cities_location[:mid]  # será pré-ordenada
        cities_part_2 = cities_location[mid:]  # será embaralhada

        # Converte para radianos (necessário para haversine)
        coords_rad = np.radians(np.array(cities_part_1))

        # Obtém a parte 1 ordenada por vizinho mais próximo (UMA única sequência)
        ordered_part_1 = order_by_nearest(coords_rad, cities_part_1, len(cities_part_1))

        # Gera population_size indivíduos, cada um com a rota completa:
        # parte 1 pré-ordenada (fixa) + parte 2 embaralhada (aleatória)
        population = [
            ordered_part_1 + random.sample(cities_part_2, len(cities_part_2))
            for _ in range(population_size)
        ]

        return population

    else:
        return [
            random.sample(cities_location, len(cities_location))
            for _ in range(population_size)
        ]
    
def  generate_pre_ordering_population(
    cities_location: List[Point],
    population_size: int
) -> List[Route]:
    coords_rad = np.radians(np.array(cities_location))

    ordered_part_1 = order_by_nearest(coords_rad, cities_location, len(cities_location))

    population = [
        ordered_part_1
        for _ in range(population_size)
    ]

    return population


def generate_random_population(
    cities_location: List[Point],
    population_size: int
) -> List[Route]:

    return [
        random.sample(cities_location, len(cities_location))
        for _ in range(population_size)
    ]



'''------------------------------------------------------------------
Calcula a distancia geografica aproximada entre duas coordenadas.
Usa a formula de Haversine com retorno e em quilometros.
------------------------------------------------------------------'''
def calculate_distance(point1: Point, point2: Point) -> float:
    earth_radius_km = 6371.0

    lat1 = math.radians(point1[0])
    lon1 = math.radians(point1[1])
    lat2 = math.radians(point2[0])
    lon2 = math.radians(point2[1])

    delta_lat = lat2 - lat1
    delta_lon = lon2 - lon1

    a = (
        math.sin(delta_lat / 2) ** 2
        + math.cos(lat1)
        * math.cos(lat2)
        * math.sin(delta_lon / 2) ** 2
    )

    c = 2 * math.atan2(
        math.sqrt(a),
        math.sqrt(1 - a)
    )

    return earth_radius_km * c

'''------------------------------------------------------------------
Calcula a distancia total da rota fechada.
A rota e fechada porque, no TSP, o veiculo retorna ao ponto inicial.
------------------------------------------------------------------'''
def calculate_fitness(path: Route) -> float:
    distance = 0.0
    n = len(path)

    if n < 2:
        return 0.0

    for i in range(n):
        distance += calculate_distance(
            path[i],
            path[(i + 1) % n]
        )

    return distance

'''------------------------------------------------------------------
Executa o crossover ordenado, Order Crossover
------------------------------------------------------------------'''
def order_crossover(
    parent1: Route,
    parent2: Route
) -> Route:

    length = len(parent1)

    start_index = random.randint(0, length - 1)
    end_index = random.randint(start_index + 1, length)

    child = parent1[start_index:end_index]

    remaining_positions = [
        i for i in range(length)
        if i < start_index or i >= end_index
    ]

    remaining_genes = [
        gene for gene in parent2
        if gene not in child
    ]

    for position, gene in zip(
        remaining_positions,
        remaining_genes
    ):
        child.insert(position, gene)

    return child
'''------------------------------------------------------------------
Aplica mutacao por troca de dois pontos.
------------------------------------------------------------------'''
def mutate(
    solution: Route,
    mutation_probability: float
) -> Route:

    mutated_solution = copy.deepcopy(solution)

    if random.random() < mutation_probability:
        if len(solution) < 2:
            return solution

        index1, index2 = random.sample(
            range(len(solution)),
            2
        )

        mutated_solution[index1], mutated_solution[index2] = (
            mutated_solution[index2],
            mutated_solution[index1],
        )

    return mutated_solution

def inversion_mutate(solution, mutation_probability):
    mutated = copy.deepcopy(solution)
    if random.random() < mutation_probability:
        i, j = sorted(random.sample(range(len(solution)), 2))
        mutated[i:j+1] = reversed(mutated[i:j+1])
    return mutated


'''------------------------------------------------------------------
Ordena a populacao pelo fitness.
------------------------------------------------------------------'''
def sort_population(
    population: List[Route],
    fitness: List[float]
):
    combined_lists = list(zip(population, fitness))

    sorted_combined_lists = sorted(
        combined_lists,
        key=lambda x: x[1]
    )

    sorted_population, sorted_fitness = zip(
        *sorted_combined_lists
    )

    return list(sorted_population), list(sorted_fitness)

'''------------------------------------------------------------------
Simula velocidade media considerando transito urbano em Sao Paulo.

Regras usadas:
- ate 5 km: 18 km/h
- ate 15 km: 25 km/h
- acima de 15 km: 35 km/h
------------------------------------------------------------------'''
def get_traffic_speed(point1: Point, point2: Point) -> float:

    distance = calculate_distance(point1, point2)

    if distance <= 5:
        return 18.0

    if distance <= 15:
        return 25.0

    return 35.0

'''------------------------------------------------------------------
Calcula o tempo total estimado da rota em minutos,
considerando o modelo de transito simulado.

Esta funcao considera somente os deslocamentos entre pontos consecutivos.
------------------------------------------------------------------'''
def calculate_route_time(route: Route) -> float:
    if len(route) < 2:
        return 0.0

    elapsed_time = 0.0

    for i in range(1, len(route)):
        previous_city = route[i - 1]
        current_city = route[i]

        distance = calculate_distance(
            previous_city,
            current_city
        )

        speed = get_traffic_speed(
            previous_city,
            current_city
        )

        elapsed_time += (distance / speed) * 60.0

    return elapsed_time

'''------------------------------------------------------------------
Calcula o custo total da rota hospitalar.

O custo considera:
1. distancia geografica
2. prioridade das entregas
3. capacidade maxima do veiculo
4. autonomia maxima
5. janelas de atendimento
6. transito urbano simulado

Menor fitness significa melhor solucao.
------------------------------------------------------------------'''
def calculate_hospital_fitness(
    path: Route,
    priorities: Dict[Point, int],
    weights: Dict[Point, int],
    vehicle_capacity: int = 160,
    max_distance: int = 35,
    time_windows: Optional[Dict[Point, Tuple[int, int]]] = None,
) -> float:
    distance = calculate_fitness(path)

    total_weight = sum(
        weights.get(city, 0)
        for city in path
    )

    capacity_penalty = 0.0
    if total_weight > vehicle_capacity:
        capacity_penalty = (
            total_weight - vehicle_capacity
        ) * 80.0

    autonomy_penalty = 0.0
    if distance > max_distance:
        autonomy_penalty = (
            distance - max_distance
        ) * 3.0

    priority_penalty = 0.0
    time_penalty = 0.0
    traffic_penalty = 0.0
    elapsed_time = 0.0

    for i, city in enumerate(path):
        if i > 0:
            previous_city = path[i - 1]

            segment_distance = calculate_distance(
                previous_city,
                city
            )

            traffic_speed = get_traffic_speed(
                previous_city,
                city
            )

            elapsed_time += (
                segment_distance
                / traffic_speed
                * 60.0
            )

            if traffic_speed <= 18.0:
                traffic_penalty += segment_distance * 3.0
            elif traffic_speed <= 25.0:
                traffic_penalty += segment_distance * 1.5

        priority = priorities.get(city, 1)
        priority_penalty += elapsed_time * (priority / 10) * 0.2
        

        if time_windows and city in time_windows:
            start, end = time_windows[city]

            if elapsed_time < start:
                time_penalty += (
                    start - elapsed_time
                ) * 1.5

            elif elapsed_time > end:
                time_penalty += (
                    elapsed_time - end
                ) * 8.0

    return (
        distance
        + priority_penalty
        + capacity_penalty
        + autonomy_penalty
        + time_penalty
        + traffic_penalty
    )


'''------------------------------------------------------------------
Divide a rota entre veiculos

Exemplo:
Veiculo 1 recebe posicoes 0, 3, 6
Veiculo 2 recebe posicoes 1, 4, 7
Veiculo 3 recebe posicoes 2, 5, 8
------------------------------------------------------------------'''
def split_route_by_vehicles(
    route: Route,
    n_vehicles: int
):
    routes = [
        []
        for _ in range(n_vehicles)
    ]

    for index, city in enumerate(route):
        vehicle_index = index % n_vehicles
        routes[vehicle_index].append(city)

    return routes

'''------------------------------------------------------------------
Fitness para multiplos veiculos.

Soma o custo das rotas individuais e adiciona uma penalidade para a maior rota.
Isso incentiva o balanceamento e reduz o tempo total da operacao.
------------------------------------------------------------------'''
def calculate_multi_vehicle_fitness(
    route: Route,
    fitness_function,
    n_vehicles: int = 3,
):
    vehicle_routes = split_route_by_vehicles(
        route,
        n_vehicles
    )

    route_costs = [
        fitness_function(vehicle_route)
        for vehicle_route in vehicle_routes
    ]

    total_cost = sum(route_costs)
    max_route_cost = max(route_costs)

    return total_cost + (max_route_cost * 2)

'''------------------------------------------------------------------
Calcula o tempo de uma rota individual de um veiculo.
------------------------------------------------------------------'''
def calculate_vehicle_route_time(route: Route) -> float:
    return calculate_route_time(route)

'''------------------------------------------------------------------
Calcula o tempo total considerando multiplos veiculos

Como os veiculos trabalham em paralelo, o tempo total da operacao eh o maior
tempo individual.
------------------------------------------------------------------'''
def calculate_operation_time(
    route: Route,
    n_vehicles: int = 3
) -> float:

    vehicle_routes = split_route_by_vehicles(
        route,
        n_vehicles
    )

    vehicle_times = [
        calculate_route_time(vehicle_route)
        for vehicle_route in vehicle_routes
        if len(vehicle_route) > 0
    ]

    if not vehicle_times:
        return 0.0

    return max(vehicle_times)