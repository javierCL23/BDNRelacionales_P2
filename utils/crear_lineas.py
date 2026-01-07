import pandas as pd
import numpy as np

def limpiar_y_preparar_dataset():
    # 1. Lectura de datasets
    try:
        df = pd.read_csv("M4_Estaciones.csv")
        dfCercanias = pd.read_csv("M5_Estaciones.csv")
    except FileNotFoundError:
        print("Error: No se encuentran los archivos CSV originales.")
        return

    # 2. Limpieza inicial de columnas
    columnas_utiles = [
        "DENOMINACION", "BARRIO", "ZONATRANSPORTE", "FECHAINICIO",
        "LINEAS", "TIPO", "GRADOACCESIBILIDAD", "TIPOVIA", "X", "Y"
    ]
    df = df[df.TIPOVIA.notna()]
    df = df[columnas_utiles]

    # Si una estación tiene varios accesos, nos quedamos con el primero.
    antes = len(df)
    df = df.drop_duplicates(subset=['DENOMINACION'], keep='first')
    print(f"Eliminados {antes - len(df)} registros duplicados por nombre de estación.")
    
    # 3. Tratamiento de Cercanías (RENFE)
    dfCercanias = dfCercanias[["DENOMINACION", "X", "Y", "LINEAS"]].dropna(subset=['LINEAS'])
    dfCercanias = dfCercanias[dfCercanias.LINEAS.notna()]

    # 4. Cruce Metro-Renfe (Tolerancia espacial)
    TOLERANCIA = 100 
    df['RENFE'] = None
    
    for idx, row in dfCercanias.iterrows():
        mask = (np.abs(df['X'] - row['X']) <= TOLERANCIA) & (np.abs(df['Y'] - row['Y']) <= TOLERANCIA)
        lineas_r = [l.strip().replace("'", "") for l in str(row['LINEAS']).replace("[", "").replace("]", "").split(',')]
        df.loc[mask, 'RENFE'] = str(lineas_r)

    # 5. Transformación de tipos y limpieza de LINEAS
    def limpiar_lista_lineas(valor):
        if pd.isna(valor): return []
        return [l.strip().replace("'", "").replace('"', '') for l in str(valor).replace("[", "").replace("]", "").split(',')]

    df['LINEAS_LISTA'] = df['LINEAS'].apply(limpiar_lista_lineas)
    df['RENFE'] = df['RENFE'].apply(limpiar_lista_lineas)

    df['LINEAS_ESTRUCTURADAS'] = df['LINEAS_LISTA'].apply(
        lambda lineas: [{"linea": l, "orden": 0} for l in lineas]
    )

    # 6. Función de ayuda para el usuario (imprimir para rellenar)
    def imprimir_guia_llenado(dataframe):
        print("\n" + "="*50)
        print("GUÍA PARA RELLENAR EL ORDEN DE LAS ESTACIONES")
        print("="*50)
        for _, row in dataframe.sort_values(by=['LINEAS']).iterrows():
            lineas = ", ".join(row['LINEAS_LISTA'])
            print(f"Estación: {row['DENOMINACION']:<25} | Líneas a numerar: {lineas}")
        print("="*50 + "\n")

    # Llamamos a la función para que veas qué tienes que rellenar
    imprimir_guia_llenado(df)

    # 7. Formateo final
    df["FECHAINICIO"] = pd.to_datetime(df.FECHAINICIO, format='%Y%m%d', errors='coerce')
    df["BARRIO"] = df["BARRIO"].fillna(-1).astype(int)
    
    df_final = df.drop(columns=['LINEAS', 'LINEAS_LISTA']).rename(columns={'LINEAS_ESTRUCTURADAS': 'LINEAS'})

    # Guardar
    df_final.to_csv("clean_dataset.csv", index=False)
    print("Dataset guardado en 'clean_dataset.csv'")

if __name__ == "__main__":
    limpiar_y_preparar_dataset()