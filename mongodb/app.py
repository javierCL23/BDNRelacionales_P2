from flask import Flask, render_template, request, jsonify
from pymongo import MongoClient

import ast
import os

app = Flask(__name__)

# Conexión a MongoDB
MONGO_URL = os.environ.get('MONGO_URL',"mongodb://127.0.0.1:27017")
client = MongoClient(MONGO_URL)
db = client["Practica2_DB"]

@app.route('/')
def index():
    return render_template('index.html')

# Obtener campos de selectores (líneas,estaciones, estudios, campus, zonas)
@app.route('/api/data/opciones', methods=['GET'])
def get_opciones():
    try:
        universidades = [u for u in db.campus.distinct("universidad") if u]
        zonas = [z for z in db.estaciones.distinct("zona") if z]
        todas_estaciones = sorted(db.estaciones.distinct("nombre"))
        
        return jsonify({
            "lineas": sorted(db.lineas.distinct("linea_id")),
            "campus": sorted(db.campus.distinct("nombre")),
            "universidades": sorted(universidades),
            "zonas": sorted(zonas),
            "estaciones_lista": todas_estaciones
        })
    except Exception as e:
        print(f"Error cargando opciones: {e}")
        return jsonify({"error": str(e)}), 500
        

# Obtener estaciones de cada línea
@app.route('/api/data/estaciones/<linea_id>', methods=['GET'])
def get_estaciones_linea(linea_id):
    linea = db.lineas.find_one({"linea_id": linea_id})
    if linea:
        return jsonify([e["nombre_estacion"] for e in linea["estaciones"]])
    return jsonify([])



# --- RUTAS CRUD (ACCIONES) ---
@app.route('/api/metro/borrar', methods=['POST'])
def borrar_linea():
    linea_id = request.form.get('linea_id')
    if not linea_id:
        return "Error: No se proporcionó un ID de línea", 400

    resultado_linea = db.lineas.delete_one({"linea_id": linea_id})
    resultado_estaciones = db.estaciones.update_many(
        {"lineas_ids.linea": linea_id},
        {"$pull": {"lineas_ids": {"linea": linea_id}}}
    )
    db.estaciones.delete_many({"lineas_ids": {"$size": 0}})

    return f"""
    <h1>Operación Exitosa: Borrado de Línea</h1>
    <p>La <strong>Línea {linea_id}</strong> ha sido eliminada del sistema.</p>
    <ul>
        <li>Líneas borradas: {resultado_linea.deleted_count}</li>
        <li>Estaciones actualizadas: {resultado_estaciones.modified_count}</li>
    </ul>
    <hr>
    <a href="/">[Volver al panel]</a>
    """

@app.route('/api/metro/cortar', methods=['POST'])
def cortar_linea():
    linea_id = request.form.get('linea_id')
    est_inicio = request.form.get('estacion_inicio')
    est_fin = request.form.get('estacion_fin')

    linea = db.lineas.find_one({"linea_id": linea_id})
    nombres_estaciones = [e["nombre_estacion"] for e in linea["estaciones"]]
    
    idx_i = nombres_estaciones.index(est_inicio)
    idx_f = nombres_estaciones.index(est_fin)
    
    rango = nombres_estaciones[min(idx_i, idx_f) : max(idx_i, idx_f) + 1]

    resultado = db.estaciones.update_many(
        {"nombre": {"$in": rango}},
        {"$set": {"grado_accesibilidad": "N"}}
    )

    return f"""
    <h1>Operación Exitosa: Corte de Línea</h1>
    <p>El tramo <strong>{est_inicio} - {est_fin}</strong> (Línea {linea_id}) ha sido marcado como no accesible.</p>
    <p>Estaciones afectadas: {resultado.modified_count}</p>
    <hr>
    <a href="/">[Volver al panel]</a>
    """

