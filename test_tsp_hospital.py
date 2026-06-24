"""
test_tsp_hospital.py

Testes automatizados para validacao das funcionalidades do projeto.

Cobertura:
  - genetic_algorithm.py : distancia, fitness, crossover, mutacao, populacao, veiculos
  - scenario_randomizer.py: ranges, garantias de criticos, reproducibilidade com seed
  - hist.py              : serialização, salvar, carregar, resumo de periodo

Execute com:
    pytest test_tsp_hospital.py -v
"""

import json
import math
import os
import random
import tempfile
from datetime import date
from typing import Dict, List, Tuple

import pytest

# ---------------------------------------------------------------------------
# Imports do projeto
# ---------------------------------------------------------------------------
import sys
sys.path.insert(0, os.path.dirname(__file__))

from genetic_algorithm import (
    calculate_distance,
    calculate_fitness,
    calculate_hospital_fitness,
    calculate_multi_vehicle_fitness,
    calculate_operation_time,
    calculate_route_time,
    generate_random_population,
    generate_random_population_with_pre_ordering,
    inversion_mutate,
    mutate,
    order_crossover,
    sort_population,
    split_route_by_vehicles,
)
from scenario_randomizer import randomize_scenario
from hospital_data import hospital_locations, priorities, weights, time_windows

# ---------------------------------------------------------------------------
# Fixtures compartilhadas
# ---------------------------------------------------------------------------

ROTA_SIMPLES = [
    (-23.6756, -46.5262),
    (-23.6637, -46.5255),
    (-23.6678, -46.4614),
    (-23.7069, -46.5554),
]

PRIORITIES_SIMPLES = {p: (i % 10) + 1 for i, p in enumerate(ROTA_SIMPLES)}
WEIGHTS_SIMPLES    = {p: 15 + i * 3  for i, p in enumerate(ROTA_SIMPLES)}


# ===========================================================================
# 1. calculate_distance
# ===========================================================================

class TestCalculateDistance:

    def test_mesmos_pontos_retorna_zero(self):
        p = (-23.5, -46.6)
        assert calculate_distance(p, p) == pytest.approx(0.0, abs=1e-6)

    def test_distancia_positiva(self):
        p1 = (-23.6756, -46.5262)
        p2 = (-23.6637, -46.5255)
        assert calculate_distance(p1, p2) > 0

    def test_simetria(self):
        p1 = (-23.6756, -46.5262)
        p2 = (-23.4553, -46.5430)
        assert calculate_distance(p1, p2) == pytest.approx(
            calculate_distance(p2, p1), rel=1e-6
        )

    def test_distancia_conhecida_aproximada(self):
        # Santo Andre → Guarulhos: ~25km em linha reta
        santo_andre = (-23.6756, -46.5262)
        guarulhos   = (-23.4553, -46.5430)
        dist = calculate_distance(santo_andre, guarulhos)
        assert 20 < dist < 35, f"Distancia inesperada: {dist:.2f} km"

    def test_formula_haversine_manual(self):
        # Dois pontos a ~1 grau de latitude ≈ 111 km
        p1 = (0.0, 0.0)
        p2 = (1.0, 0.0)
        dist = calculate_distance(p1, p2)
        assert 110 < dist < 112


# ===========================================================================
# 2. calculate_fitness (distância total da rota fechada)
# ===========================================================================

class TestCalculateFitness:

    def test_rota_vazia_retorna_zero(self):
        assert calculate_fitness([]) == 0.0

    def test_rota_um_ponto_retorna_zero(self):
        assert calculate_fitness([(-23.5, -46.6)]) == 0.0

    def test_rota_fechada_maior_que_aberta(self):
        # Rota fechada inclui o retorno ao ponto inicial
        rota = ROTA_SIMPLES
        dist_fechada = calculate_fitness(rota)
        dist_aberta  = sum(
            calculate_distance(rota[i], rota[i+1])
            for i in range(len(rota) - 1)
        )
        assert dist_fechada > dist_aberta

    def test_todas_cidades_incluidas(self):
        dist = calculate_fitness(hospital_locations)
        assert dist > 0

    def test_ordem_diferente_gera_distancia_diferente(self):
        rota1 = list(hospital_locations)
        rota2 = list(reversed(hospital_locations))
        # Rota invertida pode ter mesma distância (ciclo) — mas embaralhada não
        rota3 = rota1[:]
        random.shuffle(rota3)
        # Ao menos uma das duas deve diferir
        assert not (
            calculate_fitness(rota1) == calculate_fitness(rota2) ==
            calculate_fitness(rota3)
        )


