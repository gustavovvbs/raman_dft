import os
import subprocess
import re
import numpy as np
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
    # le as coordenadas do arquivo .xyz
    with open(molecule_xyz, 'r') as f:
        xyz_lines = f.readlines()

    # extrai o número de atomos (1 linha) e ignora a 2a (comentario)
    natoms = int(xyz_lines[0].strip())
    coords = xyz_lines[2:2 + natoms]  # apenas as linhas de coordenadas

    # conteudo do input 
    input_content = f"""! {method} {basis} OPT NUMFREQ

%elprop
   POLAR 1
end

* xyz 0 1
"""
    # adiciona as coordenadas
    for line in coords:
        input_content += line
    input_content += "*\n"

    # escreve em disco
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
    Retorna duas listas (numpy arrays):
      - freq_cm: frequências (cm^-1)
      - activity: atividade Raman
    Ignora linhas de cabeçalho e traços via regex.
    """
    freq_cm = []
    activity = []

    # regex(morra) para capturar linhas do tipo:
    #   9:      331.46      0.294356      0.328512
    pattern = re.compile(r'^\s*(\d+):\s+([\d\.]+)\s+([\d\.]+)\s+([\d\.]+)')

    raman_section_found = False

    with open(out_file, 'r') as f:
        for line in f:
            # verifica se chegou na secao certa
            if "RAMAN SPECTRUM" in line:
                raman_section_found = True
                continue

            if raman_section_found:
                # ignora traco, linha vazia ou cabecalho
                if (line.strip().startswith("---") or
                    len(line.strip()) == 0 or
                    "Mode" in line):
                    continue

                match = pattern.match(line)
                if match:
                    mode_index_str, freq_str, act_str, depol_str = match.groups()
                    freq_val = float(freq_str)
                    act_val = float(act_str)
                    freq_cm.append(freq_val)
                    activity.append(act_val)
                else:
                    # Se nao casou, secao acabou
                    break

    return np.array(freq_cm), np.array(activity)


def converter_cm_inv_para_nm_deslocado(freq_cm, laser_wavelength_nm=532.0, modo="Stokes"):
    """
    Converte a frequência vibracional (cm^-1) em comprimento de onda espalhado (nm),
    assumindo espalhamento Raman Stokes ou Anti-Stokes.
    
    Para Stokes:  ν_espalhada = ν_laser - freq_cm
    onde:
      ν_laser (cm^-1) = 1e7 / laser_wavelength_nm
      λ_espalhada (nm) = 1e7 / ν_espalhada
    """
    laser_cm_inv = 1e7 / laser_wavelength_nm  # converte laser (nm) em cm^-1

    if modo.lower() == "stokes":
        freq_espalhada = laser_cm_inv - freq_cm
    else:
        # Anti-Stokes
        freq_espalhada = laser_cm_inv + freq_cm

    # Evita divisao por zero (se freq_espalhada <= 0, eh nao-fisica)
    freq_espalhada = np.where(freq_espalhada <= 1e-6, 1e-6, freq_espalhada)
    lambda_espalhada_nm = 1e7 / freq_espalhada
    return lambda_espalhada_nm


def fator_temperatura(freq_cm, T=298.15):
    """
    Cálculo simplificado do fator de população vibracional.
    Para Stokes, intensidade ~ (n + 1) = 1 + 1/[exp(hcν / kT) - 1]
    
    h*c ~ 1.98645e-23 J.cm
    k_B = 1.380649e-23 J/K
    """
    hc = 1.98645e-23  # J.cm
    k_B = 1.380649e-23  # J/K

    freq_joules = hc * freq_cm  # E = h*c*freq
    # n = 1 / (exp(E/kT) - 1)
    n = 1.0 / (np.exp(freq_joules / (k_B * T)) - 1.0)
    return (n + 1)


def main(molecule_xyz="butano.xyz",
         method="BP86",
         basis="def2-SVP",
         jobname="raman_butano",
         laser_wavelength_nm=532.0,
         temperature=298.15,
         plot_raman_shift=False):
    """
    Workflow completo em um único script:
      1) Gera input ORCA (OPT + NUMFREQ)
      2) Executa ORCA
      3) Faz parse do "RAMAN SPECTRUM"
      4) Aplica fator de temperatura
      5) Se plot_raman_shift=False, converte para lambda (nm); senão, usa freq (cm^-1)
      6) Plota e salva o espectro em PNG
    """

    # 1) Gera o input
    inp_file = gerar_input_orca(molecule_xyz, method, basis, jobname)
    print(f"Input '{inp_file}' criado. Rodando ORCA...")

    # 2) Roda o orca
    out_file = rodar_orca(inp_file)
    print(f"Cálculo finalizado. Saída em '{out_file}'.")

    # 3) Parse da secao "RAMAN SPECTRUM"
    freq_cm, activity = parse_raman_output(out_file)
    if len(freq_cm) == 0:
        print("Não foi possível encontrar dados de Raman no arquivo de saída.")
        return

    # 4) Fator de temperatura: Intensidade ~ atividade * (n + 1)
    temp_factor = fator_temperatura(freq_cm, T=temperature)
    intensidade = activity * temp_factor

    # 5) Decide se vamos plotar em Raman Shift (cm^-1) ou em Comprimento de Onda (nm)
    if plot_raman_shift:
        # Se quisermos o deslocamento Raman em cm^-1
        # X = freq_cm, Y = intensidade
        df = pd.DataFrame({
            "Raman Shift (cm^-1)": freq_cm,
            "Intensity": intensidade
        })
        x_label = "Raman Shift (cm$^{-1}$)"
        x_data = df["Raman Shift (cm^-1)"]
        invert_x = False  
    else:
        # Converte freq_cm pra comprimento de onda espalhado (Stokes)
        lambda_espalhada_nm = converter_cm_inv_para_nm_deslocado(
            freq_cm, laser_wavelength_nm=laser_wavelength_nm, modo="Stokes"
        )
        df = pd.DataFrame({
            "Wavelength (nm)": lambda_espalhada_nm,
            "Intensity": intensidade
        })
        x_label = "Comprimento de onda espalhado (nm)"
        x_data = df["Wavelength (nm)"]
        invert_x = False  # inverter o eixo nm (Stokes)

    # 6) Plota e salva
    plt.figure(figsize=(8, 5))
    plt.title(f"Raman Spectrum: {jobname}")

    if plot_raman_shift:
        plt.plot(x_data, df["Intensity"], 'bo-', label='Stokes')
    else:
        plt.plot(x_data, df["Intensity"], 'ro-', label='Stokes')

    plt.xlabel(x_label)
    plt.ylabel("Intensidade (u.a.)")
    plt.legend()
    plt.grid(True)

    if invert_x:
        plt.gca().invert_xaxis()

    plt.tight_layout()
    fig_name = f"{jobname}_raman_spectrum.png"
    plt.savefig(fig_name, dpi=300)
    print(f"Espectro salvo como '{fig_name}'.")


if __name__ == "__main__":
    # Ajuste aqui conforme desejado (método, base, laser, etc.)
    main(
        molecule_xyz="geometries/butano.xyz",
        method="BP86",
        basis="def2-SVP",
        jobname="raman_butano",
        laser_wavelength_nm=532.0,
        temperature=300.0,
        plot_raman_shift=False  # Mude para True para plotar em cm^-1
    )
