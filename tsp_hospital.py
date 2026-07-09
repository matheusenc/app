'''---------------------------------------------------------------------------------------
tsp_hospital.py

Arquivo principal do projeto.
Executa o Algoritmo Genetico para otimizar a rota de distribuicao de medicamentos
e insumos hospitalares na regiao central/expandida de Sao Paulo de hospitais da rede D'or.

---------------------------------------------------------------------------------------'''

import itertools
import random

import pygame
from pygame.locals import *

from genetic_algorithm import (
    calculate_fitness_fromMatrix,
    calculate_hospital_fitness,
    calculate_operation_time,
    calculate_route_time,
    generate_random_population_with_pre_ordering,
    generate_pre_ordering_population,
    generate_random_population,
    inversion_mutate,
    order_crossover,
    sort_population,
    split_route_by_vehicles,
    calculate_multi_vehicle_fitness,
    create_distance_matrix,
)

from scenario_randomizer import randomize_scenario

from hist import salvar_execucao

from draw_functions import draw_cities, draw_paths, draw_plot, draw_text, save_html_map
from hospital_data import hospital_locations, hospital_names, priorities, time_windows, weights

# Configuracoes do Pygame.
WIDTH, HEIGHT = 950, 620
NODE_RADIUS = 6
FPS = 30

# Parametros padrao do algoritmo. Eles podem ser alterados na tela inicial.
POPULATION_SIZE = 80
N_GENERATIONS = 1000
MAX_STAGNATION = 250

MUTATION_PROBABILITY = 0.25
VEHICLE_CAPACITY = 60
MAX_DISTANCE = 35
TOURNAMENT_SIZE = 7
N_VEHICLES = 3

# Cores.
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (255, 0, 0)
BLUE = (0, 0, 255)
GRAY = (128, 128, 128)
GREEN = (0, 120, 0)
LIGHT_GRAY = (220, 220, 220)
DARK_GRAY = (90, 90, 90)

VEHICLE_COLORS = [
    (255, 0, 0),      # Vermelho
    (0, 0, 255),      # Azul
    (0, 180, 0),      # Verde
    (255, 140, 0),    # Laranja
    (128, 0, 128),    # Roxo
    (0, 180, 180),    # Ciano
    (255, 0, 255),    # Magenta
    (165, 42, 42),    # Marrom
]

'''------------------------------------------------------------------
Componente simples de slider para alterar valores numericos com o mouse.
------------------------------------------------------------------'''
class Slider:

    def __init__(self, x, y, width, min_value, max_value, initial_value, step, label,):
        self.rect = pygame.Rect(x, y, width, 8)
        self.min_value = min_value
        self.max_value = max_value
        self.value = initial_value
        self.step = step
        self.label = label
        self.dragging = False

    def _value_to_x(self):
        percentage = (
            (self.value - self.min_value)
            / (self.max_value - self.min_value)
        )

        return self.rect.x + percentage * self.rect.width

    def _set_value_from_mouse(self, mouse_x):
        relative_x = max(
            0,
            min(mouse_x - self.rect.x, self.rect.width),
        )

        percentage = relative_x / self.rect.width

        raw_value = self.min_value + percentage * (
            self.max_value - self.min_value
        )

        stepped_value = round(raw_value / self.step) * self.step

        self.value = int(
            max(
                self.min_value,
                min(self.max_value, stepped_value),
            )
        )

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            knob_x = self._value_to_x()

            knob_rect = pygame.Rect(
                knob_x - 10,
                self.rect.y - 8,
                20,
                24,
            )

            if knob_rect.collidepoint(event.pos) or self.rect.collidepoint(event.pos):
                self.dragging = True
                self._set_value_from_mouse(event.pos[0])

        elif event.type == pygame.MOUSEBUTTONUP:
            self.dragging = False

        elif event.type == pygame.MOUSEMOTION and self.dragging:
            self._set_value_from_mouse(event.pos[0])

    def draw(self, screen):
        draw_text(
            screen,
            f"{self.label}: {self.value}",
            BLACK,
            position=(self.rect.x, self.rect.y - 25),
        )

        pygame.draw.rect(
            screen,
            LIGHT_GRAY,
            self.rect,
            border_radius=4,
        )

        filled_width = int(self._value_to_x() - self.rect.x)

        pygame.draw.rect(
            screen,
            GREEN,
            pygame.Rect(
                self.rect.x,
                self.rect.y,
                filled_width,
                self.rect.height,
            ),
            border_radius=4,
        )

        knob_x = int(self._value_to_x())

        pygame.draw.circle(
            screen,
            BLUE,
            (knob_x, self.rect.y + 4),
            10,
        )

