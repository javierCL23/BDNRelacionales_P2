from neo4j import GraphDatabase
import pandas as pd
import os


def main():
    try:
        global driver                                                                               # Acceso a la base de datos.
        driver = GraphDatabase.driver("neo4j://localhost:7687", auth=("neo4j", "password_seguro"))
        driver.verify_connectivity()

    except Exception as e:
        print(f"Error conectando a Neo4j: {e}")
        return


    while True:                                                                                 # Interacción con la aplicación.

        MuestraMenu()
        opcion = input("Introduzca una opcion: ")

        if opcion == "1":                                                                       # 1. Consultar estaciones de una línea.
            clear_screen()
            
            linea = input("Introduzca el número de línea: ")
            ConsultaLinea(linea)

        elif opcion == "2":                                                                     # 2. Consultar hubs universitarios.
            clear_screen()
            ConsultaHubs()

        elif opcion == "3":                                                                     # 3. Consultar estaciones universitarias con cercanías.
            clear_screen()
            ConsultaRenfe()

        elif opcion == "4":                                                                     # 4. Consultar campus por estudio.
            clear_screen()
            rama = EligeRama()

            clear_screen()
            campus = ConsultaCampus(EligeEstudios(rama))

            for c in campus: print(f"{c[0]}, {c[1]}")       # Impresión Campus, Universidad por pantalla

        elif opcion == "5":                                                                     # 5. Resumen de universidades.
            clear_screen()
            ResumenUnis()

        elif opcion == "6":                                                                     # 6. Consultar rutas estación-campus.
            clear_screen()
            estacion, campus = IntroducirDatos()

            print('')
            if CalculaRuta(estacion, campus) == -1:         # Mensaje si el campus no tiene metro (e.g Aranjuez)
                print("No hay estaciones de metro cerca del campus seleccionado.")

        elif opcion == "7":                                                                     # 7. Consultar rutas estación-grado.
            clear_screen()

            rama = EligeRama()
            estudio = EligeEstudios(rama)
            campus = ConsultaCampus(estudio)
            estacion, _ = IntroducirDatos(campus = False)
            
            print('')
            for c in campus: 
                print(f"El {estudio} se puede cursar en el {c[0]} de la {c[1]}.")
                if CalculaRuta(estacion, c[0]) == -1:           # Mensaje si el campus no tiene metro (e.g Aranjuez)
                    print(f"No existe ruta de metro hasta el {c[0]}.\n")

        elif opcion == "8":                                                                     # 8. Salir.
            clear_screen()
            break

        else:                                                                                   # Errores del usuario.
            clear_screen()
            continue


        input("Pulse enter para continuar:")
        clear_screen()


def MuestraMenu():                                                                              # Interfaz del menú principal.  

    print("1. Consultar estaciones de una línea.")
    print("2. Consultar hubs universitarios.")
    print("3. Consultar estaciones universitarias con cercanías.")
    print("4. Consultar campus por estudio.")
    print("5. Resumen de universidades.")
    print("6. Consultar rutas estación-campus.")
    print("7. Consultar rutas estación-grado.")
    print("8. Salir.")


def ConsultaLinea(linea):

    if linea == "R": linea = "'R'"
    else: linea = f"'L{linea}'"

    records, _, _ = driver.execute_query("""
    MATCH (l:Linea {nombre:"""+linea+"""})-[r:TIENE_ESTACION]->(e:Estacion)

    RETURN e.nombre AS estacion, r.orden AS orden, e.Renfe AS renfe
    ORDER BY orden
    """)

    for record in records:                                                                      # Por cada estación consultada
        record = record.data()

        espacio1 = '  ' if record['orden'] < 10 else ' '
        print(f"{record['orden']}.{espacio1}{record['estacion']}", end = '')                    # Nombre de la estación.

        espacio2 = (30-len(record['estacion']))*' '
        print(f"{espacio2}", end='')

        metro = LineasDe(record['estacion'])
        if len(metro) != 0:
            for l in sorted(list(metro)): 
                if f"'{l}'" != linea:
                    print(l, end = ' ')                                                         # Correspondencia metro.
        if record['renfe'] != None:
            for l in record['renfe']:
                print(l, end = ' ')                                                             # Correspondencia renfe.

        print('')


