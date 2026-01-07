import os
from pymongo import MongoClient
import time



CONSULTAS = [
    {
        "id": "Q1_LINEAS",
        "descripcion": "Listar estaciones de L1 (Aggregate)",
        "tipo": "aggregate",
        "coleccion": "lineas",
        "pipeline": [
            {"$match": {"linea_id": "1"}},
            {"$unwind": "$estaciones"},
            {"$sort": {"estaciones.indiceEnLinea": 1}},
            {"$project": {"_id": 0, "nombre": "$estaciones.nombre_estacion", "indice": "$estaciones.indiceEnLinea"}}
        ]
    },
    {
        "id": "Q2_RENFE",
        "descripcion": "Estaciones con RENFE (Find)",
        "tipo": "find",
        "coleccion": "estaciones",
        "filtro": {"tieneRenfe": True},
        "proyeccion": {"_id": 0, "nombre": 1, "detallesRenfe": 1}
    },
    {
        "id": "Q3_ACCESIBILIDAD",
        "descripcion": "Estaciones Zona A Accesibles (Find)",
        "tipo": "find",
        "coleccion": "estaciones",
        "filtro": {"zona": "A", "grado_accesibilidad": {"$ne": "N"}},
        "proyeccion": {"_id": 0, "nombre": 1}
    },
    {
        "id": "Q4_CAMPUS_UNIV",
        "descripcion": "Campus de la Complutense (Find)",
        "tipo": "find",
        "coleccion": "campus",
        "filtro": {"universidad": "Universidad Complutense de Madrid"},
        "proyeccion": {"_id": 0, "nombre": 1, "universidad": 1}
    },
    {
        "id": "Q5_CAMPUS_ESTACION",
        "descripcion": "Campus cerca de 'Getafe Central' (ElemMatch)",
        "tipo": "find",
        "coleccion": "campus",
        "filtro": {"estaciones_cercanas": {"$elemMatch": {"nombre": "GETAFE CENTRAL", "rol": "principal"}}},
        "proyeccion": {"_id": 0, "nombre": 1, "universidad": 1}
    },
    {
        "id": "Q6_GRADOS",
        "descripcion": "Listar Grados (Aggregate + Sort)",
        "tipo": "aggregate",
        "coleccion": "campus",
        "pipeline": [
            {"$unwind": "$estudios"},
            {"$match": {"estudios.tipo": "GRADO"}},
            {"$project": {"_id": 0, "nombre": "$estudios.nombre", "nombreCampus": "$nombre", "universidad": 1}},
            {"$sort": {"nombre": 1}}
        ]
    }
]

CONFIGURACIONES_INDICES = [
    {
        "nombre": "ESCENARIO 0: Base de datos limpia (Sin índices)",
        "indices_a_crear": []
    },
    {
        "nombre": "ESCENARIO 1: Índices Básicos (Simples)",
        "indices_a_crear": [
            ("lineas", "linea_id", 1),
            ("estaciones", "tieneRenfe", 1),
            ("campus", "universidad", 1)
        ]
    },
    {
        "nombre": "ESCENARIO 2: Índices Avanzados (Compuestos y Arrays)",
        "indices_a_crear": [
            ("estaciones", [("zona", 1), ("grado_accesibilidad", 1)]),
            ("campus", "estaciones_cercanas.nombre", 1), 
            ("campus", "estudios.nombre", 1) 
        ]
    }
]


def obtener_stats(db, consulta):
    coll = db[consulta["coleccion"]]
    # Forzamos int() aquí por seguridad
    total_docs_coleccion = int(coll.count_documents({}))
    
    try:
        if consulta["tipo"] == "find":
            cursor = coll.find(consulta["filtro"], consulta["proyeccion"])
            stats = cursor.explain()["executionStats"]
            # Convertimos a int para evitar el error de tipos
            return int(stats["totalDocsExamined"]), int(stats["executionTimeMillis"]), total_docs_coleccion
            
        elif consulta["tipo"] == "aggregate":
            cmd = {
                "explain": {
                    "aggregate": consulta["coleccion"],
                    "pipeline": consulta["pipeline"],
                    "cursor": {}
                },
                "verbosity": "executionStats"
            }
            res = db.command(cmd)
            
            # Ajuste para diferentes estructuras de respuesta según versión de Mongo
            if "executionStats" in res:
                stats = res["executionStats"]
            else:
                stats = res["stages"][0]["$cursor"]["executionStats"]
            
            # Convertimos a int
            return int(stats["totalDocsExamined"]), int(stats["executionTimeMillis"]), total_docs_coleccion
            
    except Exception as e:
        # En caso de error, devolvemos -1 para manejarlo en el main
        print(f"Error interno en {consulta['id']}: {e}")
        return -1, -1, total_docs_coleccion
    
def limpiar_indices(db):
    """Borra todos los índices (menos _id) de las colecciones usadas"""
    for col_name in ["estaciones", "lineas", "campus"]:
        db[col_name].drop_indexes()

def aplicar_indices(db, lista_indices):
    """Crea los índices definidos en la configuración"""
    for item in lista_indices:
        col_name = item[0]
        if isinstance(item[1], list):
            # Es compuesto
            campos = item[1]
            db[col_name].create_index(campos)
        else:
            # Es simple
            campo = item[1]
            direccion = item[2]
            db[col_name].create_index([(campo, direccion)])

def main():
    MONGO_URL = "mongodb://127.0.0.1:27017"
    client = MongoClient(MONGO_URL)
    db = client["Practica2_DB"]
    
    print(f"{'='*100}")
    print(f"{'BENCHMARK DE ÍNDICES: Docs Examinados vs Resultados':^100}")
    print(f"{'='*100}")

    # Iteración por escenarios (diferentes índices)
    for config in CONFIGURACIONES_INDICES:
        print(f"\n>>> APLICANDO {config['nombre']}")
        
        limpiar_indices(db)
        aplicar_indices(db, config["indices_a_crear"])
        
        print(f"{'-'*110}")
        print(f"{'ID':<18} | {'Docs Leídos / Total':<20} | {'Tiempo':<8} | {'Eficiencia'}")
        print(f"{'-'*110}")

        for q in CONSULTAS:
            docs, tiempo, total = obtener_stats(db, q)
            
            ratio_str = f"{docs}/{total}"
            
            if docs == -1:
                evaluacion = "ERROR INT"
            elif docs == 0 and total > 0:
                evaluacion = "OPTIMO (Covered)"
            
            elif total > 0 and docs >= total:
                evaluacion = "SCAN TOTAL"
            elif docs <= 5:
                evaluacion = "INDEX SCAN"
            else:
                evaluacion = "PARCIAL"

            print(f"{q['id']:<18} | {ratio_str:<20} | {tiempo} ms   | {evaluacion}")

    print(f"\n{'='*110}")

if __name__ == "__main__":
    main()