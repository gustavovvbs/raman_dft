#!/usr/bin/env python3

import os
import subprocess
import re
import pandas as pd
import matplotlib.pyplot as plt

def gerar_input_orca(molecule_xyz,
                     method="BP86",
                     basis="def2-SVP",
                     jobname="raman_job"):
    """
    Gera um arquivo de entrada do ORCA para um cálculo Raman (numérico).
    - molecule_xyz: nome do arquivo .xyz com a geometria
    - method, basis: método e base para o ORCA
    - jobname: prefixo do nome do arquivo .inp e .out
    """
    # Lê as coordenadas do arquivo .xyz
    with open(molecule_xyz, 'r') as f:
        xyz_lines = f.readlines()

    # Extrai o número de átomos (1a linha) e ignora a 2a (comentário)
    natoms = int(xyz_lines[0].strip())
    coords = xyz_lines[2:2 + natoms]  # apenas as linhas de coordenadas

    # Conteúdo do input de exemplo
    input_content = f"""! {method} {basis} OPT NUMFREQ

%elprop
   POLAR 1
end

* xyz 0 1
"""
    # Adiciona as coordenadas
    for line in coords:
        input_content += line
    input_content += "*\n"

    # Escreve em disco
    inp_file = f"{jobname}.inp"
    with open(inp_file, 'w') as f:
        f.write(input_content)

    return inp_file


def rodar_orca(inp_file):
    """
    Executa o ORCA chamando:
       orca inp_file > out_file
    Retorna o nome do arquivo de saída gerado.
    """
    out_file = inp_file.replace(".inp", ".out")
    with open(out_file, 'w') as f_out:
        subprocess.run(["orca", inp_file], stdout=f_out, stderr=subprocess.STDOUT)
    return out_file


def parse_raman_output(out_file):
    """
    Faz o parse da seção "RAMAN SPECTRUM" do arquivo .out do ORCA.
    Retorna duas listas:
      - freq_cm: frequências (cm^-1)
      - activity: atividade Raman
    Utiliza expressão regular para ignorar linhas de cabeçalho e traços.
    """
    freq_cm = []
    activity = []

    # Regex para capturar linhas do tipo:
    #   9:      331.46      0.294356      0.328512
    pattern = re.compile(r'^\s*(\d+):\s+([\d\.]+)\s+([\d\.]+)\s+([\d\.]+)')

    raman_section_found = False

    with open(out_file, 'r') as f:
        for line in f:
            # Verifica se chegou na seção RAMAN SPECTRUM
            if "RAMAN SPECTRUM" in line:
                raman_section_found = True
                continue

            if raman_section_found:
                # Linhas de traços ou vazias podem sinalizar fim/continuação
                if (line.strip().startswith("---") or
                    len(line.strip()) == 0 or
                    "Mode" in line):
                    # Apenas ignorar
                    continue

                match = pattern.match(line)
                if match:
                    # Extraindo as colunas
                    mode_index_str, freq_str, act_str, depol_str = match.groups()
                    freq_val = float(freq_str)
                    act_val = float(act_str)
                    freq_cm.append(freq_val)
                    activity.append(act_val)
                else:
                    # Se não casou, pode significar que a seção acabou de fato
                    # (ou que é outra seção no arquivo). Então podemos dar break.
                    # Ou, se preferir, continue para ignorar mais linhas.
                    break

    return freq_cm, activity


def main():
    """
    Exemplo de uso integrado:
     1) Gera input do ORCA para Raman
     2) Roda ORCA
     3) Faz parse do resultado
     4) Plota e salva PNG do espectro
    """

    # Parâmetros principais
    molecule_xyz = "butano.xyz"   # Substituir pelo .xyz desejado
    method = "BP86"
    basis = "def2-SVP"
    jobname = "raman_butano"

    # 1) Gera input
    inp_file = gerar_input_orca(molecule_xyz, method, basis, jobname)

    print(f"Input '{inp_file}' criado. Rodando ORCA...")

    # 2) Roda ORCA
    out_file = rodar_orca(inp_file)
    print(f"Cálculo finalizado. Saída em '{out_file}'.")

    # 3) Faz parse da seção "RAMAN SPECTRUM"
    freq_cm, activity = parse_raman_output(out_file)
    if not freq_cm:
        print("Não foi possível encontrar dados de Raman no arquivo de saída.")
        return

    # 4) Plota e salva figura
    # Organiza num DataFrame para facilidade
    import pandas as pd
    df = pd.DataFrame({
        "Frequency (cm^-1)": freq_cm,
        "Activity": activity
    })

    plt.figure(figsize=(10, 5))
    plt.plot(df["Frequency (cm^-1)"], df["Activity"],
             marker='o', linestyle='-', label="Raman Activity")
    plt.title("Raman Spectrum")
    plt.xlabel("Raman Shift (cm$^{-1}$)")
    plt.ylabel("Activity")
    plt.grid(True)
    plt.legend()
    plt.tight_layout()

    # Salva em PNG
    fig_name = "raman_spectrum.png"
    plt.savefig(fig_name, dpi=300)
    print(f"Espectro salvo como '{fig_name}'.")


if __name__ == "__main__":
    main()