def ConsultaHubs():

    records, _, _ = driver.execute_query("""
    MATCH (c:Campus)-[:CERCANA]->(e:Estacion)
    WHERE COUNT { (c)-[:CERCANA]->(e) } > 1
    RETURN e.nombre AS estacion
    """)

    if len(records) == 0:
        print("No hay hubs universitarios (i.e estaciones conectadas a más de un campus)")      # Mensaje si no hay hubs.

    else:
        for record in records:
            record = record.data()
            print(f"{record['estacion']}")                                                      # Estaciones que son hub.

def ConsultaRenfe():

    records, summary, keys = driver.execute_query("""
    MATCH (c)-[:CERCANA]->(e:Estacion)
    WHERE e.Renfe IS NOT NULL
    RETURN e.nombre AS nombre, e.Renfe AS renfe, c.nombre AS campus, c.Universidad AS universidad
    """)

    for record in records:                                                                      # Por cada estación cerca de un campus.
        record = record.data()

        estacion = record['nombre']
        campus = record['campus']
        universidad = record['universidad']
        espacio1 = (40-len(estacion))*' '
        espacio2 = (40-(len(campus) + 2 + len(universidad)))*' '
                                                                                                # Casos de correspondencias, mismos mensajes con distintos formatos.
        if len(record['renfe']) == 1:
            print(f"{estacion+espacio1}cerca de {campus}, {universidad+espacio2}correspondencia con línea:", end = '  \t') # Correspondencia con 1 línea.
            print(record['renfe'][0])

        elif len(record['renfe']) == 2:
            print(f"{estacion+espacio1}cerca de {campus}, {universidad+espacio2}correspondencia con líneas:", end = ' \t') # Correspondencia con 2 líneas.
            print(f"{record['renfe'][0]} y {record['renfe'][1]}")

        else:
            print(f"{estacion+espacio1}cerca de {campus}, {universidad+espacio2}correspondencia con líneas:", end = ' \t') # Correspondencia con >2 líneas.
            for linea in record['renfe'][:-2]:
                print(linea, end = ", ")
            print(f"{record['renfe'][-2]} y {record['renfe'][-1]}")

def EligeRama():

    records, _, _ = driver.execute_query("""
    MATCH (e:Estudio)
    RETURN DISTINCT properties(e).rama AS rama
    """)

    ramas = list()
    idx = 1

    for record in records:                                                                      # Por cada rama (Ciencias, Artes...)
        record = record.data()

        print(f"{idx}. {record['rama']}")                                                       # Índice y rama
        ramas.append(record['rama'])
        idx += 1

    opcion = ''
    while not opcion.isnumeric() or int(opcion) not in list(range(1, idx)):                     # Se pide índice hasta uno satisfactorio.
        opcion = input("Elija una rama: ")

    return ramas[int(opcion) - 1]                                                               # Devuelve rama.

def EligeEstudios(rama):

    records, _, _ = driver.execute_query("""
    MATCH (e:Estudio {rama:$rama})
    RETURN e.nombre AS estudio
    """, rama = rama)

    estudios = list()
    idx = 1
    for record in records:                                                                      # Por cada estudio (grado en infórmatica, etc)
        record = record.data()

        espacio = '  ' if idx < 10 else ' '
        print(f"{idx}.{espacio}{record['estudio']}")                                            # Índice y estudio.
        estudios.append(record['estudio'])
        idx += 1
    

    opcion = ''
    while not opcion.isnumeric() or int(opcion) not in list(range(1, idx)):                     # Se pide índice hasta uno satisfactorio.
        opcion = input("Elija un grado: ")

    clear_screen()
    return estudios[int(opcion) - 1]                                                            # Devuelve estudio.


def ConsultaCampus(estudio):

    estudio = f"'{estudio}'"
    records, _, _ = driver.execute_query("""
    MATCH (e:Estudio {nombre:"""+estudio+"""})
    MATCH (c:Campus)-[:OFRECE]->(e)

    return c.nombre AS campus, c.Universidad AS universidad
    """)

    campus = list()
    for record in records:                                                                      # Por cada campus.
        record = record.data()

        campus.append((record['campus'], record['universidad']))                                # Recoge par (campus, universidad)

    return campus                                                                               # Devuelve el par.