@app.route('/api/data/estudios_por_campus/<campus_nombre>', methods=['GET'])
def get_estudios_campus(campus_nombre):
    campus = db.campus.find_one({"nombre": campus_nombre})
    if campus and "estudios" in campus:
        return jsonify([e["nombre"] for e in campus["estudios"]])
    return jsonify([])

@app.route('/api/estudios/actualizar', methods=['POST'])
def actualizar_coordinador():
    nombre_campus = request.form.get('campus_id')
    nombre_estudio = request.form.get('estudio_id')
    nuevo_coord = request.form.get('coordinador')
    
    # Filtramos por AMBOS campos: nombre del campus y nombre del estudio dentro de su array
    resultado = db.campus.update_one(
        { "nombre": nombre_campus, "estudios.nombre": nombre_estudio },
        { "$set": { "estudios.$.coordinador": nuevo_coord } }
    )
    
    status = "Éxito" if resultado.modified_count > 0 else "Aviso"
    return f"""
    <h1>Operación: {status}</h1>
    <p>Campus: <strong>{nombre_campus}</strong></p>
    <p>Estudio: <strong>{nombre_estudio}</strong></p>
    <p>Nuevo Coordinador: <strong>{nuevo_coord}</strong></p>
    <hr>
    <a href="/">[Volver al panel]</a>
    """


@app.route('/api/estudios/nuevo', methods=['POST'])
def nuevo_estudio():
    nombre = request.form.get('nombre')
    tipo = request.form.get('tipo')
    creditos = request.form.get('creditos')
    coordinador = request.form.get('coordinador_init')
    nombre_campus = request.form.get('campus_id')

    nuevo_estudio_embebido = {
        "nombre": nombre,
        "tipo": tipo,
        "creditos": int(creditos),
        "coordinador": coordinador
    }

    resultado = db.campus.update_one(
        {"nombre": nombre_campus},
        {"$push": {"estudios": nuevo_estudio_embebido}}
    )
    
    return f"""
    <h1>Registro Exitoso</h1>
    <p>El estudio <strong>{nombre}</strong> ({tipo}) ha sido añadido al <strong>{nombre_campus}</strong>.</p>
    <p>Créditos: {creditos} | Coordinador: {coordinador}</p>
    <hr>
    <a href="/">[Volver al panel]</a>
    """

# --- RUTAS DE CONSULTAS DE LECTURA ---
# --- RUTAS DE CONSULTAS DE LECTURA (RETORNO HTML) ---

@app.route('/api/consultas/estaciones-linea', methods=['GET'])
def consulta_recorrido():
    linea_id = request.args.get('linea_id')
    pipeline = [
        {"$match": {"linea_id": linea_id}},
        {"$unwind": "$estaciones"},
        {"$sort": {"estaciones.indiceEnLinea": 1}},
        {"$project": {"_id": 0, "nombre": "$estaciones.nombre_estacion", "indice": "$estaciones.indiceEnLinea"}}
    ]
    resultados = list(db.lineas.aggregate(pipeline))
    
    filas = "".join([f"<tr><td>{r['indice']}</td><td>{r['nombre']}</td></tr>" for r in resultados])
    
    return f"""
    <h1>Recorrido: Línea {linea_id}</h1>
    <table border="1" style="width:100%; border-collapse: collapse;">
        <thead style="background: #2c3e50; color: white;">
            <tr><th style="padding:10px;">Orden</th><th style="padding:10px;">Estación</th></tr>
        </thead>
        <tbody>{filas}</tbody>
    </table>
    <hr><a href="/">[Volver al panel]</a>
    """

