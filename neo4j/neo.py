from neo4j import GraphDatabase
import pandas as pd
from os import system,name

def clear_screen():
    system('cls' if name == 'nt' else 'clear')

def main():
    global driver
    driver = GraphDatabase.driver("neo4j://localhost:7687", auth=("neo4j", "password_seguro"))
    driver.verify_connectivity()

    while True:

        MuestraMenu()
        opcion = input("Introduzca una opcion: ")

        if opcion == "1":
            clear_screen()
            
            linea = input("Introduzca el número de línea: ")
            ConsultaLinea(linea)

        elif opcion == "2":
            clear_screen()
            ConsultaHubs()

        elif opcion == "3":
            clear_screen()
            ConsultaRenfe()

        elif opcion == "4":
            clear_screen()
            campus = ConsultaCampus(EligeEstudios())

            for c in campus: print(f"{c[0]}, {c[1]}")

        elif opcion == "5":
            clear_screen()
            ResumenUnis()

        elif opcion == "6":
            clear_screen()
            estacion, campus = IntroducirDatos()

            print('')
            if CalculaRuta(estacion, campus) == -1:
                print("No hay estaciones de metro cerca del campus seleccionado.")

        elif opcion == "7":
            clear_screen()

            estudio = EligeEstudios()
            campus = ConsultaCampus(estudio)
            estacion, _ = IntroducirDatos(campus = False)
            
            print('')
            for c in campus: 
                print(f"El {estudio} se puede cursar en el {c[0]} de la {c[1]}.")
                if CalculaRuta(estacion, c[0]) == -1:
                    print(f"No existe ruta de metro hasta el {c[0]}.\n")

        elif opcion == "8":
            clear_screen()
            break

        else:
            clear_screen()
            continue


        input("Pulse enter para continuar:")
        clear_screen()
    #"""

def CargaLineas(file):
    df = pd.read_csv(file)
    driver.execute_query("""
    UNWIND """+f"{list(df['DENOMINACION'])}"+""" as e_nombre
    MERGE (e:Estacion {nombre:e_nombre})
    """)


    for i in range(len(df)):

        nombre = f"'{df.iloc[i]['DENOMINACION']}'"

        renfe = df.iloc[i]["RENFE"]
        if renfe == "[]": 
            renfe = "NULL"
        else:
            driver.execute_query("""
            MATCH (e:Estacion {nombre:"""+nombre+"""})
            SET e.Renfe = """+renfe
            )

        lineas = df.iloc[i]["LINEAS"]
        lineas = lineas[1:-1].split("}, ")

        for i in range(len(lineas)):

            lineas[i] = lineas[i].replace('{', '')
            lineas[i] = lineas[i].replace('}', '')
            lineas[i] = lineas[i].replace("'linea': ", '')
            lineas[i] = lineas[i].replace("'orden': ", '')
            lineas[i] = lineas[i].replace("'", '')
            lineas[i] = lineas[i].replace(',', '')

            l = str(lineas[i].split()[0])
            if l != 'R': l = f"'L{l}'"
            else: l = "'R'"

            o = str(lineas[i].split()[1])


            driver.execute_query("""
            optional match (l:Linea {nombre:"""+l+"""})

            foreach (i in (case when l is null then [1] else [] end) |
                create (l:Linea {nombre:"""+l+"""})
            )"""
            )

            driver.execute_query("""
            MATCH (l:Linea {nombre:"""+l+"""})
            MATCH (e:Estacion {nombre:"""+nombre+"""})
            CREATE (l)-[:TIENE_ESTACION {orden:"""+o+"""}]->(e);
            """)

            driver.execute_query("""
            match (e:Estacion {nombre:"""+nombre+"""})
            match (l:Linea {nombre:"""+l+"""})
            match (l)-[r1:TIENE_ESTACION]->(e)
            optional match (l)-[r2:TIENE_ESTACION {orden:r1.orden + 1}]->(e_next)

            foreach (i in (case when e_next is not null then [1] else [] end) |
                create (e)-[:SIGUIENTE {linea:"""+l+"""}]->(e_next)
            )"""
            )

            driver.execute_query("""
            match (e:Estacion {nombre:"""+nombre+"""})
            match (l:Linea {nombre:"""+l+"""})
            match (l)-[r1:TIENE_ESTACION]->(e)
            optional match (l)-[r2:TIENE_ESTACION {orden:r1.orden - 1}]->(e_prev)

            foreach (i in (case when e_prev is not null then [1] else [] end) |
                    create (e_prev)-[:SIGUIENTE {linea:"""+l+"""}]->(e)
            )"""
            )



    driver.execute_query("""
    match (e1:Estacion {nombre:"CARPETANA"})
    match (e2:Estacion {nombre:"LAGUNA"})

    create (e1)-[:SIGUIENTE {linea:'L6'}]->(e2)

    """)

    driver.execute_query("""
    match (e1:Estacion {nombre:"SAN NICASIO"})
    match (e2:Estacion {nombre:"PUERTA DEL SUR"})

    create (e1)-[:SIGUIENTE {linea:'L12'}]->(e2)

    """)

