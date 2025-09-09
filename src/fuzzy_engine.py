import numpy as np 
import pandas as pd 
import skfuzzy as fuzz
from skfuzzy import control as ctrl
from typing import Union, List

class FuzzyController:
    def __init__(self, profile: dict):
        if not profile: raise ValueError("Profile cannot be null")
        self.profile = profile
        self._variables = {}
        self._create_variables()
        self._populate_membership_functions()
        self.rudder_sim = self._create_rudder_sim()
        self.elevator_sim = self._create_elevator_sim()
        print("Fuzzy Engine Inicialized")

    def _create_variables(self):
        """Create antecedents / consquents objects based on the profile ranges"""
        for name, params in self.profile['variables'].items():
            universe = np.arange(params['start'], params['stop'], params['step'])
            if 'output' in name:
                self._variables[name] = ctrl.Consequent(universe, name)
            else:
                self._variables[name] = ctrl.Antecedent(universe, name)

    def _populate_membership_functions(self):
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

        # Rudder as Input (for the Elevator SIF)
        rai = self._variables['rudder_as_input']
        rai['total_left'] = fuzz.trapmf(rai.universe, [-100, -100, -80, -50])
        rai['partial_left'] = fuzz.trimf(rai.universe, [-70, -40, -10])
        rai['neutral'] = fuzz.trimf(rai.universe, [-20, 0, 20])
        rai['partial_right'] = fuzz.trimf(rai.universe, [10, 40, 70])
        rai['total_right'] = fuzz.trapmf(rai.universe, [50, 80, 100, 100])

    def _load_csv_rules(self, file_path: str) -> List[ctrl.Rule]:
        """Reads a CSV file and converts it into a list of scikit-fuzzy rules."""
        try:
            df_rules = pd.read_csv(file_path, dtype=str).dropna(how='all').fillna('')
        except FileNotFoundError:
            print(f"ERROR: Rules file not found at '{file_path}'")
            return []

        fuzzy_rules = []
        for index, row in df_rules.iterrows():
            if not row['antecedents']: continue
            
            antecedents = []
            for item in row['antecedents'].split(';'):
                if ':' not in item: continue
                var, term = item.split(':')
                antecedents.append(self._variables[var.strip()][term.strip()])
            if not antecedents: continue

            if len(antecedents) > 1:
                operator = row['operator']
                if operator == '&':
                    final_antecedent = np.bitwise_and.reduce(antecedents)
                elif operator == '|':
                    final_antecedent = np.bitwise_or.reduce(antecedents)
                else:
                    raise ValueError(f"Invalid operator '{operator}' at line {index+2} in '{file_path}'")
            else:
                final_antecedent = antecedents[0]

            consequent_clause = self._variables[row['consequent']][row['result']]
            fuzzy_rules.append(ctrl.Rule(final_antecedent, consequent_clause))
        
        print(f"{len(fuzzy_rules)} rules were loaded from '{file_path}'")
        return fuzzy_rules

    def _create_rudder_sim(self):
        rules = self._load_csv_rules(self.profile['rule_files']['rudder'])
        ctrl_system = ctrl.ControlSystem(rules)
        return ctrl.ControlSystemSimulation(ctrl_system)

    def _create_elevator_sim(self):
        rules = self._load_csv_rules(self.profile['rule_files']['elevator'])
        self._variables['rudder_as_output'].automf(names=['total_left', 'partial_left', 'neutral', 'partial_right', 'total_right'])
        ctrl_system = ctrl.ControlSystem(rules)
        return ctrl.ControlSystemSimulation(ctrl_system)

    def calculate_outputs(self, sensor_data: dict) -> Union[dict, None]:
        """Calculates the control outputs in series (Rudder -> Elevator)."""
        try:
            # --- Rudder Simulation ---
            self.rudder_sim.input['altitude'] = sensor_data['altitude']
            self.rudder_sim.input['crosswind'] = sensor_data['crosswind']
            self.rudder_sim.compute()
            rudder_output = self.rudder_sim.output['rudder_output']

            # --- Elevator Simulation ---
            self.elevator_sim.input['altitude'] = sensor_data['altitude']
            self.elevator_sim.input['descent_rate'] = sensor_data['descent_rate']
            self.elevator_sim.input['airspeed'] = sensor_data['airspeed']
            self.elevator_sim.input['crosswind'] = sensor_data.get('crosswind', 0)
            self.elevator_sim.input['rudder_as_input'] = rudder_output

            self.elevator_sim.compute()
            elevator_output = self.elevator_sim.output['elevator_output']

            return {'rudder_output': rudder_output, 'elevator_output': elevator_output}
        except (ValueError, KeyError) as e:
            print(f"WARNING: Could not calculate output for the current scenario. Error: {e}")
            return None
