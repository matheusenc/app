"""
draw_functions.py

Funcoes responsaveis pela visualizacao grafica do projeto.
Este arquivo foi baseado no material da aula com Pygame e Matplotlib.

A tela mostra:
- grafico de evolucao do custo ao longo das geracoes;
- pontos das unidades hospitalares;
- melhor rota encontrada pelo algoritmo.
"""

import matplotlib

# Usa o backend Agg para desenhar o grafico em memoria e depois enviar para o Pygame.
# Isso evita abrir uma janela separada do Matplotlib.
matplotlib.use("Agg")

import matplotlib.pyplot as plt
from matplotlib.backends.backend_agg import FigureCanvasAgg
import pygame

import folium



def draw_plot(screen, x, y, x_label="Generation", y_label="Fitness"):
    """
    Desenha o grafico de evolucao do algoritmo.

    Eixo X: geracao.
    Eixo Y: custo da melhor rota.

    Se o algoritmo estiver melhorando, a tendencia e o custo diminuir ao longo das geracoes.
    """
    fig, ax = plt.subplots(figsize=(4, 4), dpi=100)

    ax.plot(x, y)
    ax.set_ylabel(y_label)
    ax.set_xlabel(x_label)
    plt.tight_layout()

    # Converte o grafico do Matplotlib para uma imagem que o Pygame consegue exibir.
    canvas = FigureCanvasAgg(fig)
    canvas.draw()
    raw_data = canvas.buffer_rgba()
    size = canvas.get_width_height()

    surf = pygame.image.frombuffer(raw_data, size, "RGBA")
    screen.blit(surf, (0, 0))

    # Fecha a figura para evitar consumo excessivo de memoria.
    plt.close(fig)


def draw_cities(screen, cities_locations, rgb_color, node_radius):
    """
    Desenha os pontos de entrega na tela.

    Cada ponto vermelho representa uma unidade hospitalar, UBS, farmacia ou atendimento domiciliar.
    """
    for city_location in cities_locations:
        pygame.draw.circle(screen, rgb_color, city_location, node_radius)


def draw_paths(screen, path, rgb_color, width=1):
    """
    Desenha a rota entre os pontos.

    A linha azul representa a melhor rota da geracao atual.
    A opcao True em pygame.draw.lines fecha o ciclo, ligando o ultimo ponto ao primeiro.
    """
    if len(path) > 1:
        pygame.draw.lines(screen, rgb_color, True, path, width=width)


def draw_text(screen, text, color, position=(10, 10)):
    """
    Escreve informacoes na tela do Pygame.

    Usado para mostrar geracao atual, custo inicial, melhor custo e percentual de melhoria.
    """
    pygame.font.init()
    my_font = pygame.font.SysFont("Arial", 15)
    text_surface = my_font.render(text, False, color)
    screen.blit(text_surface, position)

def save_html_map(
    route,
    hospital_names,
    priorities,
    weights,
    output_path="resultado_final.html"
):
    route_closed = route + [route[0]]

    center_lat = sum(p[0] for p in route) / len(route)
    center_lon = sum(p[1] for p in route) / len(route)

    m = folium.Map(location=[center_lat, center_lon], zoom_start=12)

    # Linha da rota
    folium.PolyLine(
        route_closed,
        color="blue",
        weight=3,
        opacity=0.8,
        tooltip="Rota otimizada"
    ).add_to(m)

    # Marcadores por hospital
    for i, point in enumerate(route):
        name     = hospital_names.get(point, str(point))
        priority = priorities.get(point, "-")
        weight   = weights.get(point, "-")

        # Ponto inicial e final em verde, demais em vermelho
        if i == 0:
            icon = folium.Icon(color="green", icon="play", prefix="fa")
            label = "INÍCIO"
        elif i == len(route) - 1:
            icon = folium.Icon(color="green", icon="plus-sign", prefix="glyphicon")
            label = "FIM"
        else:
            icon = folium.Icon(color="red", icon="plus-sign", prefix="glyphicon")
            label = f"Parada {i}"

        popup_html = f"""
        <div style="font-family:Arial; min-width:180px">
            <b>{name}</b><br>
            <hr style="margin:4px 0">
            {label}<br>
            Prioridade: <b>{priority}</b><br>
            Peso: <b>{weight}kg</b>
        </div>
        """

        folium.Marker(
            location=[point[0], point[1]],
            tooltip=f"{i if i > 0 else '★'} — {name} (P{priority})",
            popup=folium.Popup(popup_html, max_width=220),
            icon=icon,
        ).add_to(m)

    m.save(output_path)
