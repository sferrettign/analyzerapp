import requests
import webbrowser
import json

# ---- CONFIGURACIÓN ----
# ¡REEMPLAZA ESTOS VALORES CON LOS TUYOS!
APP_ID = '8124944839883970'  # También conocido como Client ID
CLIENT_SECRET = 'ApMUdaSXq4JbnIcmumfd53egwblUW1AD'
REDIRECT_URI = 'https://sferrettign.github.io/analyzerapp/callback.html' # La que configuraste
# Elige tu país (ej: MLA para Argentina, MLB para Brasil, MLM para México, etc.)
# Puedes encontrar la lista aquí: https://api.mercadolibre.com/sites
SITE_ID = 'MLC' # Ejemplo para Argentina

# URLs de la API de Mercado Libre (pueden variar ligeramente por país, pero suelen ser estas)
AUTH_URL = f'https://auth.mercadolibre.cl/authorization' # Adapta ".com.ar" a tu país si es diferente
TOKEN_URL = f'https://api.mercadolibre.cl/oauth/token'
API_BASE_URL = f'https://api.mercadolibre.cl'

access_token = None
refresh_token = None

# ---- PARTE 1: AUTENTICACIÓN ----

def get_authorization_url():
    """Genera la URL para que el usuario autorice la aplicación."""
    params = {
        'response_type': 'code',
        'client_id': APP_ID,
        'redirect_uri': REDIRECT_URI
    }
    # Construir la URL con parámetros
    auth_full_url = AUTH_URL + '?' + requests.compat.urlencode(params)
    return auth_full_url

def exchange_code_for_token(auth_code):
    """Intercambia el código de autorización por un access token."""
    global access_token, refresh_token
    payload = {
        'grant_type': 'authorization_code',
        'client_id': APP_ID,
        'client_secret': CLIENT_SECRET,
        'code': auth_code,
        'redirect_uri': REDIRECT_URI
    }
    headers = {
        'accept': 'application/json',
        'content-type': 'application/x-www-form-urlencoded'
    }
    try:
        response = requests.post(TOKEN_URL, data=payload, headers=headers, timeout=10)
        response.raise_for_status()  # Lanza una excepción para códigos de error HTTP (4XX o 5XX)
        token_data = response.json()
        
        access_token = token_data.get('access_token')
        refresh_token = token_data.get('refresh_token') # Útil para obtener nuevos access_tokens sin pedir al usuario que se loguee de nuevo
        
        if access_token:
            print("\n--- ¡Access Token obtenido exitosamente! ---")
            print(f"Access Token: {access_token[:20]}...") # Muestra solo una parte por seguridad
            if refresh_token:
                print(f"Refresh Token: {refresh_token[:20]}...")
            print(f"Expira en: {token_data.get('expires_in')} segundos")
            return True
        else:
            print("\n--- Error: No se pudo obtener el Access Token. ---")
            print("Respuesta del servidor:", token_data)
            return False
            
    except requests.exceptions.HTTPError as http_err:
        print(f"\n--- Error HTTP al obtener token: {http_err} ---")
        print("Respuesta del servidor:", response.text)
    except requests.exceptions.RequestException as req_err:
        print(f"\n--- Error de Red al obtener token: {req_err} ---")
    except json.JSONDecodeError:
        print("\n--- Error: La respuesta del servidor de tokens no es un JSON válido. ---")
        print("Respuesta del servidor:", response.text)
    return False

def authenticate():
    """Maneja el flujo completo de autenticación."""
    global access_token
    if access_token:
        print("Ya estás autenticado.")
        return True

    auth_url = get_authorization_url()
    print("--- Autenticación Requerida ---")
    print("1. Se abrirá una ventana en tu navegador para autorizar la aplicación.")
    print("2. Después de autorizar, serás redirigido a tu página de callback.")
    print("3. Copia el 'código de autorización' que aparece en esa página.")
    webbrowser.open(auth_url)
    
    auth_code = input("4. Pega el código de autorización aquí y presiona Enter: ")
    
    if auth_code:
        return exchange_code_for_token(auth_code.strip())
    else:
        print("No se ingresó ningún código.")
        return False

# ---- PARTE 2: CONSULTAR API PARA OFERTA Y DEMANDA ----