# ===========================================================================
# 3. calculate_hospital_fitness
# ===========================================================================

class TestCalculateHospitalFitness:

    def test_retorna_float_positivo(self):
        f = calculate_hospital_fitness(
            ROTA_SIMPLES, PRIORITIES_SIMPLES, WEIGHTS_SIMPLES
        )
        assert isinstance(f, float)
        assert f > 0

    def test_penalidade_capacidade_excedida(self):
        # Peso total muito acima da capacidade
        weights_pesados = {p: 100 for p in ROTA_SIMPLES}
        f_pesado = calculate_hospital_fitness(
            ROTA_SIMPLES, PRIORITIES_SIMPLES, weights_pesados,
            vehicle_capacity=10
        )
        f_normal = calculate_hospital_fitness(
            ROTA_SIMPLES, PRIORITIES_SIMPLES, WEIGHTS_SIMPLES,
            vehicle_capacity=500
        )
        assert f_pesado > f_normal

    def test_penalidade_autonomia_excedida(self):
        # max_distance muito baixo → deve penalizar
        f_restrito = calculate_hospital_fitness(
            hospital_locations, priorities, weights,
            max_distance=1
        )
        f_livre = calculate_hospital_fitness(
            hospital_locations, priorities, weights,
            max_distance=9999
        )
        assert f_restrito > f_livre

    def test_criticos_no_inicio_melhor_que_no_final(self):
        """Hospital prioridade 10 visitado primeiro deve gerar fitness menor."""
        p_alta  = (-23.6756, -46.5262)
        p_baixa = (-23.7102, -46.4145)
        prios = {p_alta: 10, p_baixa: 2}
        wts   = {p_alta: 10, p_baixa: 10}

        rota_boa  = [p_alta,  p_baixa]
        rota_ruim = [p_baixa, p_alta]

        f_boa  = calculate_hospital_fitness(rota_boa,  prios, wts)
        f_ruim = calculate_hospital_fitness(rota_ruim, prios, wts)
        assert f_boa < f_ruim

    def test_penalidade_janela_horario_violada(self):
        p = ROTA_SIMPLES[0]
        # Janela impossível de cumprir no início (já passou)
        tw_violada = {p: (0, 1)}
        f_com_janela = calculate_hospital_fitness(
            ROTA_SIMPLES, PRIORITIES_SIMPLES, WEIGHTS_SIMPLES,
            time_windows=tw_violada
        )
        f_sem_janela = calculate_hospital_fitness(
            ROTA_SIMPLES, PRIORITIES_SIMPLES, WEIGHTS_SIMPLES
        )
        assert f_com_janela >= f_sem_janela


# ===========================================================================
# 4. order_crossover
# ===========================================================================

class TestOrderCrossover:

    def test_filho_tem_mesmos_genes_que_pais(self):
        pai1 = list(hospital_locations)
        pai2 = list(reversed(hospital_locations))
        filho = order_crossover(pai1, pai2)
        assert sorted(filho) == sorted(pai1)

    def test_filho_sem_duplicatas(self):
        pai1 = list(hospital_locations)
        pai2 = list(reversed(hospital_locations))
        filho = order_crossover(pai1, pai2)
        assert len(filho) == len(set(filho))

    def test_filho_tem_tamanho_correto(self):
        pai1 = list(hospital_locations)
        pai2 = list(reversed(hospital_locations))
        filho = order_crossover(pai1, pai2)
        assert len(filho) == len(pai1)

    def test_crossover_deterministico_com_seed(self):
        random.seed(42)
        pai1 = list(hospital_locations)
        pai2 = list(reversed(hospital_locations))
        filho1 = order_crossover(pai1, pai2)

        random.seed(42)
        filho2 = order_crossover(pai1, pai2)
        assert filho1 == filho2


