# Script para lectura y conversión de datasets de líneas de metro y renfe en uno solo para obtener todo lo necesario.
import pandas as pd
import numpy as np

#Lectura de datasets
df = pd.read_csv("M4_Estaciones.csv")
dfCercanias = pd.read_csv("M5_Estaciones.csv")

#Tratamos dataset metro
columnas_buenas = df.columns[df.isnull().sum() < df.shape[0]*0.9] # Quitamos las columnas con más de un 90% de nulls

df = df[columnas_buenas]
df = df[df.TIPOVIA.notna()]

columnas_utiles = [
    "DENOMINACION",
    "BARRIO",
    "ZONATRANSPORTE",
    "FECHAINICIO",
    "LINEAS",
    "TIPO",
    "GRADOACCESIBILIDAD",
    "TIPOVIA",
    "X",
    "Y",
    ]
df = df[columnas_utiles]

#Tratar dataset cercanías (RENFE)
dfCercanias = dfCercanias[["DENOMINACION","X","Y","LINEAS"]]
dfCercanias = dfCercanias[dfCercanias.LINEAS.notna()]


print("Número de paradas de metro:",df.shape[0])
print("Número de paradas de renfe:",dfCercanias.shape[0])

print()
print("*"*10, "METRO", "*"*10)
for campo in df.columns:
    print(campo,":",df[campo][274])


print()
print("*"*10, "RENFE", "*"*10)
for campo in dfCercanias.columns:
    print(campo,":",dfCercanias[campo][105])



#Añadir info de cercanías a df de metro

# Tolerancia para considerar que una estación de Metro y una de Renfe son la misma (en metros)
TOLERANCIA = 100  # metros

df['RENFE'] = None
for idx, row in dfCercanias.iterrows():
    x_c, y_c = row['X'], row['Y']
    lineas_c = row['LINEAS']

    # Encontrar estaciones de Metro dentro de la tolerancia (misma estación)
    mask = (np.abs(df['X'] - x_c) <= TOLERANCIA) & (np.abs(df['Y'] - y_c) <= TOLERANCIA)
    
    # Asignar las líneas de Cercanías
    df.loc[mask, 'RENFE'] = lineas_c


# Convertir tipos de datos
df['LINEAS'] = df['LINEAS'].apply(lambda x: x.split(',') if pd.notnull(x) else [])
df['RENFE'] = df['RENFE'].apply(lambda x: x.split(',') if pd.notnull(x) else [])

df["FECHAINICIO"] = pd.to_datetime(df.FECHAINICIO,format = '%Y%m%d')

df["TIPO"] = df["TIPO"].astype("category")
df["GRADOACCESIBILIDAD"] = df["GRADOACCESIBILIDAD"].astype("category")
df["TIPOVIA"] = df["TIPOVIA"].astype("category")

df["BARRIO"] = df["BARRIO"].fillna(-1).astype("int")

# Guardar dataset resultado
df.to_csv("clean_dataset.csv",index=False)