def CargaUnis(file):
    df = pd.read_csv(file)
    driver.execute_query("""
    UNWIND """+f"{list(df['Campus'])}"+""" as c_nombre
    MERGE (c:Campus {nombre: c_nombre})
    """)


    for i in range(len(df)):

        nombre = f"'{df.iloc[i]['Campus']}'"
        universidad = f"'{df.iloc[i]['Universidad']}'"
        X = df.iloc[i]["X"]
        Y = df.iloc[i]["Y"]

        if df.iloc[i]['Estación_Principal'] != None and str(df.iloc[i]['Estación_Principal']) != 'nan':
            Est1 = f"'{df.iloc[i]['Estación_Principal']}'"
            T1 = df.iloc[i]['Tiempo_Principal']
        else:
            Est1 = "'No'"
            T1 = "'No'"

        if df.iloc[i]['Estación_Alternativa'] != None and str(df.iloc[i]['Estación_Alternativa']) != 'nan':
            Est2 = f"'{df.iloc[i]['Estación_Alternativa']}'"
            T2 = df.iloc[i]['Tiempo_Alternativa']
        else:
            Est2 = "'No'"
            T2 = "'No'"


        driver.execute_query("""
        MATCH (c:Campus {nombre:"""+nombre+"""})
        SET c.Universidad = """+universidad+""", c.X = """+str(X)+""", c.Y = """+str(Y)
        )

        if Est1 != "NO":

            driver.execute_query("""
            MATCH (e:Estacion {nombre:"""+Est1+"""})
            MATCH (c:Campus {nombre:"""+nombre+"""})

            CREATE (c)-[r:CERCANA]->(e)
            SET r.minutos = """+str(T1)+"""
            SET r.rol = 'Principal'
            """)

        if Est2 != "NO":

            driver.execute_query("""
            MATCH (e:Estacion {nombre:"""+Est2+"""})
            MATCH (c:Campus {nombre:"""+nombre+"""})

            CREATE (c)-[r:CERCANA]->(e)
            SET r.minutos = """+str(T2)+"""
            SET r.rol = 'Alternativa'
            """)

def CargaEstudios(file):
    df = pd.read_csv(file)
    driver.execute_query("""
    UNWIND """+f"{list(df['Estudios'])}"+""" as e_nombre
    MERGE (e:Estudio {nombre: e_nombre})
    """)


    for i in range(len(df)):

        nombre = f"'{df.iloc[i]['Estudios']}'"
        campus = f"'{df.iloc[i]['Campus']}'"
        creditos = f"'{df.iloc[i]['Créditos']}'"
        coordinador = f"'{df.iloc[i]['Coordinador']}'"

        driver.execute_query("""
        MATCH (e:Estudio {nombre:"""+nombre+"""})
        MATCH (c:Campus {nombre:"""+campus+"""})

        SET e.creditos = """+creditos+"""
        SET e.coordinador = """+coordinador+"""
        CREATE (c)-[:OFRECE]->(e);
        """)