def search_products(query, limit=10):
    """Busca productos en Mercado Libre."""
    if not access_token:
        print("Error: Necesitas autenticarte primero para buscar productos.")
        if not authenticate(): # Intenta autenticar si no hay token
            return None

    headers = {
        'Authorization': f'Bearer {access_token}'
    }
    params = {
        'q': query,
        'limit': limit,
        # Puedes añadir más parámetros como 'offset', 'sort', 'category', etc.
        # Ver documentación: https://developers.mercadolibre.com.ar/es_ar/items-y-busquedas
    }
    
    search_url = f"{API_BASE_URL}/sites/{SITE_ID}/search"
    
    try:
        print(f"\nBuscando '{query}' en {SITE_ID}...")
        response = requests.get(search_url, headers=headers, params=params, timeout=10)
        response.raise_for_status()
        search_results = response.json()
        return search_results
        
    except requests.exceptions.HTTPError as http_err:
        print(f"--- Error HTTP al buscar productos: {http_err} ---")
        print("Respuesta:", response.text)
        if response.status_code == 401: # Unauthorized
            print("El Access Token podría haber expirado o ser inválido. Intenta autenticarte de nuevo.")
            # Aquí podrías implementar la lógica para usar el refresh_token si lo tienes
            access_token = None # Forzar re-autenticación la próxima vez
    except requests.exceptions.RequestException as req_err:
        print(f"--- Error de Red al buscar productos: {req_err} ---")
    except json.JSONDecodeError:
        print("--- Error: La respuesta de búsqueda no es un JSON válido. ---")
        print("Respuesta:", response.text)
    return None

def analyze_offer_demand(search_results):
    """
    Analiza los resultados de búsqueda para inferir oferta y demanda.
    Este es un análisis MUY BÁSICO.
    """
    if not search_results or 'results' not in search_results:
        print("No hay resultados para analizar.")
        return

    total_results = search_results.get('paging', {}).get('total', 0)
    print(f"\n--- Análisis Básico de '{search_results.get('query')}' ---")
    print(f"Oferta (Total de publicaciones encontradas): {total_results}")

    if not search_results['results']:
        print("No se encontraron productos específicos en esta página para un análisis más detallado.")
        return

    print("\nAlgunos productos y su 'demanda' (cantidad vendida):")
    high_demand_items = []
    total_sold_on_page = 0

    for item in search_results['results'][:10]: # Analiza los primeros 10 de la página
        title = item.get('title', 'N/A')
        price = item.get('price', 0)
        currency = item.get('currency_id', '')
        sold_quantity = item.get('sold_quantity', 0)
        permalink = item.get('permalink', '#')
        
        print(f"- Título: {title[:60]}...")
        print(f"  Precio: {price} {currency}")
        print(f"  Cantidad Vendida: {sold_quantity}")
        # print(f"  Link: {permalink}")
        
        total_sold_on_page += sold_quantity
        if sold_quantity > 50: # Umbral arbitrario para "alta demanda"
            high_demand_items.append({'title': title, 'sold_quantity': sold_quantity})

    print(f"\nTotal de unidades vendidas (estimado de esta página): {total_sold_on_page}")
    
    if high_demand_items:
        print("\nPosibles productos con mayor demanda (en esta página):")
        for hd_item in high_demand_items:
            print(f"  - {hd_item['title'][:60]}... (Vendidos: {hd_item['sold_quantity']})")
    
    # Ideas para un análisis más profundo (más allá de este script básico):
    # - Historial de precios (requiere seguimiento en el tiempo, no directo de esta API)
    # - Número de vendedores diferentes para el mismo producto.
    # - Velocidad de venta (si se monitorea `sold_quantity` a lo largo del tiempo).
    # - Analizar preguntas y respuestas de los productos.
    # - Comparar precios entre vendedores.
    # - Utilizar filtros de categorías, condición (nuevo/usado), etc.

# ---- EJECUCIÓN PRINCIPAL ----
if __name__ == "__main__":
    # 1. Autenticar (solo la primera vez o si el token expira)
    if not authenticate():
        print("No se pudo autenticar. Saliendo.")
        exit()

    # 2. Realizar una búsqueda y análisis
    while True:
        search_query = input("\nIngresa el producto que quieres analizar (o 'salir' para terminar): ")
        if search_query.lower() == 'salir':
            break
        if not search_query.strip():
            print("Por favor, ingresa un término de búsqueda.")
            continue
            
        results = search_products(search_query, limit=20) # Pedimos más resultados para el análisis
        if results:
            analyze_offer_demand(results)
        else:
            print(f"No se pudo obtener información para '{search_query}'.")
            
    print("\n¡Hasta luego!")