'''------------------------------------------------------------------
Componente simples de Toogle para ativar Randow.
------------------------------------------------------------------'''
class Toggle:
    def __init__(self, x, y, width, height, initial_value=False, label=""):
        self.rect = pygame.Rect(x, y, width, height)
        self.value = initial_value
        self.label = label
        self.font = pygame.font.SysFont(None, 20)

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            if self.rect.collidepoint(event.pos):
                self.value = not self.value

    def draw(self, screen):
        # cor do botão
        color = (0, 120, 0) if self.value else (255, 0, 0)
        pygame.draw.rect(screen, color, self.rect, border_radius=10)

        # texto
        text = "ON" if self.value else "OFF"
        label_surface = self.font.render(f"{self.label}: {text}", True, (255, 255, 255))
        screen.blit(label_surface, (self.rect.x + 10, self.rect.y + 8))


'''------------------------------------------------------------------
Botoes para a tela de configuracao.
------------------------------------------------------------------'''
class Button:

    def __init__(self, x, y, width, height, text, background_color, text_color=WHITE):
        self.rect = pygame.Rect(x, y, width, height)
        self.text = text
        self.background_color = background_color
        self.text_color = text_color
        self.hover = False

    def handle_event(self, event):
        if event.type == pygame.MOUSEMOTION:
            self.hover = self.rect.collidepoint(event.pos)

        if event.type == pygame.MOUSEBUTTONDOWN:
            if self.rect.collidepoint(event.pos):
                return True

        return False

    def draw(self, screen):
        color = self.background_color

        if self.hover:
            color = (
                min(color[0] + 25, 255),
                min(color[1] + 25, 255),
                min(color[2] + 25, 255),
            )

        pygame.draw.rect(
            screen,
            color,
            self.rect,
            border_radius=8,
        )

        pygame.draw.rect(
            screen,
            DARK_GRAY,
            self.rect,
            width=2,
            border_radius=8,
        )

        pygame.font.init()
        font = pygame.font.SysFont("Arial", 16, bold=True)
        text_surface = font.render(self.text, True, self.text_color)
        text_rect = text_surface.get_rect(center=self.rect.center)
        screen.blit(text_surface, text_rect)