def ResumenUnis():

    records, _, _ = driver.execute_query("""
    MATCH (u)-[:OFRECE]->(e)
    RETURN u.Universidad AS universidad, e.nombre AS estudio
    """)

    universidades = dict()
    for record in records:                                                                      # Por cada estudio.
        record = record.data()

        if record['universidad'] not in universidades:                                          # Recoge universidad que lo oferta.
            universidades[record['universidad']] = {"grados":0, "masters":0}
        
        if "GRADO EN" in record['estudio']:                                                     # Conteo de grados.
            universidades[record['universidad']]["grados"] += 1

        elif "MASTER EN" in record['estudio']:                                                  # Conteo de másters.
             universidades[record['universidad']]["masters"] += 1

    for universidad in universidades:                                                           # Por cada universidad.
        print(f"{universidad}:", end = '\n\t')                                                  # Universidad:
        print(f"Nº de grados:  {universidades[universidad]['grados']}", end = '\n\t')           #       Nº de grados:  x
    print(f"Nº de másters: {universidades[universidad]['masters']}", end = '\n\n')              #       Nº de másters: y       

def LineasDe(estacion, renfe = False):

    estacion = f"'{estacion}'"

    if not renfe:                                                                               # Por defecto devuelve correspondencia con metro de estación.
        records, _, _ = driver.execute_query("""
        MATCH (l)-[r:TIENE_ESTACION]-(e)
        WHERE e.nombre = """+estacion+"""
        RETURN l.nombre AS linea
        """)

        lineas = set()
        for record in records:                                                                  # Por cada línea (de metro) la recoge.
            record = record.data()

            lineas.add(record['linea'])

    else:                                                                                       # Si renfe = True devuelve correspondencia con cercanías de estación.
        records, _, _ = driver.execute_query("""
        MATCH (e:Estacion)
        WHERE e.nombre = """+estacion+"""
        RETURN e.Renfe as renfe
        """)

        lineas = records[0].data()['renfe']                                                     # Recoge líneas de renfe.

    return lineas                                                                               # Devuelve las líneas recogidas.
    


                                                                            

def EligeUni():
        records, _, _ = driver.execute_query("""
        MATCH (c:Campus)
        RETURN DISTINCT properties(c).Universidad AS universidad
        """)

        universidades = list()
        idx = 1

        for record in records:                                                                  # Por cada universidad (UCM, UPM...)
            record = record.data()

            print(f"{idx}. {record['universidad']}")                                            # Índice y universidad.
            universidades.append(record['universidad'])
            idx += 1

        opcion = ''
        while not opcion.isnumeric() or int(opcion) not in list(range(1, idx)):                 # Se pide índice hasta uno satisfactorio. 
            opcion = input("Elija una universidad: ")

        return universidades[int(opcion) - 1]                                                   # Devuelve universidad.

def IntroducirDatos(estacion = True, campus = True):

    if estacion:                                                                                # Si se pide estación.
        valido = False
        while not valido:
            estacion = input("Introduzca la estación de origen: ")                              # Pide entrada de usuario.
            estacion = QuitaTildes(estacion).upper()                                            # Sin tener en cuenta tildes o mayúsculas.
            estacion = f"'{estacion}'"

            records, summary, keys = driver.execute_query("""
            OPTIONAL MATCH (e:Estacion {nombre:"""+estacion+"""})

            RETURN e as estacion
            """)

            if records[0].data()['estacion'] != None:                                           # Si no existe, se pide de nuevo.
                valido = True
            
            clear_screen()

    if campus:
        universidad = EligeUni()
        records, _, _ = driver.execute_query("""
        MATCH (c:Campus {Universidad:$universidad})
        RETURN c.nombre AS campus
        """, universidad = universidad)

        campus = list()
        idx = 1

        for record in records:                                                                  # Por cada campus (Campus de Leganés, Campus de Fuenlabrada...)
            record = record.data()

            print(f"{idx}. {record['campus']}")                                                 # Índice y campus.
            campus.append(record['campus'])
            idx += 1

        opcion = ''
        while not opcion.isnumeric() or int(opcion) not in list(range(1, idx)):                 # Se pide índice hasta uno satisfactorio. 
            opcion = input("Elija un campus: ")

        campus = campus[int(opcion) - 1]                                                        # Devuelve campus.

    return estacion, campus


