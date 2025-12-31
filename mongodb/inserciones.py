import pandas as pd
import ast
from pymongo import MongoClient

def mongoConnect(host = "localhost", port = "27017"):
    """Permite conexión con MongoDB asociado a un puerto y host específicos"""
    connection_string = f"mongodb://{host}:{port}/"
    try:
        client = MongoClient(connection_string, serverSelectionTimeoutMS=3000)
        client.admin.command('ping')
        print("Conexión exitosa a MongoDB")
        return client
    except Exception as e:
        print(f"Error al conectar: {e}")
        return 
    
def cargarMetro(dir = "estaciones.csv"):
    """
    ## Definición
 
    Genera la colección de estaciones en base a un csv válido y dinámicamente crea la colección con toda la información obtenida de las líneas.

    ## Parámetros

    Dir : dirección de archivo csv con el contenido de las estaciones para crear las colecciones.
    
    ## Return

    Devuelve una lista con los objetos a añadir a la coleción de estaciones y a la colección de líneas
    """
    estaciones = pd.read_csv(dir)
    estaciones_colection = []
    lineas_map = {}

    # Procesamiento de las estaciones
    for _,estacion in estaciones.iterrows():
        tieneRenfe = len(ast.literal_eval(estacion['RENFE'])) > 0
        item = {
            "nombre": estacion['DENOMINACION'],
            "fecha_creación": estacion["FECHAINICIO"],
            "zona": estacion['CORONATARIFARIA'],
            "ubicacion": {"x": estacion['X'], "y": estacion['Y']},
            "tipo_via" : estacion["TIPOVIA"],
            "grado_accesibilidad": estacion["GRADOACCESIBILIDAD"],
            "lineas_ids": ast.literal_eval(estacion['LINEAS']),
            "tieneRenfe": tieneRenfe
        }
        if tieneRenfe: item["detallesRenfe"] = ast.literal_eval(estacion['RENFE'])
        
        estaciones_colection.append(item)

        #Añadir la info de la colección de lineas
        for linea in item["lineas_ids"]:
            id_linea = linea['linea']
            if id_linea not in lineas_map:
                lineas_map[id_linea] = []
           
            lineas_map[id_linea].append({
                "nombre_estacion": estacion['DENOMINACION'],
                "indiceEnLinea": linea['orden']
            })

    # Procesamiento de las líneas
    lineas_collection = []
    for id_l, lista_estaciones in lineas_map.items():
        lista_estaciones.sort(key=lambda x: x['indiceEnLinea'])
        doc_linea = {
            "linea_id": id_l,
            "estaciones": lista_estaciones,
            "total_estaciones": len(lista_estaciones)
        }
        lineas_collection.append(doc_linea)
    
    return (estaciones_colection,lineas_collection)

def cargarUniversidad(dirCampus = "campus.csv", dirEstudios = "estudios.csv"):
    campus_df = pd.read_csv(dirCampus)
    estudios_df = pd.read_csv(dirEstudios)

    # Procesar Estudios: Determinar si es GRADO o MÁSTER
    estudios_list = []
    for _, est in estudios_df.iterrows():
        nombre_estudio = est['Estudios']
        tipo = "GRADO" if "Grado" in nombre_estudio else "MÁSTER"
        
        estudios_list.append({
            "nombre": nombre_estudio,
            "universidad": est['Universidad'],
            "campus": est['Campus'].strip(),
            "tipo": tipo,
            "creditos": est['Créditos'],
            "coordinador": est['Coordinador']
        })

    # Procesar Campus y Embeber Estudios
    campus_docs = []
    for _, camp in campus_df.iterrows():
        nombre_campus = camp['Campus'].strip()
        
        # Filtramos los estudios que pertenecen a este campus para embeberlos
        estudios_del_campus = [
            {"nombre": e['nombre'], "tipo": e['tipo']} 
            for e in estudios_list if e['campus'].upper() == nombre_campus.upper()
        ]

        # Estructuramos las estaciones cercanas (Requisito: rol principal/alternativa)
        estaciones = []
        if pd.notna(camp['Estación_Principal']):
            estaciones.append({
                "nombre": camp['Estación_Principal'],
                "minutos": camp['Tiempo_Principal'],
                "rol": "principal"
            })
        if pd.notna(camp['Estación_Alternativa']):
            estaciones.append({
                "nombre": camp['Estación_Alternativa'],
                "minutos": camp['Tiempo_Alternativa'],
                "rol": "alternativa"
            })

        doc_campus = {
            "nombre": nombre_campus,
            "universidad": camp['Universidad'],
            "coordenadas": {"x": camp['X'], "y": camp['Y']},
            "estaciones_cercanas": estaciones,
            "estudios": estudios_del_campus
        }
        campus_docs.append(doc_campus)

    return campus_docs


def main():
    #Conexión y limpieza de la base de datos
    client = mongoConnect()
    if not client:
        return 
    db = client["Practica2_DB"]

    # Borrar las colecciones si ya existen para empezar de cero en cada ejecución
    db.estaciones.drop()
    db.lineas.drop()
    db.estudios.drop()
    db.campus.drop()

    # Creación de las colecciones de lineas y estaciones
    estaciones, lineas = cargarMetro(dir = "estaciones.csv")
    db.estaciones.insert_many(estaciones)
    db.lineas.insert_many(lineas)
    print(f"Insertadas {len(estaciones)} estaciones y {len(lineas)} líneas.")

    # Creación de la colección de campus con estudios embebidos
    campus = cargarUniversidad(dirCampus= "campus.csv",dirEstudios="estudios.csv")
    db.campus.insert_many(campus)
    print(f"Insertadas {len(campus)} campus.")
    

if __name__ == "__main__":
    main()