# ===========================================================================
# 5. mutate e inversion_mutate
# ===========================================================================

class TestMutate:

    def test_swap_preserva_genes(self):
        rota = list(hospital_locations)
        mutada = mutate(rota, mutation_probability=1.0)
        assert sorted(mutada) == sorted(rota)

    def test_swap_probabilidade_zero_nao_muta(self):
        rota = list(hospital_locations)
        mutada = mutate(rota, mutation_probability=0.0)
        assert mutada == rota

    def test_inversion_preserva_genes(self):
        rota = list(hospital_locations)
        mutada = inversion_mutate(rota, mutation_probability=1.0)
        assert sorted(mutada) == sorted(rota)

    def test_inversion_probabilidade_zero_nao_muta(self):
        rota = list(hospital_locations)
        mutada = inversion_mutate(rota, mutation_probability=0.0)
        assert mutada == rota

    def test_inversion_tamanho_preservado(self):
        rota = list(hospital_locations)
        mutada = inversion_mutate(rota, mutation_probability=1.0)
        assert len(mutada) == len(rota)

    def test_original_nao_e_modificado(self):
        rota = list(hospital_locations)
        original = rota[:]
        inversion_mutate(rota, mutation_probability=1.0)
        assert rota == original


# ===========================================================================
# 6. sort_population
# ===========================================================================

class TestSortPopulation:

    def test_ordena_por_fitness_crescente(self):
        pop = [ROTA_SIMPLES, list(reversed(ROTA_SIMPLES))]
        fit = [100.0, 50.0]
        pop_s, fit_s = sort_population(pop, fit)
        assert fit_s == sorted(fit)

    def test_populacao_e_fitness_permanecem_alinhados(self):
        pop = [ROTA_SIMPLES, list(reversed(ROTA_SIMPLES))]
        fit = [999.0, 1.0]
        pop_s, fit_s = sort_population(pop, fit)
        assert fit_s[0] == 1.0
        assert pop_s[0] == list(reversed(ROTA_SIMPLES))


# ===========================================================================
# 7. split_route_by_vehicles
# ===========================================================================

class TestSplitRouteByVehicles:

    def test_total_de_cidades_preservado(self):
        for n in [1, 2, 3, 4]:
            rotas = split_route_by_vehicles(hospital_locations, n)
            total = sum(len(r) for r in rotas)
            assert total == len(hospital_locations)

    def test_numero_de_veiculos_correto(self):
        rotas = split_route_by_vehicles(hospital_locations, 3)
        assert len(rotas) == 3

    def test_distribuicao_round_robin(self):
        rota = list(range(6))
        rotas = split_route_by_vehicles(rota, 3)
        assert rotas[0] == [0, 3]
        assert rotas[1] == [1, 4]
        assert rotas[2] == [2, 5]

    def test_um_veiculo_recebe_tudo(self):
        rotas = split_route_by_vehicles(hospital_locations, 1)
        assert rotas[0] == list(hospital_locations)


# ===========================================================================
# 8. generate_random_population
# ===========================================================================

class TestGenerateRandomPopulation:

    def test_tamanho_da_populacao(self):
        pop = generate_random_population(hospital_locations, 50)
        assert len(pop) == 50

    def test_cada_individuo_tem_todas_cidades(self):
        pop = generate_random_population(hospital_locations, 10)
        for individuo in pop:
            assert sorted(individuo) == sorted(hospital_locations)

    def test_individuos_sem_duplicatas(self):
        pop = generate_random_population(hospital_locations, 10)
        for individuo in pop:
            assert len(individuo) == len(set(individuo))

    def test_populacao_com_pre_ordenacao(self):
        pop = generate_random_population_with_pre_ordering(hospital_locations, 20)
        assert len(pop) == 20
        for individuo in pop:
            assert sorted(individuo) == sorted(hospital_locations)


