import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import json
import time
import os
from typing import Dict, Any, Optional
from functools import lru_cache
from dotenv import load_dotenv

# Cargar variables de entorno desde .env
load_dotenv()

# ============================================
# CONFIGURACIÓN
# ============================================
TOKEN = os.getenv("API_TOKEN")

if not TOKEN:
    print("❌ ERROR: No se encontró API_TOKEN")
    print("   Crea un archivo .env con: API_TOKEN=tu_token")
    exit(1)

HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json"
}

BASE_URL = "https://recruiting.adere.so"
SWAPI_URL = "https://swapi.dev/api"
POKEAPI_URL = "https://pokeapi.co/api/v2"

# Crear sesión HTTP con reintentos automáticos
session = requests.Session()
retry = Retry(
    total=3,
    backoff_factor=0.3,
    status_forcelist=[500, 502, 503, 504]
)
adapter = HTTPAdapter(max_retries=retry, pool_connections=10, pool_maxsize=10)
session.mount('http://', adapter)
session.mount('https://', adapter)

# ============================================
# FUNCIONES PARA CONSULTAR APIs (CON CACHE)
# ============================================

@lru_cache(maxsize=128)
def get_star_wars_character(name: str) -> Optional[Dict]:
    """Obtiene información de un personaje de Star Wars"""
    try:
        response = session.get(f"{SWAPI_URL}/people/?search={name}", timeout=10)
        data = response.json()
        if data['results']:
            char = data['results'][0]
            # Obtener el nombre del homeworld
            homeworld_url = char.get('homeworld')
            homeworld_name = None
            if homeworld_url:
                hw_response = session.get(homeworld_url, timeout=10)
                homeworld_name = hw_response.json().get('name')
            
            return {
                'name': char['name'],
                'height': float(char['height']) if char['height'] != 'unknown' else 0,
                'mass': float(char['mass'].replace(',', '')) if char['mass'] != 'unknown' else 0,
                'homeworld': homeworld_name
            }
    except Exception as e:
        print(f"⚠️ Error obteniendo personaje {name}: {e}")
    return None

@lru_cache(maxsize=128)
def get_star_wars_planet(name: str) -> Optional[Dict]:
    """Obtiene información de un planeta de Star Wars"""
    try:
        response = session.get(f"{SWAPI_URL}/planets/?search={name}", timeout=10)
        data = response.json()
        if data['results']:
            planet = data['results'][0]
            return {
                'name': planet['name'],
                'rotation_period': float(planet['rotation_period']) if planet['rotation_period'] != 'unknown' else 0,
                'orbital_period': float(planet['orbital_period']) if planet['orbital_period'] != 'unknown' else 0,
                'diameter': float(planet['diameter']) if planet['diameter'] != 'unknown' else 0,
                'surface_water': float(planet['surface_water']) if planet['surface_water'] != 'unknown' else 0,
                'population': float(planet['population']) if planet['population'] != 'unknown' else 0
            }
    except Exception as e:
        print(f"⚠️ Error obteniendo planeta {name}: {e}")
    return None

@lru_cache(maxsize=128)
def get_pokemon(name: str) -> Optional[Dict]:
    """Obtiene información de un Pokémon"""
    try:
        response = session.get(f"{POKEAPI_URL}/pokemon/{name.lower()}", timeout=10)
        data = response.json()
        return {
            'name': data['name'],
            'base_experience': float(data['base_experience']) if data['base_experience'] else 0,
            'height': float(data['height']),
            'weight': float(data['weight'])
        }
    except Exception as e:
        print(f"⚠️ Error obteniendo pokemon {name}: {e}")
    return None

# ============================================
# FUNCIÓN PARA INTERPRETAR PROBLEMA CON IA
# ============================================

