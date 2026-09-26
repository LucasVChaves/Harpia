import csv
import logging
import operator
from functools import reduce
import numpy as np
import skfuzzy as fuzz
from skfuzzy import control as ctrl

logger = logging.getLogger(__name__)

def build_fuzzy_variables(profile_data: dict) -> dict:
    variables = {}
    logger.info("Construindo variáveis fuzzy a partir do perfil da aeronave...")
    
    for var_name, var_data in profile_data.items():
        universe = np.arange(var_data['universe'][0], var_data['universe'][1], var_data['step'])
        
        if var_data['type'] == 'antecedent':
            fuzzy_var = ctrl.Antecedent(universe, var_name)
        else:
            fuzzy_var = ctrl.Consequent(universe, var_name)
            
        for term_name, mf_data in var_data['terms'].items():
            if mf_data['shape'] == 'trimf':
                fuzzy_var[term_name] = fuzz.trimf(fuzzy_var.universe, mf_data['params'])
            elif mf_data['shape'] == 'trapmf':
                fuzzy_var[term_name] = fuzz.trapmf(fuzzy_var.universe, mf_data['params'])
                
        variables[var_name] = fuzzy_var
        
    return variables

def parse_rules_from_csv(csv_path: str, variables: dict) -> list:
    parsed_rules = []
    logger.info(f"Fazendo parsing das regras estáticas em: {csv_path}")
    
    with open(csv_path, mode='r', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        
        for row_idx, row in enumerate(reader, start=2):
            if not row or not row.get('antecedents') or not row['antecedents'].strip():
                continue
                
            antecedents_raw = row['antecedents'].split('|')
            logical_op = operator.and_ if row['operator'].strip().upper() == 'AND' else operator.or_
            
            conditions = []
            for ant in antecedents_raw:
                if '==' not in ant:
                    raise ValueError(f"Erro na linha {row_idx} do arquivo {csv_path}: o trecho '{ant}' não contém '=='.")
                
                var_name, term = ant.split('==')
                conditions.append(variables[var_name.strip()][term.strip()])
                
            antecedent_expr = reduce(logical_op, conditions)
            
            consequent_var = row['consequent'].strip()
            consequent_term = row['result'].strip()
            consequent_expr = variables[consequent_var][consequent_term]
            
            rule = ctrl.Rule(antecedent_expr, consequent_expr)
            parsed_rules.append(rule)
            
    return parsed_rules

class HarpiaFuzzyEngine:
    def __init__(self, profile_data: dict, rudder_csv: str, elevator_csv: str):
        self.variables = build_fuzzy_variables(profile_data)
        
        rudder_rules = parse_rules_from_csv(rudder_csv, self.variables)
        self.rudder_ctrl = ctrl.ControlSystem(rudder_rules)
        self.sim_rudder = ctrl.ControlSystemSimulation(self.rudder_ctrl)
        
        elevator_rules = parse_rules_from_csv(elevator_csv, self.variables)
        self.elevator_ctrl = ctrl.ControlSystem(elevator_rules)
        self.sim_elevator = ctrl.ControlSystemSimulation(self.elevator_ctrl)
        logger.info("Motor de inferência Harpia instanciado e pronto para execução.")

    def compute(self, altitude: float, taxa_descida: float, velocidade: float, vento_traves: float) -> tuple[float, float]:
        telemetry = {
            'altitude': altitude,
            'taxa_descida': taxa_descida,
            'velocidade': velocidade,
            'vento_traves': vento_traves
        }
        
        for key, value in telemetry.items():
            try:
                self.sim_rudder.input[key] = value
            except ValueError:
                pass
                
        self.sim_rudder.compute()
        rudder_output = self.sim_rudder.output['comando_leme']
        
        telemetry['leme_como_entrada'] = rudder_output
        
        for key, value in telemetry.items():
            try:
                self.sim_elevator.input[key] = value
            except ValueError:
                pass
                
        self.sim_elevator.compute()
        elevator_output = self.sim_elevator.output['comando_profundor']
        
        return rudder_output, elevator_output
