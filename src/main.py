import json
import logging
import os
import sys
import random
from fuzzy_engine import HarpiaFuzzyEngine

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

def load_json(filepath: str) -> dict:
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        logger.error(f"Erro: O arquivo de perfil não foi encontrado em {filepath}")
        sys.exit(1)

def select_profile(profiles_dir: str) -> str:
    if not os.path.exists(profiles_dir):
        logger.error(f"Diretório de perfis não encontrado: {profiles_dir}")
        sys.exit(1)
        
    profiles = [f for f in os.listdir(profiles_dir) if f.endswith('.json')]
    
    if not profiles:
        logger.error("Nenhum perfil de aeronave (.json) encontrado.")
        sys.exit(1)
        
    print("\n=== PERFIS DE AERONAVE DISPONÍVEIS ===")
    for idx, profile in enumerate(profiles):
        print(f"[{idx}] {profile.replace('.json', '')}")
        
    while True:
        try:
            choice = int(input("\nSelecione o ID do perfil desejado: "))
            if 0 <= choice < len(profiles):
                return profiles[choice]
            print("ID inválido. Tente novamente.")
        except ValueError:
            print("Por favor, insira um número válido.")

def get_flight_data() -> dict:
    print("\n=== DADOS DE TELEMETRIA (FLARE) ===")
    print("[1] Inserir dados manualmente")
    print("[2] Gerar cenário aleatório realista")
    
    escolha = input("Opção: ").strip()
    
    if escolha == '1':
        try:
            alt = float(input(" Altitude (0 a 10m): "))
            td = float(input(" Taxa de descida (0.5 a 5m/s): "))
            vel = float(input(" Velocidade (20 a 40m/s): "))
            vento = float(input(" Vento de través (-8 a 8m/s): "))
            return {'altitude': alt, 'taxa_descida': td, 'velocidade': vel, 'vento_traves': vento}
        except ValueError:
            logger.warning("Entrada inválida detectada. Alternando para geração aleatória.")
            
    data = {
        'altitude': round(random.uniform(1.0, 8.0), 1),
        'taxa_descida': round(random.uniform(1.0, 3.5), 1),
        'velocidade': round(random.uniform(25.0, 36.0), 1),
        'vento_traves': round(random.uniform(-7.0, 7.0), 1)
    }
    logger.info(f"Cenário sintético gerado: {data}")
    return data

def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    profiles_dir = os.path.join(base_dir, 'config', 'profiles')
    rules_dir = os.path.join(base_dir, 'config', 'rules')
    
    selected_filename = select_profile(profiles_dir)
    aircraft_name = selected_filename.replace('.json', '')
    
    profile_path = os.path.join(profiles_dir, selected_filename)
    rudder_rules_path = os.path.join(rules_dir, f'{aircraft_name}_rudder.csv')
    elevator_rules_path = os.path.join(rules_dir, f'{aircraft_name}_elevator.csv')
    
    logger.info(f"Iniciando Harpia Engine com o perfil: {aircraft_name.upper()}")
    profile_data = load_json(profile_path)
    
    try:
        engine = HarpiaFuzzyEngine(
            profile_data=profile_data,
            rudder_csv=rudder_rules_path,
            elevator_csv=elevator_rules_path
        )
    except Exception as e:
        logger.error(f"Falha na compilação do motor. Verifique a sintaxe dos CSVs: {e}")
        sys.exit(1)
    
    flight_data = get_flight_data()
    
    try:
        rudder, elevator = engine.compute(**flight_data)
        
        print("\n" + "=" * 50)
        print(" SIMULAÇÃO DE POUSO - RESULTADO DA INFERÊNCIA")
        print("=" * 50)
        print(f" Leme:      {rudder:>6.2f}% ({'Esquerda' if rudder < 0 else 'Direita'})")
        print(f" Profundor: {elevator:>6.2f}% ({'Empurrar' if elevator < 0 else 'Puxar'})")
        print("=" * 50 + "\n")
        
    except ValueError:
        logger.error("Falha na inferência. O cenário recaiu em um hiato não mapeado pelas regras base.")

if __name__ == "__main__":
    main()