# ===========================================================================
# 9. calculate_route_time e calculate_operation_time
# ===========================================================================

class TestRouteTimes:

    def test_rota_vazia_retorna_zero(self):
        assert calculate_route_time([]) == 0.0

    def test_rota_com_um_ponto_retorna_zero(self):
        assert calculate_route_time([(-23.5, -46.6)]) == 0.0

    def test_tempo_positivo_para_rota_valida(self):
        t = calculate_route_time(hospital_locations)
        assert t > 0

    def test_operation_time_paralelo_menor_que_serial(self):
        """Com múltiplos veículos em paralelo, o tempo deve ser menor."""
        t1 = calculate_operation_time(hospital_locations, n_vehicles=1)
        t4 = calculate_operation_time(hospital_locations, n_vehicles=4)
        assert t4 < t1

    def test_operation_time_um_veiculo(self):
        t1_op   = calculate_operation_time(hospital_locations, n_vehicles=1)
        t1_rota = calculate_route_time(hospital_locations)
        assert t1_op == pytest.approx(t1_rota, rel=1e-4)


# ===========================================================================
# 10. scenario_randomizer
# ===========================================================================

class TestScenarioRandomizer:

    def test_tamanho_dos_dicts(self):
        prios, wts = randomize_scenario(hospital_locations)
        assert len(prios) == len(hospital_locations)
        assert len(wts)   == len(hospital_locations)

    def test_prioridades_dentro_do_range(self):
        prios, _ = randomize_scenario(hospital_locations)
        for v in prios.values():
            assert 1 <= v <= 10, f"Prioridade fora do range: {v}"

    def test_pesos_dentro_do_range(self):
        _, wts = randomize_scenario(hospital_locations)
        for v in wts.values():
            assert 5 <= v <= 40, f"Peso fora do range: {v}"

    def test_garante_dois_criticos(self):
        prios, _ = randomize_scenario(hospital_locations)
        n_criticos = sum(1 for v in prios.values() if v == 10)
        assert n_criticos >= 2

    def test_reproducibilidade_com_seed(self):
        p1, w1 = randomize_scenario(hospital_locations, seed=42)
        p2, w2 = randomize_scenario(hospital_locations, seed=42)
        assert p1 == p2
        assert w1 == w2

    def test_seeds_diferentes_geram_resultados_diferentes(self):
        p1, _ = randomize_scenario(hospital_locations, seed=1)
        p2, _ = randomize_scenario(hospital_locations, seed=99)
        assert p1 != p2

    def test_oscila_em_torno_da_base(self):
        base_prios = {p: 8 for p in hospital_locations}
        base_wts   = {p: 20 for p in hospital_locations}
        prios, wts = randomize_scenario(
            hospital_locations,
            base_priorities=base_prios,
            base_weights=base_wts,
            seed=0
        )
        # Maioria dos valores deve estar próxima da base (exceto os 2 críticos forçados)
        proximos_prio = sum(
            1 for p in hospital_locations
            if abs(prios[p] - 8) <= 2
        )
        assert proximos_prio >= len(hospital_locations) - 4

        proximos_peso = sum(
            1 for p in hospital_locations
            if 14 <= wts[p] <= 26  # ±30% de 20
        )
        assert proximos_peso >= len(hospital_locations) - 2


# ===========================================================================
# 11. hist.py — persistência
# ===========================================================================

