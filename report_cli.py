"""
report_cli.py

Menu interativo de linha de comando para:
  - Gerar instrucoes de motoristas (execucao atual ou historico)
  - Gerar relatorio executivo diario ou de periodo
  - Fazer perguntas em linguagem natural sobre as rotas (Q&A multi-turn)
  - Selecionar periodo por data, ultimos N dias ou dias especificos

Uso standalone:
    python report_cli.py

Ou chamado ao final do tsp_hospital.py apos salvar o historico:
    from report_cli import iniciar_menu
    iniciar_menu(execucao_atual={...})
"""

import os
import sys
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional, Tuple

from hist import (
    carregar_dia,
    carregar_intervalo,
    carregar_ultimos_dias,
    listar_dias_disponiveis,
    resumo_periodo,
)
from llm_integration import (
    LLMError,
    instrucoes_motoristas,
    relatorio_executivo,
    responder_pergunta,
)

Point = Tuple[float, float]

# ---------------------------------------------------------------------------
# Helpers de UI
# ---------------------------------------------------------------------------

LINHA  = "=" * 56
LINHA2 = "-" * 56


def _cls():
    os.system("cls" if os.name == "nt" else "clear")


def _titulo(texto: str):
    print(f"\n{LINHA}")
    print(f"  {texto}")
    print(LINHA)


def _opcao(n, texto):
    print(f"  [{n}] {texto}")


def _input(prompt: str) -> str:
    return input(f"\n  {prompt}: ").strip()


def _pausar():
    input("\n  Pressione ENTER para continuar...")


