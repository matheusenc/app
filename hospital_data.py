'''---------------------------------------------------------------------------------------
hospital_data.py

Dados do problema de roteirizacao hospitalar usando unidades da Rede D'Or
na Grande Sao Paulo e ABC.

Observacao:
- Os hospitais e enderecos foram baseados na lista publica de unidades da Rede D'Or.
- As coordenadas sao aproximadas.
---------------------------------------------------------------------------------------'''
hospital_locations = [
    (-23.6756, -46.5262),  # Hospital Bartira - Santo Andre
    (-23.6637, -46.5255),  # Hospital e Maternidade Brasil - Santo Andre
    (-23.6678, -46.4614),  # Hospital Brasil Maua - Maua
    (-23.7069, -46.5554),  # Hospital IFOR - Sao Bernardo
    (-23.7133, -46.5467),  # Hospital Sao Luiz Sao Bernardo
    (-23.6226, -46.5712),  # Hospital Sao Luiz Sao Caetano
    (-23.4932, -46.8499),  # Hospital Sao Luiz Alphaville - Barueri
    (-23.5856, -46.6786),  # Hospital Sao Luiz Itaim
    (-23.6438, -46.6422),  # Hospital Sao Luiz Jabaquara
    (-23.5908, -46.7156),  # Hospital Sao Luiz Morumbi
    (-23.5605, -46.5882),  # Hospital Villa Lobos - Mooca
    (-23.5601, -46.5582),  # Hospital Sao Luiz Analia Franco
    (-23.4553, -46.5430),  # Hospital Sao Luiz Guarulhos
    (-23.5327, -46.7797),  # Hospital Sao Luiz Osasco
    (-23.6436, -46.6414),  # Hospital da Crianca - Jabaquara
    (-23.7102, -46.4145),  # Hospital e Maternidade Ribeirao Pires
]

hospital_names = {
    (-23.6756, -46.5262): "Hospital Bartira - Santo Andre",
    (-23.6637, -46.5255): "Hospital e Maternidade Brasil - Santo Andre",
    (-23.6678, -46.4614): "Hospital Brasil Maua",
    (-23.7069, -46.5554): "Hospital IFOR - Sao Bernardo",
    (-23.7133, -46.5467): "Hospital Sao Luiz Sao Bernardo",
    (-23.6226, -46.5712): "Hospital Sao Luiz Sao Caetano",
    (-23.4932, -46.8499): "Hospital Sao Luiz Alphaville",
    (-23.5856, -46.6786): "Hospital Sao Luiz Itaim",
    (-23.6438, -46.6422): "Hospital Sao Luiz Jabaquara",
    (-23.5908, -46.7156): "Hospital Sao Luiz Morumbi",
    (-23.5605, -46.5882): "Hospital Villa Lobos",
    (-23.5601, -46.5582): "Hospital Sao Luiz Analia Franco",
    (-23.4553, -46.5430): "Hospital Sao Luiz Guarulhos",
    (-23.5327, -46.7797): "Hospital Sao Luiz Osasco",
    (-23.6436, -46.6414): "Hospital da Crianca",
    (-23.7102, -46.4145): "Hospital e Maternidade Ribeirao Pires",
}

hospital = {
    (-23.6756, -46.5262): 0,
    (-23.6637, -46.5255): 1,
    (-23.6678, -46.4614): 2,
    (-23.7069, -46.5554): 3,
    (-23.7133, -46.5467): 4,
    (-23.6226, -46.5712): 5,
    (-23.4932, -46.8499): 6,
    (-23.5856, -46.6786): 7,
    (-23.6438, -46.6422): 8,
    (-23.5908, -46.7156): 9,
    (-23.5605, -46.5882): 10,
    (-23.5601, -46.5582): 11,
    (-23.4553, -46.5430): 12,
    (-23.5327, -46.7797): 13,
    (-23.6436, -46.6414): 14,
    (-23.7102, -46.4145): 15,
}

priorities = {
    (-23.6756, -46.5262): 8,
    (-23.6637, -46.5255): 10,
    (-23.6678, -46.4614): 8,
    (-23.7069, -46.5554): 9,
    (-23.7133, -46.5467): 10,
    (-23.6226, -46.5712): 9,
    (-23.4932, -46.8499): 7,
    (-23.5856, -46.6786): 10,
    (-23.6438, -46.6422): 8,
    (-23.5908, -46.7156): 9,
    (-23.5605, -46.5882): 7,
    (-23.5601, -46.5582): 8,
    (-23.4553, -46.5430): 7,
    (-23.5327, -46.7797): 7,
    (-23.6436, -46.6414): 9,
    (-23.7102, -46.4145): 8,
}

weights = {
    (-23.6756, -46.5262): 18,
    (-23.6637, -46.5255): 24,
    (-23.6678, -46.4614): 15,
    (-23.7069, -46.5554): 20,
    (-23.7133, -46.5467): 22,
    (-23.6226, -46.5712): 18,
    (-23.4932, -46.8499): 12,
    (-23.5856, -46.6786): 20,
    (-23.6438, -46.6422): 16,
    (-23.5908, -46.7156): 18,
    (-23.5605, -46.5882): 14,
    (-23.5601, -46.5582): 17,
    (-23.4553, -46.5430): 13,
    (-23.5327, -46.7797): 15,
    (-23.6436, -46.6414): 16,
    (-23.7102, -46.4145): 14,
}

time_windows = {
    (-23.6637, -46.5255): (0, 120),
    (-23.7133, -46.5467): (0, 130),
    (-23.5856, -46.6786): (20, 150),
    (-23.5908, -46.7156): (30, 180),
    (-23.6226, -46.5712): (40, 190),
    (-23.6436, -46.6414): (50, 210),
    (-23.7069, -46.5554): (60, 230),
    (-23.6756, -46.5262): (70, 240),
    (-23.5601, -46.5582): (80, 260),
    (-23.6678, -46.4614): (90, 280),
    (-23.7102, -46.4145): (100, 320),
}