@app.route('/api/consultas/estaciones-renfe', methods=['GET'])
def consulta_renfe():
    resultados = list(db.estaciones.find(
        {"tieneRenfe": True},
        {"_id": 0, "nombre": 1, "detallesRenfe": 1}
    ))
    
    filas = "".join([f"<tr><td>{r['nombre']}</td><td>{r.get('detallesRenfe', 'Cercanías')}</td></tr>" for r in resultados])
    
    return f"""
    <h1>Correspondencias con Renfe</h1>
    <table border="1" style="width:100%; border-collapse: collapse;">
        <thead style="background: #e74c3c; color: white;">
            <tr><th style="padding:10px;">Estación Metro</th><th style="padding:10px;">Detalles Renfe</th></tr>
        </thead>
        <tbody>{filas}</tbody>
    </table>
    <hr><a href="/">[Volver al panel]</a>
    """

@app.route('/api/consultas/accesibilidad-zona', methods=['GET'])
def consulta_accesibilidad():
    zona = request.args.get('zona')
    # Filtrado por zona y accesibilidad distinta a 'N'
    resultados = list(db.estaciones.find(
        {"zona": zona, "grado_accesibilidad": {"$ne": "N"}},
        {"_id": 0, "nombre": 1, "grado_accesibilidad": 1}
    ))

    total = len(resultados)
    filas = "".join([f"<tr><td style='padding:8px;'>{r['nombre']}</td><td style='padding:8px;'>Nivel {r['grado_accesibilidad']}</td></tr>" for r in resultados])
    
    return f"""
    <h1>Estaciones Accesibles - Zona {zona}</h1>
    <p style="background: #d4edda; color: #155724; padding: 10px; border-radius: 5px; font-weight: bold;">
        Se han encontrado <strong>{total}</strong> estaciones accesibles en esta zona.
    </p>
    <table border="1" style="width:100%; border-collapse: collapse; margin-top: 10px;">
        <thead style="background: #27ae60; color: white;">
            <tr>
                <th style="padding:10px; text-align: left;">Estación</th>
                <th style="padding:10px; text-align: left;">Grado de Accesibilidad</th>
            </tr>
        </thead>
        <tbody>
            {filas if total > 0 else "<tr><td colspan='2' style='padding:10px; text-align:center;'>No se han encontrado estaciones accesibles en esta zona.</td></tr>"}
        </tbody>
    </table>
    <hr>
    <a href="/">[Volver al panel]</a>
    """

@app.route('/api/consultas/campus-universidad', methods=['GET'])
def consulta_campus_uni():
    uni = request.args.get('universidad')
    resultados = list(db.campus.find(
        {"universidad": uni},
        {"_id": 0, "nombre": 1, "universidad": 1}
    ))
    
    filas = "".join([f"<tr><td>{r['nombre']}</td><td>{r['universidad']}</td></tr>" for r in resultados])
    
    return f"""
    <h1>Sedes de la {uni}</h1>
    <table border="1" style="width:100%; border-collapse: collapse;">
        <thead style="background: #3498db; color: white;">
            <tr><th style="padding:10px;">Nombre Campus</th><th style="padding:10px;">Universidad</th></tr>
        </thead>
        <tbody>{filas}</tbody>
    </table>
    <hr><a href="/">[Volver al panel]</a>
    """

@app.route('/api/consultas/campus-estacion', methods=['GET'])
def consulta_campus_estacion():
    estacion = request.args.get('estacion_nombre')
    resultados = list(db.campus.find(
        {"estaciones_cercanas": {"$elemMatch": {"nombre": estacion, "rol": "principal"}}},
        {"_id": 0, "nombre": 1, "universidad": 1}
    ))
    
    total = len(resultados)
    filas = "".join([f"<tr><td>{r['nombre']}</td><td>{r['universidad']}</td></tr>" for r in resultados])
    
    return f"""
    <h1>Campus vinculados a: {estacion}</h1>
    <p>Se han encontrado <strong>{total}</strong> campus que tienen esta parada como principal.</p>
    <table border="1" style="width:100%; border-collapse: collapse;">
        <thead style="background: #2c3e50; color: white;">
            <tr><th style="padding:10px;">Campus</th><th style="padding:10px;">Universidad</th></tr>
        </thead>
        <tbody>
            {filas if total > 0 else "<tr><td colspan='2' style='padding:10px; text-align:center;'>No hay campus asociados.</td></tr>"}
        </tbody>
    </table>
    <hr><a href="/">[Volver al panel]</a>
    """

