import time
import airplane_profiles
import fuzzy_engine
import simulator_interface
from pathlib import Path

def select_airplane_profile() -> str | None:
    """Searches for airplanes profiles in the config folder"""
    profiles_path = Path("src/config/profiles")
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
    print("Initializing the Flare Assist program...")

    profile_name = select_airplane_profile()
    if not profile_name:
        print("No profile selected. Killing program.")
        return
    
    loaded_profile = airplane_profiles.load_profile(profile_name)
    if not loaded_profile:
        print("Could not load the profile. Killing program.")
        return
    
    fuzzy_controller = fuzzy_engine.FuzzyController(loaded_profile)
    simulator = simulator_interface.DummySimulator()

    print(f"\nInitializing real-time control loop (simulated)... Press Ctrl+C to exit.")
    try:
        while True:
            current_data = simulator.read_rand_data()
            print(f"\nReading data: Altitude={current_data['altitude']:.1f}m, Crosswind={current_data['crosswind']:.1f}m/s")

            commands = fuzzy_controller.calculate_outputs(current_data)
            if commands:
                simulator.send_command(commands)

            time.sleep(0.2) # 5 Hz loop frequency
    except KeyboardInterrupt:
        print("\nControl loop stopped by the user. Killing program.")

if __name__ == "__main__":
    main()