class RadioButton:
    def __init__(self, x, y, radius, value, label="", group=None):
        self.center = (x, y)
        self.radius = radius
        self.label = label
        self.group = group
        self.value = value
        self.font = pygame.font.SysFont(None, 20)

        # Rect usado só para clique (caixa ao redor do círculo)
        self.rect = pygame.Rect(x - radius, y - radius, radius * 2, radius * 2)

        if group is not None:
            group.add(self)

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            if self.rect.collidepoint(event.pos):
                if self.group:
                    self.group.select(self)

    def draw(self, screen):
        # círculo externo
        pygame.draw.circle(screen, (90, 90, 90), self.center, self.radius, 2)

        # preenchido se selecionado
        if self.group and self.group.selected == self:
            pygame.draw.circle(screen, (90, 90, 90), self.center, self.radius // 2)

        # texto ao lado
        label_surface = self.font.render(self.label, True, (90, 90, 90))
        screen.blit(label_surface, (self.center[0] + self.radius + 10, self.center[1] - 10))

class RadioGroup:
    def __init__(self):
        self.buttons = []
        self.selected = None

    def add(self, button):
        self.buttons.append(button)
        if self.selected is None:
            self.selected = button  # primeiro vira padrão

    def select(self, button):
        self.selected = button

    def get_selected_value(self):
        return self.selected.value if self.selected else None

'''------------------------------------------------------------------
Converte latitude/longitude para coordenadas de tela do Pygame.
------------------------------------------------------------------'''
def latlon_to_screen(lat, lon):
    
    min_lat = -23.7300   # parte sul: Sao Bernardo / Ribeirao Pires
    max_lat = -23.4500   # parte norte: Guarulhos

    min_lon = -46.8700   # oeste: Alphaville / Osasco
    max_lon = -46.4000   # leste: Maua / Ribeirao Pires

    margin = 40
    map_start_x = 420
    map_width = WIDTH - map_start_x - margin
    map_height = HEIGHT - (margin * 2)

    x = map_start_x + ((lon - min_lon) / (max_lon - min_lon)) * map_width
    y = margin + ((max_lat - lat) / (max_lat - min_lat)) * map_height

    return int(x), int(y)

'''------------------------------------------------------------------
Converte uma rota com latitude/longitude para pixels.
------------------------------------------------------------------'''
def convert_route_to_screen(route):

    return [latlon_to_screen(lat, lon) for lat, lon in route]

'''------------------------------------------------------------------
Seleciona um pai por torneio.
------------------------------------------------------------------'''
def tournament_selection(population, population_fitness, tournament_size, used):
    available_indices = [
        i for i in range(len(population))
        if i not in used
    ]

    chosen_indices = random.sample(available_indices, tournament_size)

    for i in chosen_indices:
        used.add(i)

    competitors = [
        (population[i], population_fitness[i], i)
        for i in chosen_indices
    ]

    winner = min(competitors, key=lambda x: x[1])
  
    return winner[0]

'''------------------------------------------------------------------
Cria a funcao de custo usando a quantidade de veiculos escolhida na tela inicial.
------------------------------------------------------------------'''
def make_hospital_cost(n_vehicles, matrix):

    def hospital_cost(route):
        """
        Calcula o custo da solucao com multiplos veiculos.
        """

        def single_vehicle_cost(r):
            return calculate_hospital_fitness(
                r,
                matrix,
                priorities,
                weights,
                VEHICLE_CAPACITY,
                MAX_DISTANCE,
                time_windows,
            )

        return calculate_multi_vehicle_fitness(
            route,
            single_vehicle_cost,
            n_vehicles,
        )

    return hospital_cost

'''------------------------------------------------------------------
 Calcula o fitness de todos os individuos.
------------------------------------------------------------------'''
def calculate_population_fitness(population, hospital_cost):
    return [hospital_cost(individual) for individual in population]


'''------------------------------------------------------------------
Formata minutos em horas e minutos.
------------------------------------------------------------------'''
def format_minutes(minutes):
    return f"{int(minutes // 60)}h {int(minutes % 60)}min"

'''------------------------------------------------------------------
Desenha a tela inicial de configuracao com sliders e botoes.
------------------------------------------------------------------'''
def draw_config_screen(screen, sliders, toggle_collision, radios, start_button, exit_button):
    screen.fill(WHITE)

    draw_text(screen, "CONFIGURACAO DO ALGORITMO", BLACK, position=(40, 35))
    draw_text(screen, "Arraste os controles abaixo e clique em INICIAR para executar.", BLACK,position=(40, 60))

    pygame.draw.rect(
        screen,
        (245, 245, 245),
        pygame.Rect(30, 95, 360, 400),
        border_radius=12,
    )

    pygame.draw.rect(
        screen,
        DARK_GRAY,
        pygame.Rect(30, 95, 360, 400),
        width=2,
        border_radius=12,
    )

    for slider in sliders:
        slider.draw(screen)

    toggle_collision.draw(screen)

    for radio in radios:
        radio.draw(screen)

    # dentro do loop:
    for event in pygame.event.get():
        for r in radios:
            r.handle_event(event)

    for r in radios:
        r.draw(screen)

    start_button.draw(screen)
    exit_button.draw(screen)


'''------------------------------------------------------------------
Tela inicial para alterar parametros antes de executar o algoritmo.
------------------------------------------------------------------'''
def configuration_screen(screen, clock):
    sliders = [
        Slider(
            x=55,
            y=130,
            width=290,
            min_value=1,
            max_value=8,
            initial_value=N_VEHICLES,
            step=1,
            label="Veiculos",
        ),
        Slider(
            x=55,
            y=180,
            width=290,
            min_value=50,
            max_value=500,
            initial_value=POPULATION_SIZE,
            step=10,
            label="Populacao",
        ),
        Slider(
            x=55,
            y=230,
            width=290,
            min_value=100,
            max_value=5000,
            initial_value=N_GENERATIONS,
            step=100,
            label="Geracoes maximas",
        ),
        Slider(
            x=55,
            y=280,
            width=290,
            min_value=100,
            max_value=4000,
            initial_value=MAX_STAGNATION,
            step=50,
            label="Sem melhora",
        ),
    ]

    toggle_collision = Toggle(
        x=55,
        y=310,
        width=290,
        height=30,
        initial_value=True,
        label="Manter Elitismo"
    )

    group = RadioGroup()

    radio1 = RadioButton(55, 370, 10, 100, "Inicialização Heuristica", group)
    radio2 = RadioButton(55, 395, 10, 0, "Inicialização Aleatória", group)
    radio3 = RadioButton(55, 420, 10, 50, "Inicialização Misturada", group)

    radios = [radio1, radio2, radio3]

    start_button = Button(
        x=55,
        y=450,
        width=135,
        height=38,
        text="INICIAR",
        background_color=GREEN,
    )

    exit_button = Button(
        x=210,
        y=450,
        width=135,
        height=38,
        text="SAIR",
        background_color=RED,
    )

    configuring = True

    while configuring:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                raise SystemExit

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN:
                    configuring = False

                elif event.key == pygame.K_ESCAPE:
                    pygame.quit()
                    raise SystemExit

            if start_button.handle_event(event):
                configuring = False

            if exit_button.handle_event(event):
                pygame.quit()
                raise SystemExit

            for slider in sliders:
                slider.handle_event(event)

            for radio in radios:
                radio.handle_event(event)

            toggle_collision.handle_event(event)

        draw_config_screen(screen, sliders, toggle_collision, radios, start_button, exit_button)
        pygame.display.flip()
        clock.tick(FPS)

    return {
        "N_VEHICLES": sliders[0].value,
        "POPULATION_SIZE": sliders[1].value,
        "N_GENERATIONS": sliders[2].value,
        "MAX_STAGNATION": sliders[3].value,
        "MANTER_ELITISMO" : toggle_collision.value,
        "TIPO_INICIALIZACAO" : group.get_selected_value(),
    }

'''------------------------------------------------------------------
Carrega o mapa de fundo, caso exista.
Se o arquivo nao existir, retorna None e o programa usa fundo branco.
------------------------------------------------------------------'''
def load_background_map():
    try:
        background_map = pygame.image.load("mapa.png")
        return pygame.transform.scale(
            background_map,
            (WIDTH - 420, HEIGHT),
        )
    except pygame.error:
        print("Aviso: arquivo mapa.png nao encontrado. Usando fundo branco.")
        return None



'''------------------------------------------------------------------
Função Principal.
------------------------------------------------------------------'''
def main():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Otimizacao de Rotas Hospitalares com Algoritmo Genetico")
    clock = pygame.time.Clock()

    config = configuration_screen(screen, clock)

    n_vehicles = config["N_VEHICLES"]
    population_size = config["POPULATION_SIZE"]
    n_generations = config["N_GENERATIONS"]
    max_stagnation = config["MAX_STAGNATION"]

    # # if config["ATIVAR_RANDOM"] :
    priorities_random, weights_random = randomize_scenario(
        hospital_locations, 
        priorities,
        weights,
        time_windows
        #seed=42  # seed opcional para reproducibilidade
    )
        
    priorities.update(priorities_random)
    weights.update(weights_random)
    time_windows.update(time_windows)

    points = list(hospital_names.keys())

    matrix = create_distance_matrix(points)

    hospital_cost = make_hospital_cost(n_vehicles, matrix)
    background_map = load_background_map()

    generation_counter = itertools.count(start=1)
    # cities_locations = hospital_names
    
    screen_locations = convert_route_to_screen(points)

    baseline_route = points.copy()
    baseline_fitness = hospital_cost(baseline_route)

    if config["TIPO_INICIALIZACAO"] == 100 : 
        population = generate_pre_ordering_population(points, population_size)
    elif  config["TIPO_INICIALIZACAO"] == 50 : 
        population = generate_random_population_with_pre_ordering(points, population_size)
    else:
        population = generate_random_population(points, population_size)
    
    population[0] = baseline_route

    best_fitness_values = []
    best_solutions = []

    best_global_fitness = float("inf")
    generations_without_improvement = 0

    running = True

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_q:
                running = False

        generation = next(generation_counter)

        if generation > n_generations:
            print("\nLimite maximo de geracoes atingido.")
            running = False
            break

        screen.fill(WHITE)

        if background_map:
            screen.blit(background_map, (420, 0))

        population_fitness = calculate_population_fitness(population, hospital_cost)
        population, population_fitness = sort_population(population, population_fitness)

        best_solution = population[0]
        best_fitness = population_fitness[0]

        if best_fitness < best_global_fitness:
            best_global_fitness = best_fitness
            generations_without_improvement = 0
        else:
            generations_without_improvement += 1

        best_fitness_values.append(best_fitness)
        best_solutions.append(best_solution)

        improvement = ((baseline_fitness - best_fitness) / baseline_fitness) * 100
        # best_solution_screen = convert_route_to_screen(best_solution)

        draw_plot(
            screen,
            list(range(len(best_fitness_values))),
            best_fitness_values,
            y_label="Custo da rota",
        )

        draw_cities(
            screen,
            screen_locations,
            BLACK,
            NODE_RADIUS
        )

        #desenha a rota dos veiculos para a melhorar solução
        vehicle_routes_current = split_route_by_vehicles(
            best_solution,
            n_vehicles
        )

        for vehicle_id, route in enumerate(vehicle_routes_current):
            if len(route) < 2:
                continue

            route_only = [city for city, _ in route]

            route_screen = convert_route_to_screen(route_only)

            color = VEHICLE_COLORS[
                vehicle_id % len(VEHICLE_COLORS)
            ]

            draw_paths(
                screen,
                route_screen,
                color,
                width=3
            )

        vehicle_routes_current = split_route_by_vehicles(
            population[1],
            n_vehicles
        )

        for vehicle_id, route in enumerate(vehicle_routes_current):
            if len(route) < 2:
                continue

            route_only = [city for city, _ in route]

            route_screen = convert_route_to_screen(route_only)

            color = VEHICLE_COLORS[
                vehicle_id % len(VEHICLE_COLORS)
            ]

            draw_paths(
                screen,
                route_screen,
                color,
                width=1
            )

        draw_text(screen, f"Geracao: {generation}/{n_generations}", BLACK, position=(20, 400))
        draw_text(screen, f"Veiculos: {n_vehicles}", BLACK, position=(20, 420))
        draw_text(screen, f"Populacao: {population_size}", BLACK, position=(20, 440))
        draw_text(screen, f"Custo baseline: {round(baseline_fitness, 2)}", BLACK, position=(20, 460))

        draw_text(screen, f"Sem melhora: {generations_without_improvement}/{max_stagnation}", BLACK, position=(200, 400))
        draw_text(screen, f"Melhor custo: {round(best_fitness, 2)}", BLACK, position=(200, 420))
        draw_text(screen, f"Melhoria: {round(improvement, 2)}%", GREEN, position=(200, 440))

        legend_y = 500
        legend_x = 20  
        aux = 1

        #desenha a legenda dos veiculos utilizados
        for vehicle_id in range(n_vehicles):
            if vehicle_id > 3:
                legend_x = 200 
                if aux > 3:
                    aux = 0
                    legend_y = 500

            color = VEHICLE_COLORS[
                vehicle_id % len(VEHICLE_COLORS)
            ]

            pygame.draw.rect(
                screen,
                color,
                (legend_x, legend_y, 18, 18)
            )

            draw_text(
                screen,
                f"Veiculo {vehicle_id + 1}",
                BLACK,
                position=(legend_x+25, legend_y - 2)
            )

            legend_y += 25   
            aux+1
        
        draw_text(screen, "Pressione Q para sair", BLACK, position=(200, 460))

        print(
            f"Geracao {generation}: Melhor custo = {round(best_fitness, 2)} "
            f"| Melhoria vs baseline = {round(improvement, 2)}% "
            f"| Sem melhora = {generations_without_improvement}/{max_stagnation}"
        )

        if generations_without_improvement >= max_stagnation:
            print(
                f"\nConvergencia atingida. "
                f"Sem melhoria nas ultimas {max_stagnation} geracoes."
            )
            running = False
            break

        if config["MANTER_ELITISMO"] :
            new_population = [population[0]]
        else :
            new_population = []

        while len(new_population) < population_size:
            used = set()

            parent1 = tournament_selection(
                population,
                population_fitness,
                TOURNAMENT_SIZE,
                used,
            )

            parent2 = tournament_selection(
                population,
                population_fitness,
                TOURNAMENT_SIZE,
                used,
            )

            forceMutation = False

            if generations_without_improvement > 100 or generations_without_improvement > max_stagnation * 0.50:
                forceMutation = True
                draw_text(screen, "Mutação Forte Ativada", RED, position=(200, 500))

            child = order_crossover(parent1, parent2)
            child = inversion_mutate(child, MUTATION_PROBABILITY, forceMutation)

            new_population.append(child)

        population = new_population

        pygame.display.flip()
        clock.tick(FPS)

    if not best_solutions:
        pygame.quit()
        return

    final_solution = best_solutions[-1]
    final_fitness = best_fitness_values[-1]
    final_distance = calculate_fitness_fromMatrix(final_solution, matrix, True)
    improvement = ((baseline_fitness - final_fitness) / baseline_fitness) * 100

    print("\n==============================")
    print("ROTA FINAL OTIMIZADA")
    print("==============================")

    vehicle_routes = split_route_by_vehicles(final_solution, n_vehicles)

    total_vehicle_distance = 0.0
    total_vehicle_time = 0.0
    vehicle_distances = []
    vehicle_times = []

    for vehicle_id, route in enumerate(vehicle_routes, start=1):
        route_distance = calculate_fitness_fromMatrix(route, matrix, False)
        route_time = calculate_route_time(matrix, route)

        total_vehicle_distance += route_distance
        total_vehicle_time += route_time

        vehicle_distances.append(route_distance)
        vehicle_times.append(route_time)

        print(f"\nVEICULO {vehicle_id}")
        print("-" * 30)

        for city in route:
            print(
                f"{hospital_names[city[0]]} "
                f"| Prioridade {priorities[city[0]]} "
                f"| Peso {weights[city[0]]}kg"
            )

        print(f"\nDistancia do veiculo {vehicle_id}: {round(route_distance, 2)} km")
        print(f"Tempo do veiculo {vehicle_id}: {round(route_time, 1)} min")
        print(f"Tempo formatado: {format_minutes(route_time)}")

    baseline_time = calculate_operation_time(
        matrix,
        baseline_route,
        n_vehicles,
    )

    final_time = calculate_operation_time(
        matrix,
        final_solution,
        n_vehicles,
    )

    time_reduction = (
        ((baseline_time - final_time) / baseline_time) * 100
        if baseline_time > 0
        else 0
    )

    max_vehicle_distance = max(vehicle_distances) if vehicle_distances else 0
    max_vehicle_time = max(vehicle_times) if vehicle_times else 0

    print("\n==============================")
    print("INDICADORES GERAIS")
    print("==============================")

    print(f"\nCusto da rota baseline: {round(baseline_fitness, 2)}")
    print(f"Custo da rota otimizada: {round(final_fitness, 2)}")

    print(f"\nDistancia da rota otimizada unica: {round(final_distance, 2)} km")
    print(f"Distancia total somada dos veiculos: {round(total_vehicle_distance, 2)} km")
    print(f"Maior distancia individual: {round(max_vehicle_distance, 2)} km")

    print(f"\nTempo baseline estimado da operacao: {round(baseline_time, 1)} min")
    print(f"Tempo otimizado estimado da operacao: {round(final_time, 1)} min")
    print(f"Tempo total somado dos veiculos: {round(total_vehicle_time, 1)} min")
    print(f"Maior tempo individual: {round(max_vehicle_time, 1)} min")

    print(f"\nTempo real estimado da operacao: {format_minutes(max_vehicle_time)}")
    print(f"Reducao de tempo vs baseline: {round(time_reduction, 2)}%")

    print(f"\nMelhoria vs baseline: {round(improvement, 2)}%")

       
    save_html_map(
        baseline_route,
        hospital_names,
        priorities,
        weights,
        output_path="mapa_baseline.html"
    )
    
    save_html_map(
        final_solution,
        hospital_names,
        priorities,
        weights,
        output_path="mapa_otimizado.html"
    )
    
    salvar_execucao(final_solution, 
                    baseline_route, 
                    hospital_names, 
                    priorities, 
                    weights, 
                    final_fitness, 
                    baseline_fitness, 
                    final_distance,
                    n_vehicles,
                    population_size,
                    n_generations,
                    MUTATION_PROBABILITY)

    print("\nArquivo prompt_llm.txt, mapa_baseline.html e mapa_otimizado.html gerados com sucesso.")

    pygame.quit()


if __name__ == "__main__":
    main()
