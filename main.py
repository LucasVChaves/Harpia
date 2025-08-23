import time
import airplane_profiles
import fuzzy_engine
import simulator_interface
from pathlib import Path

def select_airplane_profile() -> str | None:
    """Searches for airplanes profiles in the config folder"""
    profiles_path = Path("config/profiles")
    if not profiles_path.exists() or not profiles_path.is_dir():
        print(f"ERROR: Directory '{profiles_path}' not found")
        return None
    
    available_profiles = sorted([p.stem for p in profiles_path.glob("*.json")])
    if not available_profiles:
        print(f"ERRO: No available profiles (.json) found in '{profiles_path}'")
        return None
    
    print("\nPlease choose an aircraft profile:")
    for i, profile_name in enumerate(available_profiles):
        print(f"  [{i + 1}] - {profile_name}")

    while True:
        try:
            selection = input(f"Insert the chosen profile number (1-{len(available_profiles)}):")
            selection = int(selection)
            if 1 <= selection <= len(available_profiles):
                return available_profiles[selection - 1]
            else:
                print("Invalid selection. Choose one of the enumerated numbers.")
        except ValueError:
            print("Invalid input. Choose one of the enumerated numbers.")
        except KeyboardInterrupt:
            print("\n Selection interrupted by the user")
            return None


def main():
    print("Inicializing the flare assist program")

    profile = select_airplane_profile()
    if not profile:
        print("Killing program")
        return
    
    profile = airplane_profiles.load_profile(profile)
    if not profile:
        print("Could not find the profile. Killing program")
        return
    
    fuzzy_controller = fuzzy_engine.FuzzyController(airplane_profiles)
    simulator = simulator_interface.DummySimulator()

    print(f"Inicializing real time control loop (simulated)... Press Ctrl+c to exit.")
    try:
        while True:
            curr_data = simulator.read_rand_data()
            print(f"Reading data: Altitude={curr_data['altitude']:.1f}m, crosswind={curr_data['vento_traves']:.1f}m/s")

            output = fuzzy_controller.calculate_outputs(curr_data)
            if output:
                simulator.send_command(output)

            time.sleep(0.2) # 5 Hz
    except KeyboardInterrupt:
        print("\n Loop interrupt stopped by the user. Killing program.")