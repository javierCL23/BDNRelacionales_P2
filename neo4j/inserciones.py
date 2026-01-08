import pandas as pd
from neo4j import GraphDatabase
import time
import os

def get_driver(URI,AUTH):
    try:
        driver = GraphDatabase.driver(URI, auth=AUTH)
        driver.verify_connectivity()
        print("Conexión exitosa a Neo4j")
        return driver
    except Exception as e:
        print(f"Error conectando a Neo4j: {e}")
        return None

def limpiar_base_datos(driver):
    print("Limpiando base de datos...")
    with driver.session() as session:
        session.run("MATCH (n) DETACH DELETE n")
    print("Base de datos vacía.")

def cargar_lineas(driver, df):
    print("Cargando Líneas y Estaciones...")
    with driver.session() as session:
        # 1. Crear nodos Estacion
        session.run("""
        UNWIND $nombres as e_nombre
        MERGE (e:Estacion {nombre:e_nombre})
        """, nombres=list(df['DENOMINACION']))

        # 2. Procesar detalles (Renfe y conexiones)
        for i, row in df.iterrows():
            nombre = row['DENOMINACION']
            
            # Cargar propiedad Renfe
            renfe = row["RENFE"]
            if renfe != "[]":
                session.run(f"MATCH (e:Estacion {{nombre: '{nombre}'}}) SET e.Renfe = {renfe}")

            # Procesar el string de 'LINEAS' (Lógica adaptada de tu neo.py)
            lineas_raw = row["LINEAS"][1:-1].split("}, ")
            
            for item in lineas_raw:
                # Limpieza de caracteres del string original
                clean_item = item.replace('{', '').replace('}', '').replace("'linea': ", '').replace("'orden': ", '').replace("'", '').replace(',', '')
                parts = clean_item.split()
                
                l_code = parts[0]
                orden = parts[1]

                nombre_linea = f"L{l_code}" if l_code != 'R' else 'R'

                # Crear Línea y relación con Estación
                session.run(f"""
                MERGE (l:Linea {{nombre: '{nombre_linea}'}})
                WITH l
                MATCH (e:Estacion {{nombre: '{nombre}'}})
                MERGE (l)-[:TIENE_ESTACION {{orden: {orden}}}]->(e)
                """)

        # 3. Crear relaciones CONEXION
        print("Creando relaciones de trayecto (CONEXION)...")
        session.run("""
            MATCH (l:Linea)-[r:TIENE_ESTACION]->(e:Estacion)
            WITH l, e ORDER BY r.orden
            WITH l, collect(e) as estaciones
            FOREACH (i in range(0, size(estaciones)-2) |
                FOREACH (e1 in [estaciones[i]] |
                    FOREACH (e2 in [estaciones[i+1]] |
                        MERGE (e1)-[:CONEXION {linea:l.nombre}]-(e2)
                        
            )))
        """)

        # 4. Conexiones manuales
        session.run("MATCH (a:Estacion {nombre:'CARPETANA'}), (b:Estacion {nombre:'LAGUNA'}) MERGE (a)-[:CONEXION {linea:'L6'}]-(b)")
        session.run("MATCH (a:Estacion {nombre:'SAN NICASIO'}), (b:Estacion {nombre:'PUERTA DEL SUR'}) MERGE (a)-[:CONEXION {linea:'L12'}]-(b)")

def cargar_campus(driver, df):
    print("Cargando Campus...")
    with driver.session() as session:
        session.run("UNWIND $nombres as c_nombre MERGE (c:Campus {nombre: c_nombre})", nombres=list(df['Campus']))

        for i, row in df.iterrows():
            # Actualizar propiedades
            session.run("""
                MATCH (c:Campus {nombre: $nombre})
                SET c.Universidad = $uni, c.X = $x, c.Y = $y
            """, nombre=row['Campus'], uni=row['Universidad'], x=row['X'], y=row['Y'])

            # Relaciones Cercana (Principal)
            if str(row['Estación_Principal']) != 'nan':
                session.run("""
                    MATCH (c:Campus {nombre: $c}), (e:Estacion {nombre: $e})
                    MERGE (c)-[:CERCANA {minutos: $t, rol: 'Principal'}]->(e)
                """, c=row['Campus'], e=row['Estación_Principal'], t=row['Tiempo_Principal'])

            # Relaciones Cercana (Alternativa)
            if str(row['Estación_Alternativa']) != 'nan':
                session.run("""
                    MATCH (c:Campus {nombre: $c}), (e:Estacion {nombre: $e})
                    MERGE (c)-[:CERCANA {minutos: $t, rol: 'Alternativa'}]->(e)
                """, c=row['Campus'], e=row['Estación_Alternativa'], t=row['Tiempo_Alternativa'])

def cargar_estudios(driver, df):
    print("Cargando Estudios...")
    with driver.session() as session:
        # Crear nodo estudio (Nombre común)
        session.run("UNWIND $nombres as e_nombre MERGE (e:Estudio {nombre: e_nombre})", nombres=list(df['Estudios']))

        for i, row in df.iterrows():
            # Información relativa a cada campus en la arista RELACIÓN [:OFRECE]
            session.run("""
                MATCH (e:Estudio {nombre: $est})
                MATCH (c:Campus {nombre: $camp})
                MERGE (c)-[r:OFRECE]->(e)
                SET r.creditos = $cred, 
                    r.coordinador = $coord, 
                    r.rama = $rama
            """, est=row['Estudios'], camp=row['Campus'], 
                 cred=row['Créditos'], coord=row['Coordinador'], rama=row['Rama'])
def main():

    # Configuración de conexión
    URI = os.environ.get("NEO_URL","neo4j://localhost:7687")
    AUTH = ("neo4j", "password_seguro")

    print(URI)

    ready = False
    while not ready:
        driver = get_driver(URI,AUTH)
        if driver:
            ready = True
        else:
            time.sleep(3)

    # Cargar CSVs
    try:
        print("Leyendo archivos CSV...")
        campus_df = pd.read_csv("campus.csv") 
        estudios_df = pd.read_csv("estudios.csv") 
        lineas_df = pd.read_csv("estaciones.csv")
    except FileNotFoundError as e:
        print(f"Error: No se encuentra el archivo: {e}")
        driver.close()
        return

    # Ejecutar proceso
    start_time = time.time()
    
    limpiar_base_datos(driver)
    cargar_lineas(driver, lineas_df)
    cargar_campus(driver, campus_df)
    cargar_estudios(driver, estudios_df)

    driver.close()
    print(f"\nCarga completada en {round(time.time() - start_time, 2)} segundos.")

if __name__ == "__main__":
    main()
