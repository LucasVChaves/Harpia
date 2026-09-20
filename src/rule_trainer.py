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

    def generate_synthetic_data(self, num_scenarios: int = 100) -> pd.DataFrame:
        logger.info(f"Gerando {num_scenarios} cenários sintéticos de aproximação...")
        
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
        
        logger.info(f"Simulação base concluída. {len(df_final)} cenários viáveis retidos para aprendizado.")
        return df_final

    def _find_optimal_k(self, X_scaled: np.ndarray) -> int:
        logger.info(f"Avaliando o K ótimo (limite de {self.max_clusters} clusters) via método do cotovelo ortogonal...")
        
        wcss = []
        cluster_range = range(1, self.max_clusters + 1)
        
        for k in cluster_range:
            kmeans = KMeans(n_clusters=k, init='k-means++', random_state=42, n_init='auto')
            kmeans.fit(X_scaled)
            wcss.append(kmeans.inertia_)

        k_norm = MinMaxScaler().fit_transform(np.array(cluster_range).reshape(-1, 1))
        wcss_norm = MinMaxScaler().fit_transform(np.array(wcss).reshape(-1, 1))
        pontos = np.column_stack((k_norm, wcss_norm))
        
        linha = np.array([pontos[0], pontos[-1]])
        vetor_linha = linha[1] - linha[0]
        norm_linha = np.linalg.norm(vetor_linha)
        
        distancias = [np.linalg.norm(np.cross(vetor_linha, linha[0] - p)) / norm_linha for p in pontos]
        
        k_opt = cluster_range[np.argmax(distancias)]
        logger.info(f"Matemática de convergência concluída. K ótimo estabilizado em: {k_opt} regras.")
        return k_opt

    def _translate_to_fuzzy(self, variable_name: str, value: float) -> str:
        fuzzy_var = self.engine.variables[variable_name] 
        memberships = {
            term: fuzz.interp_membership(fuzzy_var.universe, fuzzy_var[term].mf, value)
            for term in fuzzy_var.terms
        }
        return max(memberships, key=memberships.get)

    def train_and_export(self, output_csv_path: str, target: str = 'comando_leme'):
        logger.info(f"Iniciando pipeline de treinamento Neurofuzzy para o controlador: {target.upper()}")
        
        df = self.generate_synthetic_data(num_scenarios=200)
        
        features = ['altitude', 'taxa_descida', 'velocidade', 'vento_traves']
        X = df[features]
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)
        
        k_opt = self._find_optimal_k(X_scaled)
        
        logger.info("Extraindo matriz de centroides K-Means...")
        kmeans = KMeans(n_clusters=k_opt, random_state=42, n_init=10)
        kmeans.fit(X_scaled)
        centers = scaler.inverse_transform(kmeans.cluster_centers_)
        
        csv_headers = ['antecedents', 'operator', 'consequent', 'result']
        extracted_rules = []

        logger.info("Traduzindo tensores numéricos para variáveis linguísticas fuzzy...")
        for i, center in enumerate(centers):
            alt_term = self._translate_to_fuzzy('altitude', center[0])
            td_term = self._translate_to_fuzzy('taxa_descida', center[1])
            vel_term = self._translate_to_fuzzy('velocidade', center[2])
            vento_term = self._translate_to_fuzzy('vento_traves', center[3])
            
            mean_output = df[kmeans.labels_ == i][target].mean()
            out_term = self._translate_to_fuzzy(target, mean_output)
            
            antecedents_str = f"altitude=={alt_term}|taxa_descida=={td_term}|velocidade=={vel_term}|vento_traves=={vento_term}"
            
            extracted_rules.append({
                'antecedents': antecedents_str,
                'operator': 'AND',
                'consequent': target,
                'result': out_term
            })

        with open(output_csv_path, mode='w', newline='', encoding='utf-8') as file:
            writer = csv.DictWriter(file, fieldnames=csv_headers)
            writer.writeheader()
            writer.writerows(extracted_rules)
            
        logger.info(f"Sucesso! {len(extracted_rules)} regras persistidas fisicamente em: {output_csv_path}")

if __name__ == "__main__":
    import os
    import sys
    import json
    
    try:
        from fuzzy_engine import HarpiaFuzzyEngine
    except ImportError:
        logger.error("Falha na importação. Certifique-se de que fuzzy_engine.py está no mesmo diretório.")
        sys.exit(1)

    def load_json(filepath: str) -> dict:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)

    base_dir = os.path.dirname(os.path.abspath(__file__))
    profiles_dir = os.path.join(base_dir, 'config', 'profiles')
    rules_dir = os.path.join(base_dir, 'config', 'rules')
    
    profiles = [f for f in os.listdir(profiles_dir) if f.endswith('.json')]
    if not profiles:
        logger.error("Nenhum perfil de aeronave encontrado no diretório de configurações.")
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

    logger.info(f"Compilando motor de geração sintética para: {aircraft_name.upper()}")
    try:
        profile_data = load_json(profile_path)
        base_engine = HarpiaFuzzyEngine(
            profile_data=profile_data,
            rudder_csv=base_rudder_csv,
            elevator_csv=base_elevator_csv
        )
    except Exception as e:
        logger.error(f"Erro fatal na compilação do motor. Falta de regras base? Detalhes: {e}")
        sys.exit(1)

    trainer = NeuroFuzzyTrainer(base_engine=base_engine, max_clusters=15)

    logger.info("=== INICIANDO PIPELINE DE APRENDIZADO DE MÁQUINA ===")
    try:
        logger.info(f"--- Otimizando SIF A: Leme ---")
        trainer.train_and_export(output_csv_path=output_rudder_csv, target='comando_leme')
        
        logger.info(f"--- Otimizando SIF B: Profundor ---")
        trainer.train_and_export(output_csv_path=output_elevator_csv, target='comando_profundor')
        
        logger.info("=== TREINAMENTO CONCLUÍDO COM SUCESSO ===")
    except Exception as e:
        logger.error(f"Processo de treinamento abortado: {e}", exc_info=True)