def MuestraMenu():

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

    records, summary, keys = driver.execute_query("""
    MATCH (l:Linea {nombre:"""+linea+"""})-[r:TIENE_ESTACION]->(e:Estacion)

    RETURN e.nombre AS estacion, r.orden as orden, e.Renfe as renfe
    ORDER BY orden
    """)

    for record in records:
        record = record.data()

        espacio1 = '  ' if record['orden'] < 10 else ' '
        print(f"{record['orden']}.{espacio1}{record['estacion']}", end = '')

        espacio2 = (30-len(record['estacion']))*' '
        print(f"{espacio2}", end='')

        metro = LineasDe(record['estacion'])
        if len(metro) != 0:
            for l in sorted(list(metro)): 
                if f"'{l}'" != linea:
                    print(l, end = ' ')
        if record['renfe'] != None:
            for l in record['renfe']:
                print(l, end = ' ')

        print('')

def ConsultaHubs():
    records, _, _ = driver.execute_query("""
    MATCH (c:Campus)-[:CERCANA]->(e:Estacion)
    WHERE COUNT { (c)-[:CERCANA]->(e) } > 1
    RETURN e.nombre AS estacion
    """)

    if len(records) == 0:
        print("No hay hubs universitarios (i.e estaciones conectadas a más de un campus)")

    else:
        for record in records:
            record = record.data()
            print(f"{record['estacion']}")

def ConsultaRenfe():
    records, _, _ = driver.execute_query("""
    MATCH (c)-[:CERCANA]->(e:Estacion)
    WHERE e.Renfe IS NOT NULL
    RETURN e.nombre as nombre, e.Renfe as renfe, c.nombre as campus, c.Universidad as universidad
    """)

    for record in records:
        record = record.data()

        estacion = record['nombre']
        campus = record['campus']
        universidad = record['universidad']
        espacio1 = (40-len(estacion))*' '
        espacio2 = (40-(len(campus) + 2 + len(universidad)))*' '

        if len(record['renfe']) == 1:
            print(f"{estacion+espacio1}cerca de {campus}, {universidad+espacio2}correspondencia con línea:", end = '  \t')
            print(record['renfe'][0])

        elif len(record['renfe']) == 2:
            print(f"{estacion+espacio1}cerca de {campus}, {universidad+espacio2}correspondencia con líneas:", end = ' \t')
            print(f"{record['renfe'][0]} y {record['renfe'][1]}")

        else:
            print(f"{estacion+espacio1}cerca de {campus}, {universidad+espacio2}correspondencia con líneas:", end = ' \t')
            for linea in record['renfe'][:-2]:
                print(linea, end = ", ")
            print(f"{record['renfe'][-2]} y {record['renfe'][-1]}")

def EligeEstudios():

    records, _, _ = driver.execute_query("""
    MATCH (e:Estudio)
    return e.nombre as estudio
    """)

    estudios = list()
    idx = 1
    for record in records:
        record = record.data()
        espacio = '  ' if idx < 10 else ' '
        print(f"{idx}.{espacio}{record['estudio']}")
        estudios.append(record['estudio'])
        idx += 1

    opcion = ''
    while not opcion.isnumeric() or int(opcion) not in list(range(1, idx)):
        opcion = input("Elija un grado: ")

    clear_screen()
    return estudios[int(opcion) - 1]

def ConsultaCampus(grado):
    grado = f"'{grado}'"
    records, _, _ = driver.execute_query("""
    MATCH (e:Estudio {nombre:"""+grado+"""})
    MATCH (c:Campus)-[:OFRECE]->(e)

    return c.nombre as campus, c.Universidad as universidad
    """)

    campus = list()
    for record in records:
        record = record.data()

        campus.append((record['campus'], record['universidad']))

    return campus

def ResumenUnis():
    records, _, _ = driver.execute_query("""
    MATCH (u)-[:OFRECE]->(e)
    RETURN u.Universidad as universidad, e.nombre as estudio
    """)

    universidades = dict()
    for record in records:
        record = record.data()

        if record['universidad'] not in universidades:
            universidades[record['universidad']] = {"grados":0, "masters":0}
        
        if "GRADO EN" in record['estudio']:
            universidades[record['universidad']]["grados"] += 1

        else:
             universidades[record['universidad']]["masters"] += 1

    for universidad in universidades:
        print(f"{universidad}:", end = '\n\t')
        print(f"Nº de grados:  {universidades[universidad]['grados']}", end = '\n\t')
        print(f"Nº de másters: {universidades[universidad]['masters']}", end = '\n\n')