@app.route('/api/consultas/grados-detalle', methods=['GET'])
def consulta_grados():
    nombre_grado = request.args.get('nombre_grado')
    pipeline = [{"$unwind":"$estudios"}, {"$match":{"estudios.tipo":"GRADO"}}]
    
    if nombre_grado:
        pipeline.append({"$match": {"estudios.nombre": {"$regex": nombre_grado, "$options": "i"}}})
        
    pipeline.extend([
        {"$project": {"_id": 0, "nombre": "$estudios.nombre", "nombreCampus": "$nombre", "universidad": 1}},
        {"$sort": {"nombre": 1}}
    ])
    
    resultados = list(db.campus.aggregate(pipeline))
    
    filas = "".join([f"<tr><td>{r['nombre']}</td><td>{r['nombreCampus']}</td><td>{r['universidad']}</td></tr>" for r in resultados])
    
    return f"""
    <h1>Detalle de Títulos de Grado</h1>
    <table border="1" style="width:100%; border-collapse: collapse;">
        <thead style="background: #3498db; color: white;">
            <tr>
                <th style="padding:10px;">Grado</th>
                <th style="padding:10px;">Campus</th>
                <th style="padding:10px;">Universidad</th>
            </tr>
        </thead>
        <tbody>{filas}</tbody>
    </table>
    <hr><a href="/">[Volver al panel]</a>
    """
# --- RUTAS DE AGREGACIONES ---

@app.route('/api/agregaciones/estaciones-por-linea', methods=['GET'])
def agregacion_estaciones_linea():
    pipeline = [
        {"$unwind": "$lineas_ids"},
        {"$group": {"_id": "$lineas_ids.linea", "nEstaciones": {"$sum": 1}}},
        {"$sort": {"nEstaciones": -1}},
        {"$project":{"_id":0,"linea":"$_id","nEstaciones":1}}
    ]
    resultados = list(db.estaciones.aggregate(pipeline))
    
    filas = "".join([f"<tr><td>Línea {r['linea']}</td><td>{r['nEstaciones']}</td></tr>" for r in resultados])
    
    return f"""
    <h1>Ranking: Estaciones por Línea</h1>
    <table border="1" style="width:100%; border-collapse: collapse; text-align: left;">
        <thead style="background: #2c3e50; color: white;">
            <tr><th style="padding: 10px;">Línea</th><th style="padding: 10px;">Nº Estaciones</th></tr>
        </thead>
        <tbody>
            {filas}
        </tbody>
    </table>
    <hr><a href="/">[Volver al panel]</a>
    """

@app.route('/api/agregaciones/universitarias-por-zona', methods=['GET'])
def agregacion_universitarias_zona():
    pipeline = [
        {"$unwind": "$estaciones_cercanas"},
        {"$lookup": {
            "from": "estaciones",
            "localField": "estaciones_cercanas.nombre",
            "foreignField": "nombre",
            "as": "info_estacion"
        }},
        {"$unwind": "$info_estacion"},
        {"$group": {"_id": "$info_estacion.zona", "nEstaciones": {"$count": {}}}},
        {"$project":{"_id":0,"Tarifa":"$_id","nEstaciones":1}},
        {"$sort": {"Tarifa": 1}}
    ]
    resultados = list(db.campus.aggregate(pipeline))
    
    filas = "".join([f"<tr><td>Zona {r['Tarifa']}</td><td>{r['nEstaciones']}</td></tr>" for r in resultados])
    
    return f"""
    <h1>Estaciones Universitarias por Zona</h1>
    <table border="1" style="width:100%; border-collapse: collapse; text-align: left;">
        <thead style="background: #e74c3c; color: white;">
            <tr><th style="padding: 10px;">Zona Tarifaria</th><th style="padding: 10px;">Nº Estaciones</th></tr>
        </thead>
        <tbody>
            {filas}
        </tbody>
    </table>
    <hr><a href="/">[Volver al panel]</a>
    """