def CalculaRuta(estacion, campus):

    if estacion[0] != "'": estacion = f"'{estacion}'"
    if campus[0] != "'": campus = f"'{campus}'"
    
    records, _, _ = driver.execute_query("""
    MATCH (c)-[:CERCANA]-(e)
    WHERE c.nombre = """+campus+"""
    RETURN e.nombre AS estacion
    """)

    destino = [record.data()['estacion'] for record in records]                                 # destino = estaciones susceptibles de ser el destino.
    
    if len(destino) == 0:                                                                       # Si no hay, no se puede calcular una ruta.
        return -1

    else:
    
        if len(destino) == 1:                                                                   # Si hay una, esa será el destino.

            records, summary, keys = driver.execute_query("""
            MATCH p = SHORTEST 1 (e1)-[:CONEXION]-+(e2)
            WHERE e1.nombre = """+estacion+""" AND e2.nombre = '"""+destino[0]+"""'
            RETURN [n in nodes(p) | n.nombre] AS camino
            """)

        if len(destino) == 2:                                                                   # Si hay dos, ambas son tenidas en cuenta.

            records, summary, keys = driver.execute_query("""
            MATCH p = SHORTEST 1 (e1)-[:CONEXION]-+(e2)
            WHERE e1.nombre = """+estacion+""" AND (e2.nombre = '"""+destino[0]+"""' OR e2.nombre = '"""+destino[1]+"""')
            RETURN [n in nodes(p) | n.nombre] AS camino
            """)

        record = records[0].data()
        
        print(f"RUTA {record['camino'][0]}-{record['camino'][-1]}, {len(record['camino'])} estaciones\n")   # "Ruta ORIGEN-DESTINO (n estaciones)"

        transbordos = 0
        for i in range(len(record['camino'])):                                                  # Por cada estación en el camino.

            estacion_prev = record['camino'][i - 1] if i != 0 else None                         # Previa.
            estacion = record['camino'][i]                                                      # Actual.
            estacion_next = record['camino'][i + 1] if i < len(record['camino']) - 1 else None  # Próxima.

            espacio = (30-len(estacion))*' '
            print(f"{estacion}{espacio}", end = '\t')                                           # Nombre de estación actual.

            if estacion_prev == None: lineas = LineasDe(estacion).intersection(LineasDe(estacion_next))             # Correspondencia metro para ORIGEN.
            elif estacion_next == None: lineas = LineasDe(estacion).intersection(LineasDe(estacion_prev))           # Correspondencia metro para intermedias.
            else: lineas = LineasDe(estacion).intersection(LineasDe(estacion_prev).union(LineasDe(estacion_next)))  # Correspondencia metro para DESTINO
                                                                                                                    # Tres opciones para tres formatos que muestren la línea actual.
                                                                                                                    # Si apareciese más de una línea indica transbordo.

            for linea in sorted(list(lineas)): print(linea, end = ' ')                                              # Se imprimen las líneas.                     

            if LineasDe(estacion, renfe = True) != None:                                                            # Si hay correspondencia con cercanías, se marca con C

                print("C", end = ' ')

            if len(lineas) != 1:                                                                                    # Si se detecta diferencias entre líneas anteriores y posteriores
                print("TRANSBORDO")                                                                                 # se indica transbordo.
                transbordos += 1
            else: print('')

        print(f"Ruta con {transbordos} transbordos\n")                                                              # Notificación de número de transbordos en la ruta.


def QuitaTildes(palabra):                                                                                           # Herramienta auxiliar para eliminar tildes de una palabra.

    palabra = palabra.replace('á', 'a')
    palabra = palabra.replace('é', 'e')
    palabra = palabra.replace('í', 'i')
    palabra = palabra.replace('ó', 'o')
    palabra = palabra.replace('ú', 'u')

    return palabra


def clear_screen():                                                                                                 # Herramienta auxiliar para limpiar la pantalla.
    os.system('cls' if os.name == 'nt' else 'clear')


if __name__ == "__main__":
    main()
