import csv
import logging
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler, MinMaxScaler
import skfuzzy as fuzz

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

class NeuroFuzzyTrainer:
    def __init__(self, base_engine, max_clusters: int = 30):
        self.engine = base_engine
        self.max_clusters = max_clusters

    def generate_synthetic_data(self, num_scenarios: int = 2000) -> pd.DataFrame:
        logger.info(f"Gerando {num_scenarios} cenários sintéticos para amostragem densa...")
        
        dados_entrada = {
            'altitude': np.random.uniform(0, 10, num_scenarios),
            'taxa_descida': np.random.uniform(0.5, 4.5, num_scenarios),
            'velocidade': np.random.uniform(25, 38, num_scenarios),
            'vento_traves': np.random.uniform(-8, 8, num_scenarios)
        }
        df = pd.DataFrame(dados_entrada)
        
        resultados_leme = []
        resultados_profundor = []
        indices_validos = []

        for idx, row in df.iterrows():
            try:
                leme, prof = self.engine.compute(
                    row['altitude'], 
                    row['taxa_descida'], 
                    row['velocidade'], 
                    row['vento_traves']
                )
                resultados_leme.append(leme)
                resultados_profundor.append(prof)
                indices_validos.append(idx)
            except (ValueError, KeyError):
                continue

        df_final = df.loc[indices_validos].copy()
        df_final['comando_leme'] = resultados_leme
        df_final['comando_profundor'] = resultados_profundor
        return df_final

    def _find_optimal_k(self, X_scaled: np.ndarray) -> int:
        logger.info(f"Avaliando K ótimo (limite {self.max_clusters}) via cotovelo ortogonal...")
        wcss = []
        cluster_range = range(1, self.max_clusters + 1)
        
        for k in cluster_range:
            kmeans = KMeans(n_clusters=k, init='k-means++', random_state=42, n_init='auto')
            kmeans.fit(X_scaled)
            wcss.append(kmeans.inertia_)

        k_norm = MinMaxScaler().fit_transform(np.array(cluster_range).reshape(-1, 1))
        wcss_norm = MinMaxScaler().fit_transform(np.array(wcss).reshape(-1, 1))
        pontos = np.column_stack((k_norm, wcss_norm))
        
        p1 = pontos[0]
        p2 = pontos[-1]
        norm_linha = np.linalg.norm(p2 - p1)
        
        distancias = [
            np.abs((p2[0] - p1[0]) * (p1[1] - p[1]) - (p1[0] - p[0]) * (p2[1] - p1[1])) / norm_linha 
            for p in pontos
        ]
        
        k_opt = cluster_range[np.argmax(distancias)]
        
        try:
            from plotter import plot_metodo_cotovelo
            plot_metodo_cotovelo(list(cluster_range), wcss, k_opt, "fig_grafico_cotovelo.png")
        except ImportError:
            pass
            
        logger.info(f"Convergência concluída. K ótimo: {k_opt} regras.")
        return k_opt

    def _translate_to_fuzzy(self, variable_name: str, value: float) -> str:
        fuzzy_var = self.engine.variables[variable_name] 
        memberships = {
            term: fuzz.interp_membership(fuzzy_var.universe, fuzzy_var[term].mf, value)
            for term in fuzzy_var.terms
        }
        return max(memberships, key=memberships.get)

    def train_and_export(self, output_csv_path: str, target: str, base_csv_path: str):
        logger.info(f"Iniciando pipeline Neurofuzzy para: {target.upper()}")
        
        df = self.generate_synthetic_data(num_scenarios=2000)
        
        if target == 'comando_leme':
            features = ['altitude', 'vento_traves']
        else:
            features = ['altitude', 'taxa_descida', 'velocidade']
            
        X = df[features]
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)
        
        k_opt = self._find_optimal_k(X_scaled)
        
        kmeans = KMeans(n_clusters=k_opt, random_state=42, n_init=10)
        kmeans.fit(X_scaled)
        centers = scaler.inverse_transform(kmeans.cluster_centers_)
        
        extracted_rules = []
        
        logger.info("Hibridização: Integrando regras heurísticas base (Safety Net)...")
        with open(base_csv_path, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row and row.get('antecedents') and row['antecedents'].strip():
                    extracted_rules.append(row)

        logger.info("Adicionando regras Neurofuzzy otimizadas...")
        for i, center in enumerate(centers):
            if target == 'comando_leme':
                alt_term = self._translate_to_fuzzy('altitude', center[0])
                vento_term = self._translate_to_fuzzy('vento_traves', center[1])
                antecedents_str = f"altitude=={alt_term}|vento_traves=={vento_term}"
            else:
                alt_term = self._translate_to_fuzzy('altitude', center[0])
                td_term = self._translate_to_fuzzy('taxa_descida', center[1])
                vel_term = self._translate_to_fuzzy('velocidade', center[2])
                antecedents_str = f"altitude=={alt_term}|taxa_descida=={td_term}|velocidade=={vel_term}"
            
            mean_output = df[kmeans.labels_ == i][target].mean()
            out_term = self._translate_to_fuzzy(target, mean_output)
            
            rule_dict = {
                'antecedents': antecedents_str,
                'operator': 'AND',
                'consequent': target,
                'result': out_term
            }
            if rule_dict not in extracted_rules:
                extracted_rules.append(rule_dict)

        csv_headers = ['antecedents', 'operator', 'consequent', 'result']
        with open(output_csv_path, mode='w', newline='', encoding='utf-8') as file:
            writer = csv.DictWriter(file, fieldnames=csv_headers)
            writer.writeheader()
            writer.writerows(extracted_rules)
            
        logger.info(f"Sucesso! {len(extracted_rules)} regras persistidas em: {output_csv_path}")

if __name__ == "__main__":
    import os
    import sys
    import json
    
    try:
        from fuzzy_engine import HarpiaFuzzyEngine
    except ImportError:
        logger.error("Falha na importação. Certifique-se de que fuzzy_engine.py está no mesmo diretório.")
        sys.exit(1)

    base_dir = os.path.dirname(os.path.abspath(__file__))
    profiles_dir = os.path.join(base_dir, 'config', 'profiles')
    rules_dir = os.path.join(base_dir, 'config', 'rules')
    
    profiles = [f for f in os.listdir(profiles_dir) if f.endswith('.json')]
    if not profiles:
        sys.exit(1)
        
    print("\n=== TREINAMENTO NEUROFUZZY - SELEÇÃO DE PERFIL ===")
    for idx, profile in enumerate(profiles):
        print(f"[{idx}] {profile.replace('.json', '')}")
        
    choice = int(input("\nSelecione o ID da aeronave para treinar: "))
    aircraft_name = profiles[choice].replace('.json', '')
    
    profile_path = os.path.join(profiles_dir, profiles[choice])
    
    base_rudder_csv = os.path.join(rules_dir, f'{aircraft_name}_rudder.csv')
    base_elevator_csv = os.path.join(rules_dir, f'{aircraft_name}_elevator.csv')
    
    output_rudder_csv = os.path.join(rules_dir, f'{aircraft_name}_rudder_trained.csv')
    output_elevator_csv = os.path.join(rules_dir, f'{aircraft_name}_elevator_trained.csv')

    with open(profile_path, 'r', encoding='utf-8') as f:
        profile_data = json.load(f)
        
    base_engine = HarpiaFuzzyEngine(
        profile_data=profile_data,
        rudder_csv=base_rudder_csv,
        elevator_csv=base_elevator_csv
    )

    trainer = NeuroFuzzyTrainer(base_engine=base_engine, max_clusters=15)

    logger.info("=== INICIANDO PIPELINE HÍBRIDO ===")
    
    logger.info(f"--- Otimizando SIF A: Leme ---")
    trainer.train_and_export(output_csv_path=output_rudder_csv, target='comando_leme', base_csv_path=base_rudder_csv)
    
    logger.info(f"--- Otimizando SIF B: Profundor ---")
    trainer.train_and_export(output_csv_path=output_elevator_csv, target='comando_profundor', base_csv_path=base_elevator_csv)
    
    logger.info("=== TREINAMENTO CONCLUÍDO COM SUCESSO ===")