@app.route('/api/agregaciones/estudios-universidad', methods=['GET'])
def agregacion_estudios_universidad():
    pipeline = [
        {"$unwind": "$estudios"},
        {"$group": {
            "_id": "$universidad",
            "nGrados": {"$sum": {"$cond": [{"$eq": ["$estudios.tipo", "GRADO"]}, 1, 0]}},
            "nMaster": {"$sum": {"$cond": [{"$eq": ["$estudios.tipo", "MÁSTER"]}, 1, 0]}}
        }},
        {"$project": {"_id": 0, "universidad": "$_id", "nGrados": 1, "nMaster": 1}},
        {"$sort": {"universidad": 1}}
    ]
    resultados = list(db.campus.aggregate(pipeline))
    
    filas = "".join([f"<tr><td>{r['universidad']}</td><td>{r['nGrados']}</td><td>{r['nMaster']}</td></tr>" for r in resultados])
    
    return f"""
    <h1>Informe de Estudios por Universidad</h1>
    <table border="1" style="width:100%; border-collapse: collapse; text-align: left;">
        <thead style="background: #3498db; color: white;">
            <tr>
                <th style="padding: 10px;">Universidad</th>
                <th style="padding: 10px;">Grados</th>
                <th style="padding: 10px;">Másteres</th>
            </tr>
        </thead>
        <tbody>
            {filas}
        </tbody>
    </table>
    <hr><a href="/">[Volver al panel]</a>
    """

@app.route('/api/agregaciones/comparar-trayectos', methods=['GET'])
def comparar_trayectos():
    linea_id = request.args.get('linea_id')
    est_a = request.args.get('estacion_a')
    est_b = request.args.get('estacion_b')

    if not all([linea_id, est_a, est_b]):
        return jsonify({"error": "Faltan parámetros"}), 400

    pipeline = [
        {"$match": {"linea_id": linea_id}},
        {"$project": {
            "_id": 0,
            "estacionA": {
                "$filter": {
                    "input": "$estaciones",
                    "as": "e",
                    "cond": {"$eq": ["$$e.nombre_estacion", est_a]}
                }
            },
            "estacionB": {
                "$filter": {
                    "input": "$estaciones",
                    "as": "e",
                    "cond": {"$eq": ["$$e.nombre_estacion", est_b]}
                }
            }
        }},
        {"$project": {
            "estacionA": {"$arrayElemAt": ["$estacionA", 0]},
            "estacionB": {"$arrayElemAt": ["$estacionB", 0]}
        }},
        {"$project": {
            "distancia": {
                "$abs": {
                    "$subtract": [
                        "$estacionA.indiceEnLinea",
                        "$estacionB.indiceEnLinea"
                    ]
                }
            }
        }}
    ]
    
    resultado = list(db.lineas.aggregate(pipeline))
    # Devuelve 0 en caso de no encontrarse.
    distancia = resultado[0]['distancia'] if resultado else 0

    return f"""
    <h1>Cálculo de Trayecto: Línea {linea_id}</h1>
    <div style="padding: 20px; border: 1px solid #eee; border-radius: 8px;">
        <p>Origen: <strong>{est_a}</strong></p>
        <p>Destino: <strong>{est_b}</strong></p>
        <hr>
        <h2 style="color: #3498db;">Distancia: {distancia} estaciones</h2>
    </div>
    <hr>
    <a href="/">[Volver al panel]</a>
    """