def interpret_problem(problem_text: str) -> Dict[str, Any]:
    """Usa IA para interpretar el problema y extraer la operación"""
    
    prompt = f"""Analiza este problema y convierte a JSON.

PROBLEMA: {problem_text}

PASO 1 - Identifica entidades:
- Personajes de Star Wars
- Planetas de Star Wars  
- Pokémon

PASO 2 - Convierte la operación matemática a Python usando estas reglas ESTRICTAS:
- Primer personaje en la lista → character1
- Segundo personaje en la lista → character2
- Primer planeta en la lista → planet1
- Segundo planeta en la lista → planet2
- Primer pokémon en la lista → pokemon1
- Segundo pokémon en la lista → pokemon2

ATRIBUTOS:
- character1.height, character1.mass, character1.homeworld
- planet1.rotation_period, planet1.orbital_period, planet1.diameter, planet1.surface_water, planet1.population
- pokemon1.base_experience, pokemon1.height, pokemon1.weight

EJEMPLO:
Problema: "Luke (masa 77) entrena con Pikachu (experiencia 112). Multiplica la masa de Luke por la experiencia de Pikachu."
Respuesta correcta:
{{
  "characters": ["Luke Skywalker"],
  "planets": [],
  "pokemon": ["Pikachu"],
  "operation": "character1.mass * pokemon1.base_experience"
}}

RESPONDE SOLO JSON (sin markdown, sin texto extra):
{{
  "characters": [...],
  "planets": [...],
  "pokemon": [...],
  "operation": "..."
}}"""

    try:
        response = session.post(
            f"{BASE_URL}/chat_completion",
            headers=HEADERS,
            json={
                "model": "gpt-4o-mini",
                "messages": [
                    {"role": "developer", "content": "Extrae información estructurada. Responde SOLO JSON válido."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.1  # Más determinístico
            },
            timeout=15
        )
        
        content = response.json()['choices'][0]['message']['content'].strip()
        
        # Limpiar markdown
        if content.startswith('```'):
            lines = content.split('\n')
            content = '\n'.join(lines[1:-1])
            if content.startswith('json'):
                content = content[4:]
        
        return json.loads(content.strip())
    except Exception as e:
        print(f"⚠️ Error interpretando: {e}")
        return None

# ============================================
# FUNCIÓN PARA RESOLVER PROBLEMA
# ============================================

def solve_problem(problem_text: str, verbose: bool = True) -> Optional[float]:
    """Resuelve un problema completo"""
    
    # 1. Interpretar
    interpretation = interpret_problem(problem_text)
    if not interpretation:
        return None
    
    if verbose:
        print(f"🧠 Interpretación: {json.dumps(interpretation, ensure_ascii=False)}")
    
    # 2. Obtener datos
    entities = {}
    
    # Personajes
    for i, char_name in enumerate(interpretation.get('characters', []), 1):
        char_data = get_star_wars_character(char_name)
        if char_data:
            entities[f'character{i}'] = char_data
            if verbose:
                print(f"✓ {char_name}: height={char_data['height']}, mass={char_data['mass']}")
    
    # Planetas
    for i, planet_name in enumerate(interpretation.get('planets', []), 1):
        planet_data = get_star_wars_planet(planet_name)
        if planet_data:
            entities[f'planet{i}'] = planet_data
            if verbose:
                print(f"✓ {planet_name}: orbital={planet_data['orbital_period']}")
    
    # Pokémon
    for i, pokemon_name in enumerate(interpretation.get('pokemon', []), 1):
        pokemon_data = get_pokemon(pokemon_name)
        if pokemon_data:
            entities[f'pokemon{i}'] = pokemon_data
            if verbose:
                print(f"✓ {pokemon_name}: exp={pokemon_data['base_experience']}")
    
    # 3. Evaluar
    try:
        class Entity:
            def __init__(self, data):
                for key, value in data.items():
                    setattr(self, key, value)
        
        namespace = {name: Entity(data) for name, data in entities.items()}
        operation = interpretation['operation']
        
        if verbose:
            print(f"🔢 Operación: {operation}")
        
        result = eval(operation, {"__builtins__": {}}, namespace)
        result = round(result, 10)
        
        if verbose:
            print(f"✅ Resultado: {result}")
        
        return result
        
    except Exception as e:
        print(f"❌ Error evaluando: {e}")
        return None

# ============================================
# MODO PRÁCTICA
# ============================================

def test_practice():
    """Prueba con el endpoint de práctica"""
    print("\n" + "="*50)
    print("🧪 MODO PRÁCTICA")
    print("="*50 + "\n")
    
    try:
        response = session.get(f"{BASE_URL}/challenge/test", headers=HEADERS, timeout=10)
        
        if response.status_code != 200:
            print(f"❌ Error HTTP {response.status_code}: {response.text}")
            return
        
        data = response.json()
        
        print("📦 Respuesta del servidor:")
        print(json.dumps(data, indent=2, ensure_ascii=False))
        print("\n" + "="*50 + "\n")
        
        if 'problem' not in data:
            print("❌ No hay campo 'problem'")
            return
        
        print(f"📝 Problema:\n{data['problem']}\n")
        
        # Verificar si tiene la solución
        has_solution = 'solution' in data
        if has_solution:
            print(f"🎯 Solución esperada: {data['solution']}")
            
        # Verificar si tiene la expresión
        if 'expression' in data:
            print(f"📐 Expresión correcta: {data['expression']}\n")
        
        result = solve_problem(data['problem'], verbose=True)
        
        if result is not None:
            print(f"\n{'='*50}")
            print(f"✅ Tu solución: {result}")
            
            if has_solution:
                expected = data['solution']
                match = abs(result - expected) < 1e-9
                print(f"💯 {'✓ CORRECTO' if match else '✗ INCORRECTO'}")
                if not match:
                    print(f"   Esperado: {expected}")
                    print(f"   Obtenido: {result}")
                    print(f"   Diferencia: {abs(result - expected)}")
            print("="*50)
        else:
            print("\n❌ No se pudo resolver")
            if has_solution:
                print(f"La respuesta correcta era: {data['solution']}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

# ============================================
# DESAFÍO REAL (OPTIMIZADO)
# ============================================

def run_challenge():
    """Ejecuta el desafío real optimizado"""
    print("\n" + "="*50)
    print("🚀 INICIANDO DESAFÍO REAL")
    print("="*50 + "\n")
    
    start_time = time.time()
    problems_solved = 0
    problems_attempted = 0
    
    try:
        # Iniciar
        response = session.get(f"{BASE_URL}/challenge/start", headers=HEADERS, timeout=10)
        current_problem = response.json()
        
        while time.time() - start_time < 175:  # Terminar 5s antes
            problems_attempted += 1
            elapsed = int(time.time() - start_time)
            
            print(f"\n{'='*50}")
            print(f"⏱️  {elapsed}s | Problema #{problems_attempted} | Resueltos: {problems_solved}")
            print(f"{'='*50}\n")
            
            # Resolver con menos verbosidad
            answer = solve_problem(current_problem['problem'], verbose=False)
            
            if answer is None:
                print("⚠️ Saltando problema...")
                answer = 0
            else:
                print(f"✅ Respuesta: {answer}")
            
            # Enviar
            try:
                response = session.post(
                    f"{BASE_URL}/challenge/solution",
                    headers=HEADERS,
                    json={
                        "problem_id": current_problem['id'],
                        "answer": answer
                    },
                    timeout=10
                )
                
                result = response.json()
                
                if 'problem' in result:
                    problems_solved += 1
                    current_problem = result
                else:
                    print(f"\n🏁 Fin: {result}")
                    break
                    
            except Exception as e:
                print(f"❌ Error enviando: {e}")
                break
        
        elapsed = int(time.time() - start_time)
        print(f"\n{'='*50}")
        print(f"🏁 DESAFÍO COMPLETADO")
        print(f"📊 Resueltos: {problems_solved}/{problems_attempted}")
        print(f"⏱️  Tiempo: {elapsed}s")
        print(f"⚡ Velocidad: {problems_solved/(elapsed/60):.1f} problemas/minuto")
        print(f"{'='*50}\n")
        
    except Exception as e:
        print(f"❌ Error crítico: {e}")
        import traceback
        traceback.print_exc()

# ============================================
# MENÚ
# ============================================

if __name__ == "__main__":
    print("="*50)
    print("🌟 ADERESO CHALLENGE SOLVER - OPTIMIZED")
    print("="*50)
    
    print("\n1. 🧪 Modo Práctica")
    print("2. 🚀 Desafío Real (3 min)")
    print("3. 🔥 Práctica Rápida (5 veces)")
    
    choice = input("\nOpción: ")
    
    if choice == "1":
        test_practice()
    elif choice == "2":
        confirm = input("\n⚠️ ¿Comenzar desafío real? (s/n): ")
        if confirm.lower() == 's':
            print("\n🔥 Iniciando en 3 segundos...")
            time.sleep(3)
            run_challenge()
    elif choice == "3":
        for i in range(5):
            print(f"\n{'='*50}")
            print(f"PRUEBA {i+1}/5")
            print(f"{'='*50}")
            test_practice()
            time.sleep(1)
    else:
        print("Opción inválida")