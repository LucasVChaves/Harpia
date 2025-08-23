import numpy as np 
import pandas as pd 
import skfuzzy as fuzz
from skfuzzy import control as ctrl
from typing import Union

class FuzzyController:
    def __init__(self, profile: dict):
        self.profile = profile
        self._variables = {}
        self._create_variables()
        self._populate_pertinence_functions()
        self.rudder_sim = self._create_rudder_sim()
        self.elevator_sim = self._create_elevator_sim()
        print("Fuzzy Engine Inicialized")

    def _create_variables(self):
        """Create antecedents / consquents objects based on the profile ranges"""
        for name, params in self.profile['variables'].items():
            universo = np.arange(params['start'], params['stop'], params['step'])
            if 'comando' in name:
                self._variables[name] = ctrl.Consequent(universo, name)
            else:
                self._variables[name] = ctrl.Antecedent(universo, name)

    def _populate_pertinence_functions(self):
        """Defines the fuzzy matrices for the each variable"""
        # Altitude (m)
        alt = self._variables['altitude']
        alt['low'] = fuzz.trapmf(alt.universe, [0, 0, 1.5, 4])
        alt['ideal'] = fuzz.trapmf(alt.universe, [2.5, 4.5, 6.5, 8.5])
        alt['high'] = fuzz.trapmf(alt.universe, [7, 9, 10, 10])

        # Descent rate (m/s)
        ds = self._variables['descent_rate']
        ds['low'] = fuzz.trapmf(ds.universe, [0, 0, 1, 2.5])
        ds['ideal'] = fuzz.trimf(ds.universe, [1.5, 2.7, 4])
        ds['high'] = fuzz.trapmf(ds.universe, [3.5, 4.5, 5, 5])

        # Airspeed (m/s)
        sp = self._variables['airspeed']
        sp['low'] = fuzz.trapmf(sp.universe, [20, 20, 24, 29])
        sp['ideal'] = fuzz.trapmf(sp.universe, [27, 29, 33.5, 35.5])
        sp['high'] = fuzz.trapmf(sp.universe, [33.5, 36, 40, 40])

        # Crosswind (m/s)
        cw = self._variables['crosswind']
        cw['strong_left'] = fuzz.trapmf(cw.universe, [-8, -8, -7, -4])
        cw['moderate_left'] = fuzz.trimf(cw.universe, [-6, -3.5, -1])
        cw['null'] = fuzz.trimf(cw.universe, [-2, 0, 2])
        cw['moderate_right'] = fuzz.trimf(cw.universe, [1, 3.5, 6])
        cw['strong_right'] = fuzz.trapmf(cw.universe, [4, 7, 8, 8])
        
        # Rudder Output (% of travel)
        ro = self._variables['rudder_output']
        ro['total_left'] = fuzz.trapmf(ro.universe, [-100, -100, -80, -50])
        ro['partial_left'] = fuzz.trimf(ro.universe, [-70, -40, -10])
        ro['neutral'] = fuzz.trimf(ro.universe, [-20, 0, 20])
        ro['partial_right'] = fuzz.trimf(ro.universe, [10, 40, 70])
        ro['total_right'] = fuzz.trapmf(ro.universe, [50, 80, 100, 100])
        
        # Elevator Output (% of travel)
        eo = self._variables['elevator_output']
        eo['push'] = fuzz.trapmf(eo.universe, [-20, -20, -10, 0])
        eo['mantain'] = fuzz.trimf(eo.universe, [-5, 10, 25])
        eo['pull_light'] = fuzz.trimf(eo.universe, [20, 45, 70])
        eo['pull_strong'] = fuzz.trapmf(eo.universe, [60, 85, 100, 100])

        rai = self._variables['rudder_as_input']
        rai['total_left'] = fuzz.trapmf(rai.universe, [-100, -100, -80, -50])
        rai['partial_left'] = fuzz.trimf(rai.universe, [-70, -40, -10])
        rai['neutral'] = fuzz.trimf(rai.universe, [-20, 0, 20])
        rai['partial_right'] = fuzz.trimf(rai.universe, [10, 40, 70])
        rai['total_right'] = fuzz.trapmf(rai.universe, [50, 80, 100, 100])

    def _load_csv_rules(self, file_path: str) -> Union[dict, None]:
        """Reads the CSV files with the fuzzy ruleset"""
        try:
            regras_df = pd.read_csv(file_path, dtype=str).dropna(how='all')
            regras_df = regras_df.fillna('')
        except FileNotFoundError:
            print(f"ERRO: Arquivo de regras não encontrado em '{file_path}'")
            return None
        regras_fuzzy = []

        for index, row in regras_df.iterrows():
            if not row['antecedents']:
                continue
                
            clausulas_antecedentes = []
            antecedents_str_list = row['antecedents'].split(';')
            
            for item in antecedents_str_list:
                if ':' not in item: continue
                variavel, termo = item.split(':')
                clausula = self._variables[variavel.strip()][termo.strip()]
                clausulas_antecedentes.append(clausula)
            
            if not clausulas_antecedentes: continue

            clausula_final = clausulas_antecedentes[0]
            if len(clausulas_antecedentes) > 1:
                operador = row['operator']
                if operador == '&':
                    for i in range(1, len(clausulas_antecedentes)):
                        clausula_final &= clausulas_antecedentes[i]
                elif operador == '|':
                    for i in range(1, len(clausulas_antecedentes)):
                        clausula_final |= clausulas_antecedentes[i]
                else:
                    raise ValueError(f"Operador '{operador}' inválido na linha {index+2} do arquivo {file_path}")

            consequente = self._variables[row['consequent']][row['result']]
            
            regras_fuzzy.append(ctrl.Rule(clausula_final, consequente))
                
            print(f"Carregadas {len(regras_fuzzy)} regras de '{file_path}'")
            return regras_fuzzy
    
    def _create_rudder_output(self):
        rules = self._load_csv_rules(self.profile['rule_files']['rudder'])
        ctrl_system = ctrl.ControlSystem(rules)
        return ctrl.ControlSystemSimulation(ctrl_system)

    def _create_elevator_output(self):
        rules = self._load_csv_rules(self.profile['rule_files']['elevator'])
        self._variables['rudder_as_output'].automf(names=['total_left', 'partial_left', 'neutral', 'partial_right', 'total_right'])
        ctrl_system = ctrl.ControlSystem(rules)
        return ctrl.ControlSystemSimulation(ctrl_system)
    
    def calculate_outputs(self, sensor_data: dict) -> Union[dict, None]:
        try:
            self.rudder_sim.input['altitude'] = sensor_data['altitude']
            self.rudder_sim.input['crosswind'] = sensor_data['crosswind']
            self.rudder_sim.compute()
            rudder_output = self.rudder_sim.output['rudder_output']

            self.elevator_sim.inputs.clear()

            elevator_inputs = {ant.label for rule in self.elevator_sim.ctrl.rules for ant in rule.antecedent.terms}
            if 'altitude' in elevator_inputs: self.elevator_sim.input['altitude'] = sensor_data['altitude']
            if 'taxa_descida' in elevator_inputs: self.elevator_sim.input['taxa_descida'] = sensor_data['taxa_descida']
            if 'velocidade' in elevator_inputs: self.elevator_sim.input['velocidade'] = sensor_data['velocidade']
            if 'vento_traves' in elevator_inputs: self.elevator_sim.input['vento_traves'] = sensor_data['vento_traves']
            if 'leme_como_entrada' in elevator_inputs: self.elevator_sim.input['leme_como_entrada'] = rudder_output

            self.elevator_sim.compute()
            elevator_output = self.elevator_sim.output['elevator_output']

            return {'rudder_output': rudder_output, 'elevator_output': elevator_output}
        except Exception as e:
            print(f"ERROR during fuzzy calculation: {e}")
            return None