@app.route('/api/agregaciones/recomendacion', methods=['GET'])
def recomendacion_campus():
    linea_id = request.args.get('linea_id')
    est_origen = request.args.get('estacion_origen')
    nombre_grado = request.args.get('nombre_grado')

    if not all([linea_id, est_origen, nombre_grado]):
        return "<h1>Error: Faltan parámetros</h1>", 400

    pipeline_origen = [
        {"$match": {"nombre": est_origen}},
        {"$unwind": "$lineas_ids"},
        {"$match": {"lineas_ids.linea": linea_id}},
        {"$project": {"_id": 0, "orden": "$lineas_ids.orden"}}
    ]

    res_origen = list(db.estaciones.aggregate(pipeline_origen))

    if not res_origen:
        return "Error: La estación de origen no pertenece a esa línea."

    indice_origen = res_origen[0]['orden']

    pipeline = [
        # 1. Separar por estudios
        {"$unwind": "$estudios"},

        # 2. Filtrar por grados con regex válido
        {
            "$match": {
                "estudios.nombre": {"$regex": nombre_grado, "$options": "i"},
                "estudios.tipo": "GRADO"  
            }
        },

        # 3. Separar por estaciones
        {"$unwind": "$estaciones_cercanas"},

        # 4. Cruzamos con la colección estaciones
        {
            "$lookup": {
                "from": "estaciones",
                "localField": "estaciones_cercanas.nombre",
                "foreignField": "nombre",
                "as": "info_estacion"
            }
        },
        {"$unwind": "$info_estacion"},

        # 5. Filtrar por línea
        {"$unwind": "$info_estacion.lineas_ids"},
        {
            "$match": {
                "info_estacion.lineas_ids.linea": linea_id
            }
        },

        # 6. Cálculo de distancias
        {
            "$project": {
                "campus": "$nombre",
                "universidad": "$universidad",
                "grado_completo": "$estudios.nombre",
                "coordinador": "$estudios.coordinador",
                "rama": "$estudios.rama", 

                "estacion_destino": "$estaciones_cercanas.nombre",
                "distancia": {
                    "$abs": {
                        "$subtract": ["$info_estacion.lineas_ids.orden", indice_origen]
                    }
                }
            }
        },
        # 7. Quedarnos con la más cercana
        {"$sort": {"distancia": 1}},
        {"$limit": 1}
    ]

    resultados = list(db.campus.aggregate(pipeline))

    if not resultados:
        return f"<h1>Sin resultados</h1><p>No hay campus con <strong>{nombre_grado}</strong> en la Línea {linea_id}.</p><a href='/'>Volver</a>"

    mejor = resultados[0]
    rama_str = mejor.get('rama', 'No especificada')

    return f"""
    <h1 style="text-align:center;">Campus Recomendado</h1>
    <div style="background: #34495e; color: white; padding: 15px; border-radius: 8px 8px 0 0;">
        <h2 style="margin:0;">{mejor['grado_completo']}</h2>
        <p style="margin: 5px 0 0 0; font-size: 0.9em; opacity: 0.9;">
            Rama: <strong>{rama_str}</strong> | Coordinador: <strong>{mejor['coordinador']}</strong>
        </p>
    </div>

    <div style="padding: 20px; border: 2px solid #34495e; border-top: none; border-radius: 0 0 8px 8px; background: #fff; text-align: center;">
        <h3 style="color: #2c3e50; margin-top: 0;">{mejor['campus']}</h3>
        <h4 style="color: #7f8c8d; margin-bottom: 20px;">{mejor['universidad']}</h4>
        
        <div style="display: flex; justify-content: space-around; align-items: center; background: #f4f6f7; padding: 15px; border-radius: 6px;">
            <div>
                <small>ESTÁS EN</small><br>
                <strong>{est_origen}</strong>
            </div>
            <div style="font-size: 1.5rem; color: #27ae60;">➝ {mejor['distancia']} paradas ➝</div>
            <div>
                <small>VIAJA A</small><br>
                <strong>{mejor['estacion_destino']}</strong>
            </div>
        </div>
    </div>
    <hr>
    <a href="/">[Volver al panel]</a>
    """

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)