def QuitaTildes(palabra):
    palabra = palabra.replace('á', 'a')
    palabra = palabra.replace('é', 'e')
    palabra = palabra.replace('í', 'i')
    palabra = palabra.replace('ó', 'o')
    palabra = palabra.replace('ú', 'u')

    return palabra

def LineasDe(estacion, renfe = False):
    estacion = f"'{estacion}'"

    if not renfe:
        records, _, _ = driver.execute_query("""
        MATCH (l)-[r:TIENE_ESTACION]-(e)
        WHERE e.nombre = """+estacion+"""
        RETURN l.nombre as linea
        """)

        lineas = set()
        for record in records:
            record = record.data()

            lineas.add(record['linea'])

    else:
        records, _, _ = driver.execute_query("""
        MATCH (e:Estacion)
        WHERE e.nombre = """+estacion+"""
        RETURN e.Renfe as renfe
        """)

        lineas = records[0].data()['renfe']

    return lineas

def IntroducirDatos(estacion = True, campus = True):
    if estacion:
        valido = False
        while not valido:
            estacion = input("Introduzca la estación de origen: ")
            estacion = QuitaTildes(estacion).upper()
            estacion = f"'{estacion}'"

            records, summary, keys = driver.execute_query("""
            OPTIONAL MATCH (e:Estacion {nombre:"""+estacion+"""})

            RETURN e as estacion
            """)

            if records[0].data()['estacion'] != None:
                valido = True

    if campus:
        valido = False
        while not valido:
            campus = input("Introduzca el campus de destino: ")
            campus = QuitaTildes(campus).upper()
            campus = f"'{campus}'"

            records, summary, keys = driver.execute_query("""
            OPTIONAL MATCH (c:Campus {nombre:"""+campus+"""})

            RETURN c as campus
            """)

            if records[0].data()['campus'] != None:
                valido = True

    return estacion, campus

def CalculaRuta(estacion, campus):
    if estacion[0] != "'": estacion = f"'{estacion}'"
    if campus[0] != "'": campus = f"'{campus}'"
    
    records, _, _ = driver.execute_query("""
    MATCH (c)-[:CERCANA]-(e)
    WHERE c.nombre = """+campus+"""
    RETURN e.nombre as estacion
    """)

    destino = [record.data()['estacion'] for record in records]
    
    if len(destino) == 0:
        return -1

    else:
    
        if len(destino) == 1:

            records, summary, keys = driver.execute_query("""
            MATCH p = SHORTEST 1 (e1)-[:SIGUIENTE]-+(e2)
            WHERE e1.nombre = """+estacion+""" AND e2.nombre = '"""+destino[0]+"""'
            RETURN [n in nodes(p) | n.nombre] AS camino
            """)

        if len(destino) == 2:

            records, summary, keys = driver.execute_query("""
            MATCH p = SHORTEST 1 (e1)-[:SIGUIENTE]-+(e2)
            WHERE e1.nombre = """+estacion+""" AND (e2.nombre = '"""+destino[0]+"""' OR e2.nombre = '"""+destino[1]+"""')
            RETURN [n in nodes(p) | n.nombre] AS camino
            """)

        record = records[0].data()
        
        print(f"RUTA {record['camino'][0]}-{record['camino'][-1]}, {len(record['camino'])} estaciones\n")

        transbordos = 0
        for i in range(len(record['camino'])):

            estacion_prev = record['camino'][i - 1] if i != 0 else None
            estacion = record['camino'][i]
            estacion_next = record['camino'][i + 1] if i < len(record['camino']) - 1 else None

            espacio = (30-len(estacion))*' '
            print(f"{estacion}{espacio}", end = '\t')

            if estacion_prev == None: lineas = LineasDe(estacion).intersection(LineasDe(estacion_next))
            elif estacion_next == None: lineas = LineasDe(estacion).intersection(LineasDe(estacion_prev))
            else: lineas = LineasDe(estacion).intersection(LineasDe(estacion_prev).union(LineasDe(estacion_next)))
            
            for linea in sorted(list(lineas)): print(linea, end = ' ')

            if LineasDe(estacion, renfe = True) != None:

                print("C", end = ' ')

            if len(lineas) != 1: 
                print("TRANSBORDO")
                transbordos += 1
            else: print('')

        print(f"Ruta con {transbordos} transbordos\n")

if __name__ == "__main__":
    main()