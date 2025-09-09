import numpy as np

class DummySimulator:
    def __init__(self):
        print('Dummy Simulator started')

    def read_rand_data(self):
        """Generates random dummy sensor data for tests"""
        data = {
            'altitude': np.random.uniform(0, 10),
            'descent_rate': np.random.uniform(0.5, 4.5),
            'airspeed': np.random.uniform(25, 38),
            'crosswind': np.random.uniform(-8, 8)
        }
        return data
    
    def send_command(self, commands: dict):
        """Prints the received commands"""
        if commands:
            print(f"SIMULATOR: Received outputs: RUDDER: {commands['rudder_output']:.2f}, ELEVATOR: {commands['elevator_output']}")