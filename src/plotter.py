import matplotlib.pyplot as plt
import numpy as np
from mpl_toolkits.mplot3d import Axes3D

"""
Este é um arquivo utilitário para plotar alguns gráficos relevantes ao artigo.
Não é necessário para o funcionamento da ferramenta.
"""

def plot_elbow(k_values: list, wcss_values: list, k_opt: int, output_filename="elbow_plot.png"):
    plt.figure(figsize=(8, 5))
    plt.plot(k_values, wcss_values, marker='o', linestyle='-', color='#1f77b4', label='FWCSS')
    
    idx_opt = k_values.index(k_opt)
    plt.plot(k_opt, wcss_values[idx_opt], marker='X', color='red', markersize=10, label=f'K Ótimo ({k_opt})')
    
    plt.title('Análise do Cotovelo via Distância Ortogonal', fontsize=12)
    plt.xlabel('Número de Clusters (Regras)', fontsize=10)
    plt.ylabel('Soma Quadrática Intra-Cluster (FWCSS)', fontsize=10)
    plt.xticks(np.arange(min(k_values), max(k_values)+1, 2))
    plt.grid(True, linestyle='--', alpha=0.7)
    plt.legend()
    
    plt.tight_layout()
    plt.savefig(output_filename, dpi=300)
    plt.close()


def plot_superficie_controle_leme(engine, output_filename="superficie_leme_plot.png"):
    vento_range = np.linspace(-8, 8, 20)
    altitude_range = np.linspace(0, 10, 20)
    X, Y = np.meshgrid(vento_range, altitude_range)
    Z = np.zeros_like(X)
    
    taxa_descida_const = 2.5
    velocidade_const = 32.0

    for i in range(X.shape[0]):
        for j in range(X.shape[1]):
            try:
                leme, _ = engine.compute(
                    altitude=Y[i, j], 
                    taxa_descida=taxa_descida_const, 
                    velocidade=velocidade_const, 
                    vento_traves=X[i, j]
                )
                Z[i, j] = leme
            except (ValueError, KeyError):
                Z[i, j] = np.nan
                
    fig = plt.figure(figsize=(10, 7))
    ax = fig.add_subplot(111, projection='3d')
    
    surf = ax.plot_surface(X, Y, Z, cmap='coolwarm', edgecolor='none', alpha=0.9)
    
    ax.set_title('Superfície de Controle Não-Linear: Comando do Leme', pad=20)
    ax.set_xlabel('Vento de Través (m/s)')
    ax.set_ylabel('Altitude (m)')
    ax.set_zlabel('Deflexão do Leme (%)')
    fig.colorbar(surf, shrink=0.5, aspect=10, label='Sinal de Controle')
    
    ax.view_init(elev=25, azim=300)
    plt.savefig(output_filename, dpi=300)
    plt.close()


def plot_simulacao_monte_carlo(engine, output_filename="monte_carlo_flare.png"):
    time_steps = 100
    t = np.linspace(0, 10, time_steps) # 10 segundos de flare
    
    # Dinâmica de voo simulada
    altitude = np.linspace(10, 0, time_steps)  # Desce de 10m até o toque
    velocidade = np.linspace(38, 25, time_steps) # Desacelera para a velocidade de estol
    taxa_descida = np.linspace(3, 1, time_steps) # Flare
    
    vento_base = 3.0 # Vento lateral constante de 3 m/s
    ruido_gaussiano = np.random.normal(0, 1.5, time_steps)
    vento_traves = vento_base + ruido_gaussiano
    
    resposta_leme = []
    
    for i in range(time_steps):
        try:
            leme, _ = engine.compute(
                altitude=altitude[i], 
                taxa_descida=taxa_descida[i], 
                velocidade=velocidade[i], 
                vento_traves=vento_traves[i]
            )
            resposta_leme.append(leme)
        except (ValueError, KeyError):
            resposta_leme.append(resposta_leme[-1] if resposta_leme else 0)

    # Série Temporal
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8), sharex=True)
    
    # Gráfico de Entrada
    ax1.plot(t, vento_traves, color='red', alpha=0.7, label='Vento com Ruído Estocástico')
    ax1.axhline(vento_base, color='black', linestyle='--', label='Vento Médio (3 m/s)')
    ax1.set_ylabel('Vento de Través (m/s)')
    ax1.set_title('Perturbação Atmosférica Durante o Landing Flare', fontsize=11)
    ax1.grid(True, linestyle=':', alpha=0.6)
    ax1.legend()
    
    # Gráfico de Saída
    ax2.plot(t, resposta_leme, color='blue', linewidth=2, label='Ação do Leme (SIF A)')
    ax2.set_xlabel('Tempo (s)')
    ax2.set_ylabel('Deflexão do Leme (%)')
    ax2.set_title('Resposta Adaptativa do Controlador Neurofuzzy', fontsize=11)
    ax2.grid(True, linestyle=':', alpha=0.6)
    ax2.legend()
    
    plt.tight_layout()
    plt.savefig(output_filename, dpi=300)
    plt.close()

if __name__ == "__main__":
    import os
    import sys
    import json
    from fuzzy_engine import HarpiaFuzzyEngine

    print("=== GERADOR DE GRÁFICOS ===")

    base_dir = os.path.dirname(os.path.abspath(__file__))
    profile_path = os.path.join(base_dir, 'config', 'profiles', 'cessna_172.json')
    
    rudder_csv = os.path.join(base_dir, 'config', 'rules', 'cessna_172_rudder_trained.csv')
    elevator_csv = os.path.join(base_dir, 'config', 'rules', 'cessna_172_elevator_trained.csv')

    try:
        with open(profile_path, 'r', encoding='utf-8') as f:
            profile_data = json.load(f)
            
        engine = HarpiaFuzzyEngine(
            profile_data=profile_data,
            rudder_csv=rudder_csv,
            elevator_csv=elevator_csv
        )
    except Exception as e:
        print(f"Erro ao carregar o motor. Você já rodou o rule_trainer.py? Detalhes: {e}")
        sys.exit(1)

    print("1. Renderizando Superfície de Controle 3D...")
    plot_superficie_controle_leme(engine, output_filename=os.path.join(base_dir, 'fig_superficie_leme.png'))

    print("2. Executando Simulação Estocástica de Monte Carlo...")
    plot_simulacao_monte_carlo(engine, output_filename=os.path.join(base_dir, 'fig_monte_carlo_flare.png'))

    print("Concluído! Gráficos salvos com resolução de 300dpi na pasta src/.")