def _parse_data(texto: str) -> Optional[date]:
    """Tenta parsear data nos formatos DD/MM/YYYY ou YYYY-MM-DD."""
    for fmt in ("%d/%m/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(texto, fmt).date()
        except ValueError:
            continue
    return None


def _salvar_saida(conteudo: str, prefixo: str) -> str:
    """Salva o texto gerado em arquivo .txt com timestamp."""
    os.makedirs("reports", exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    filepath = os.path.join("reports", f"{prefixo}_{ts}.txt")
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(conteudo)
    return filepath


def _exibir_e_salvar(conteudo: str, prefixo: str):
    print(f"\n{LINHA2}")
    print(conteudo)
    print(LINHA2)
    caminho = _salvar_saida(conteudo, prefixo)
    print(f"\n  Salvo em: {caminho}")


# ---------------------------------------------------------------------------
# Seleção de período
# ---------------------------------------------------------------------------

def _menu_periodo() -> Optional[List[dict]]:
    """Exibe submenu de selecao de periodo e retorna os registros carregados."""
    _titulo("Selecionar Periodo")
    _opcao(1, "Hoje")
    _opcao(2, "Ultimos 7 dias")
    _opcao(3, "Ultimos 30 dias")
    _opcao(4, "Data especifica (DD/MM/AAAA)")
    _opcao(5, "Intervalo de datas")
    _opcao(6, "Escolher dias do historico")
    _opcao(0, "Voltar")

    escolha = _input("Opcao")

    if escolha == "0":
        return None

    if escolha == "1":
        registros = carregar_dia(date.today())

    elif escolha == "2":
        registros = carregar_ultimos_dias(7)

    elif escolha == "3":
        registros = carregar_ultimos_dias(30)

    elif escolha == "4":
        texto = _input("Data (DD/MM/AAAA ou YYYY-MM-DD)")
        d = _parse_data(texto)
        if not d:
            print("  Data invalida.")
            return None
        registros = carregar_dia(d)

    elif escolha == "5":
        inicio_txt = _input("Data de inicio (DD/MM/AAAA)")
        fim_txt    = _input("Data de fim    (DD/MM/AAAA)")
        inicio = _parse_data(inicio_txt)
        fim    = _parse_data(fim_txt)
        if not inicio or not fim or inicio > fim:
            print("  Datas invalidas.")
            return None
        registros = carregar_intervalo(inicio, fim)

    elif escolha == "6":
        dias = listar_dias_disponiveis()
        if not dias:
            print("  Nenhum historico encontrado.")
            return None
        print("\n  Dias disponíveis:")
        for i, d in enumerate(dias, start=1):
            print(f"    [{i}] {d}")
        selecionados = _input("Numeros dos dias (ex: 1,3,5)")
        registros = []
        for parte in selecionados.split(","):
            parte = parte.strip()
            if parte.isdigit():
                idx = int(parte) - 1
                if 0 <= idx < len(dias):
                    d = _parse_data(dias[idx])
                    if d:
                        registros.extend(carregar_dia(d))
        registros.sort(key=lambda r: r.get("timestamp", ""))

    else:
        print("  Opcao invalida.")
        return None

    if not registros:
        print("  Nenhum registro encontrado para o periodo selecionado.")
        return None

    print(f"\n  {len(registros)} execucao(oes) encontrada(s).")
    return registros


# ---------------------------------------------------------------------------
# Ações do menu
# ---------------------------------------------------------------------------

def _acao_instrucoes_motoristas(execucao_atual: Optional[dict]):
    _titulo("Instrucoes para Motoristas")

    if execucao_atual:
        _opcao(1, "Execucao atual (recem finalizada)")
        _opcao(2, "Selecionar do historico")
        _opcao(0, "Voltar")
        escolha = _input("Opcao")

        if escolha == "0":
            return
        if escolha == "1":
            registro = execucao_atual
        else:
            registros = _menu_periodo()
            if not registros:
                return
            # Usa a execucao mais recente do periodo
            registro = registros[-1]
    else:
        registros = _menu_periodo()
        if not registros:
            return
        registro = registros[-1]

    print("\n  Gerando instrucoes... aguarde.")
    try:
        from hist import deserializar_registro
        r = deserializar_registro(registro) if "rotas" in registro else registro

        resultado = instrucoes_motoristas(
            route=r["rotas"]["otimizada"],
            hospital_names=r["hospital_names"],
            priorities=r["priorities"],
            weights=r["weights"],
            n_vehicles=r["indicadores"]["n_vehicles"],
            baseline_fitness=r["indicadores"]["baseline_fitness"],
            best_fitness=r["indicadores"]["best_fitness"],
            final_distance=r["indicadores"]["final_distance_km"],
        )
        _exibir_e_salvar(resultado, "instrucoes_motoristas")
    except LLMError as e:
        print(f"\n  ERRO: {e}")

    _pausar()


def _acao_relatorio_executivo(execucao_atual: Optional[dict]):
    _titulo("Relatorio Executivo")
    _opcao(1, "Relatorio da execucao atual")
    _opcao(2, "Relatorio de periodo (semanal/mensal)")
    _opcao(0, "Voltar")

    escolha = _input("Opcao")
    if escolha == "0":
        return

    print("\n  Gerando relatorio... aguarde.")

    try:
        if escolha == "1":
            if not execucao_atual:
                print("  Nenhuma execucao atual disponivel. Use a opcao 2.")
                _pausar()
                return

            from hist import deserializar_registro
            r = deserializar_registro(execucao_atual) if "rotas" in execucao_atual else execucao_atual
            ind = r["indicadores"]

            resultado = relatorio_executivo(
                baseline_fitness=ind["baseline_fitness"],
                best_fitness=ind["best_fitness"],
                final_distance=ind["final_distance_km"],
                n_vehicles=ind["n_vehicles"],
            )
            _exibir_e_salvar(resultado, "relatorio_executivo_diario")

        elif escolha == "2":
            registros = _menu_periodo()
            if not registros:
                return

            res_periodo = resumo_periodo(registros)
            # Usa o indicador do primeiro registro como referencia
            primeiro = registros[0]["indicadores"]

            resultado = relatorio_executivo(
                baseline_fitness=res_periodo["baseline_medio"],
                best_fitness=res_periodo["custo"]["media"],
                final_distance=res_periodo["distancia_km"]["media"],
                n_vehicles=primeiro.get("n_vehicles", 1),
                resumo_periodo=res_periodo,
            )
            _exibir_e_salvar(resultado, "relatorio_executivo_periodo")

    except LLMError as e:
        print(f"\n  ERRO: {e}")

    _pausar()


def _acao_qa(execucao_atual: Optional[dict]):
    _titulo("Perguntas sobre as Rotas (Q&A)")
    print("  Selecione o contexto para as perguntas:")
    _opcao(1, "Execucao atual")
    _opcao(2, "Periodo do historico")
    _opcao(0, "Voltar")

    escolha = _input("Opcao")
    if escolha == "0":
        return

    if escolha == "1" and execucao_atual:
        registros = [execucao_atual]
    else:
        registros = _menu_periodo()
        if not registros:
            return

    print(f"\n  Contexto carregado: {len(registros)} execucao(oes).")
    print("  Digite sua pergunta ou 'sair' para voltar ao menu.\n")

    conversa: Optional[List[dict]] = None

    while True:
        pergunta = _input("Voce")
        if pergunta.lower() in ("sair", "exit", "q"):
            break
        if not pergunta:
            continue

        print("  ...\n")
        try:
            resposta, conversa = responder_pergunta(
                pergunta=pergunta,
                historico_registros=registros,
                conversa=conversa,
            )
            print(f"  IA: {resposta}\n")
        except LLMError as e:
            print(f"  ERRO: {e}\n")
            conversa = None  # Reinicia conversa em caso de erro


def _acao_ver_historico():
    _titulo("Historico Disponivel")
    dias = listar_dias_disponiveis()
    if not dias:
        print("  Nenhum historico encontrado na pasta 'historico/'.")
    else:
        print(f"  {len(dias)} dia(s) com dados:\n")
        for d in dias:
            registros = carregar_dia(
                datetime.strptime(d, "%Y-%m-%d").date()
            )
            custo_medio = sum(
                r["indicadores"]["best_fitness"] for r in registros
            ) / len(registros)
            melhoria_media = sum(
                r["indicadores"]["improvement_pct"] for r in registros
            ) / len(registros)
            print(
                f"  {d}  |  {len(registros)} exec  |  "
                f"Custo medio: {round(custo_medio, 2)}  |  "
                f"Melhoria media: {round(melhoria_media, 2)}%"
            )
    _pausar()


# ---------------------------------------------------------------------------
# Menu principal
# ---------------------------------------------------------------------------

def iniciar_menu(execucao_atual: Optional[dict] = None):
    """
    Ponto de entrada do CLI.

    execucao_atual: dict no formato de registro do historico.py,
                    representando a execucao recem finalizada (opcional).
    """
    while True:
        _cls()
        _titulo("Sistema de Relatorios — Rotas Hospitalares")

        if execucao_atual:
            ind = execucao_atual.get("indicadores", {})
            print(
                f"  Execucao atual: custo {ind.get('best_fitness', 'N/A')} | "
                f"melhoria {ind.get('improvement_pct', 'N/A')}%\n"
            )

        _opcao(1, "Instrucoes para motoristas")
        _opcao(2, "Relatorio executivo")
        _opcao(3, "Perguntas sobre as rotas (Q&A)")
        _opcao(4, "Ver historico disponivel")
        _opcao(0, "Sair")

        escolha = _input("Opcao")

        if escolha == "0":
            print("\n  Encerrando.\n")
            break
        elif escolha == "1":
            _acao_instrucoes_motoristas(execucao_atual)
        elif escolha == "2":
            _acao_relatorio_executivo(execucao_atual)
        elif escolha == "3":
            _acao_qa(execucao_atual)
        elif escolha == "4":
            _acao_ver_historico()
        else:
            print("  Opcao invalida.")


# ---------------------------------------------------------------------------
# Execucao standalone (sem execucao_atual)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    iniciar_menu()