import json
from typing import Union

def load_profile(aircraft_name: str) -> Union[dict, None]:
    """Loads the configuration profile of a specific airplane from a JSON file in the config folder."""
    file_path = f"src/config/profiles/{aircraft_name}.json"
    try:
        with open(file_path, 'r') as f:
            profile = json.load(f)
            print(f"'{profile['name']}' profile loaded with success")
            return profile
    except FileNotFoundError:
        print(f"ERRO: Arquivo de perfil não encontrado em {file_path}")
        return None
