from neo4j import GraphDatabase
import pandas as pd


def CargaUnis(df):

    driver.execute_query("""
    UNWIND """+f"{list(df['Campus'])}"+""" as c_nombre
    MERGE (c:Campus {nombre: c_nombre})
    """)


    for i in range(len(df)):

        nombre = f"'{df.iloc[i]['Campus'].upper()}'"
        universidad = f"'{df.iloc[i]['Universidad'].upper()}'"
        X = df.iloc[i]["X"]
        Y = df.iloc[i]["Y"]

        if df.iloc[i]['Estación_Principal'] != None and str(df.iloc[i]['Estación_Principal']) != 'nan':
            Est1 = f"'{df.iloc[i]['Estación_Principal'].upper()}'"
            T1 = df.iloc[i]['Tiempo_Principal']
        else:
            Est1 = "'No'"
            T1 = "'No'"

        if df.iloc[i]['Estación_Alternativa'] != None and str(df.iloc[i]['Estación_Alternativa']) != 'nan':
            Est2 = f"'{df.iloc[i]['Estación_Alternativa'].upper()}'"
            T2 = df.iloc[i]['Tiempo_Alternativa']
        else:
            Est2 = "'No'"
            T2 = "'No'"


        driver.execute_query("""
        MATCH (c:Campus {nombre:"""+nombre+"""})
        SET c.Universidad = """+universidad+""", c.X = """+str(X)+""", c.Y = """+str(Y)+""",
        c.Estación_Principal = """+Est1+""", c.Tiempo_Principal = """+str(T1)+""", 
        c.Estación_Alternativa = """+Est2+""", c.Tiempo_Alternativa = """+str(T2)
        )

        if Est1 != "NO":

            driver.execute_query("""
            MATCH (e:Estación {nombre:"""+Est1+"""})
            MATCH (c:Campus {nombre:"""+nombre+"""})

            CREATE (c)-[r:CERCANA]->(e)
            SET r.minutos = """+T1+"""
            SET r.rol = Principal
            """)

        if Est2 != "NO":

            driver.execute_query("""
            MATCH (e:Estación {nombre:"""+Est2+"""})
            MATCH (c:Campus {nombre:"""+nombre+"""})

            CREATE (c)-[r:CERCANA]->(e)
            SET r.minutos = """+T2+"""
            SET r.rol = Alternativa
            """)

def CargaEstudios(df):

    driver.execute_query("""
    UNWIND """+f"{list(df['Estudios'])}"+""" as e_nombre
    MERGE (e:Estudio {nombre: e_nombre})
    """)


    for i in range(len(df)):

        nombre = f"'{df.iloc[i]['Estudios'].upper()}'"
        campus = f"'{df.iloc[i]['Campus'].upper()}'"

        driver.execute_query("""
        MATCH (e:Estudio {nombre:"""+nombre+"""})
        MATCH (c:Campus {nombre:"""+campus+"""})
        CREATE (c)-[:OFRECE]->(e);
        """)

def CargaLineas(df):

    driver.execute_query("""
    UNWIND """+f"{list(df['DENOMINACION'])}"+""" as e_nombre
    MERGE (e:Estación {nombre:e_nombre})
    """)


    for i in range(len(df)):

        nombre = f"'{df.iloc[i]['DENOMINACION']}'"
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
            MATCH (e:Estación {nombre:"""+nombre+"""})
            CREATE (l)-[:TIENE_ESTACION {orden:"""+o+"""}]->(e);
            """)

            driver.execute_query("""
            match (e:Estación {nombre:"""+nombre+"""})
            match (l:Linea {nombre:"""+l+"""})
            match (l)-[r1:TIENE_ESTACION]->(e)
            optional match (l)-[r2:TIENE_ESTACION {orden:r1.orden + 1}]->(e_next)

            foreach (i in (case when e_next is not null then [1] else [] end) |
                create (e)-[:SIGUIENTE {linea:"""+l+"""}]->(e_next)
            )"""
            )

            driver.execute_query("""
            match (e:Estación {nombre:"""+nombre+"""})
            match (l:Linea {nombre:"""+l+"""})
            match (l)-[r1:TIENE_ESTACION]->(e)
            optional match (l)-[r2:TIENE_ESTACION {orden:r1.orden - 1}]->(e_prev)

            foreach (i in (case when e_prev is not null then [1] else [] end) |
                    create (e_prev)-[:SIGUIENTE {linea:"""+l+"""}]->(e)
            )"""
            )



    driver.execute_query("""
    match (e1:Estación {nombre:"CARPETANA"})
    match (e2:Estación {nombre:"LAGUNA"})

    create (e1)-[:SIGUIENTE {linea:'L6'}]->(e2)

    """)

    driver.execute_query("""
    match (e1:Estación {nombre:"SAN NICASIO"})
    match (e2:Estación {nombre:"PUERTA DEL SUR"})

    create (e1)-[:SIGUIENTE {linea:'L12'}]->(e2)

    """)






driver = GraphDatabase.driver("neo4j://localhost:7687", auth=("neo4j", "123456789"))
driver.verify_connectivity()

campus_df = pd.read_csv("campus.csv")
estudios_df = pd.read_csv("estudios.csv")
lineas_df = pd.read_csv("estaciones.csv")

CargaLineas(lineas_df)
CargaUnis(campus_df)
CargaEstudios(estudios_df)