class TestHist:

    @pytest.fixture(autouse=True)
    def tmp_hist_dir(self, monkeypatch, tmp_path):
        """Redireciona o diretório de histórico para um temporário."""
        import hist as h
        monkeypatch.setattr(h, "HISTORICO_DIR", str(tmp_path / "hist"))
        return tmp_path

    def _registro_base(self):
        pts = hospital_locations[:4]
        names = {p: f"Hospital {i}" for i, p in enumerate(pts)}
        prios = {p: 8 for p in pts}
        wts   = {p: 20 for p in pts}
        return pts, names, prios, wts

    def test_salvar_cria_arquivo(self, tmp_hist_dir):
        from hist import salvar_execucao
        pts, names, prios, wts = self._registro_base()
        caminho = salvar_execucao(
            pts, pts, names, prios, wts,
            1000.0, 900.0, 50.0, 1, 80, 500, 0.25,
            data=date(2025, 6, 20)
        )
        assert os.path.exists(caminho)

    def test_carregar_dia_retorna_lista(self, tmp_hist_dir):
        from hist import salvar_execucao, carregar_dia
        pts, names, prios, wts = self._registro_base()
        salvar_execucao(
            pts, pts, names, prios, wts,
            1000.0, 900.0, 50.0, 1, 80, 500, 0.25,
            data=date(2025, 6, 20)
        )
        registros = carregar_dia(date(2025, 6, 20))
        assert len(registros) == 1
        assert registros[0]["data"] == "2025-06-20"

    def test_multiplas_execucoes_mesmo_dia(self, tmp_hist_dir):
        from hist import salvar_execucao, carregar_dia
        pts, names, prios, wts = self._registro_base()
        for fitness in [900.0, 850.0, 880.0]:
            salvar_execucao(
                pts, pts, names, prios, wts,
                1000.0, fitness, 50.0, 1, 80, 500, 0.25,
                data=date(2025, 6, 21)
            )
        registros = carregar_dia(date(2025, 6, 21))
        assert len(registros) == 3

    def test_improvement_calculado_corretamente(self, tmp_hist_dir):
        from hist import salvar_execucao, carregar_dia
        pts, names, prios, wts = self._registro_base()
        salvar_execucao(
            pts, pts, names, prios, wts,
            1000.0, 800.0, 50.0, 1, 80, 500, 0.25,
            data=date(2025, 6, 22)
        )
        r = carregar_dia(date(2025, 6, 22))[0]
        assert r["indicadores"]["improvement_pct"] == pytest.approx(20.0, rel=1e-4)

    def test_deserializar_converte_pontos(self, tmp_hist_dir):
        from hist import salvar_execucao, carregar_dia, deserializar_registro
        pts, names, prios, wts = self._registro_base()
        salvar_execucao(
            pts, pts, names, prios, wts,
            1000.0, 900.0, 50.0, 1, 80, 500, 0.25,
            data=date(2025, 6, 23)
        )
        r = carregar_dia(date(2025, 6, 23))[0]
        rd = deserializar_registro(r)
        # Chaves devem ser tuplas novamente
        for k in rd["hospital_names"]:
            assert isinstance(k, tuple)

    def test_resumo_periodo_calcula_corretamente(self, tmp_hist_dir):
        from hist import salvar_execucao, carregar_intervalo, resumo_periodo
        pts, names, prios, wts = self._registro_base()
        salvar_execucao(pts, pts, names, prios, wts,
                        1000.0, 900.0, 50.0, 1, 80, 500, 0.25,
                        data=date(2025, 6, 20))
        salvar_execucao(pts, pts, names, prios, wts,
                        1000.0, 800.0, 40.0, 1, 80, 500, 0.25,
                        data=date(2025, 6, 21))

        registros = carregar_intervalo(date(2025, 6, 20), date(2025, 6, 21))
        res = resumo_periodo(registros)

        assert res["total_execucoes"] == 2
        assert res["custo"]["minimo"] == 800.0
        assert res["custo"]["maximo"] == 900.0
        assert res["custo"]["media"]  == pytest.approx(850.0)
        assert res["distancia_km"]["minima"] == 40.0

    def test_listar_dias_disponiveis(self, tmp_hist_dir):
        from hist import salvar_execucao, listar_dias_disponiveis
        pts, names, prios, wts = self._registro_base()
        for d in [date(2025, 6, 20), date(2025, 6, 22)]:
            salvar_execucao(pts, pts, names, prios, wts,
                            1000.0, 900.0, 50.0, 1, 80, 500, 0.25, data=d)
        dias = listar_dias_disponiveis()
        assert "2025-06-20" in dias
        assert "2025-06-22" in dias
        assert "2025-06-21" not in dias