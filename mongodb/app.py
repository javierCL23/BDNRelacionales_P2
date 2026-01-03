from flask import Flask, render_template, request, jsonify
from pymongo import MongoClient

import ast
import os

app = Flask(__name__)

# Conexión a MongoDB
MONGO_URL = os.environ.get('MONGO_URL')
client = MongoClient(MONGO_URL)
db = client["Practica2_DB"]

@app.route('/')
def index():
    return render_template('index.html')

# Obtener campos de selectores (líneas, estudios, campus)
@app.route('/api/data/opciones', methods=['GET'])
def get_opciones():
    try:
        # Extraemos y limpiamos de posibles nulos o vacíos
        universidades = [u for u in db.campus.distinct("universidad") if u]
        zonas = [z for z in db.estaciones.distinct("zona") if z]
        
        # Ojo: asegúrate de que el nombre del campo en MongoDB sea exactamente "universidad"
        return jsonify({
            "lineas": sorted(db.lineas.distinct("linea_id")),
            "campus": sorted(db.campus.distinct("nombre")),
            "universidades": sorted(universidades),
            "zonas": sorted(zonas)
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
    return jsonify(resultados)

@app.route('/api/consultas/estaciones-renfe', methods=['GET'])
def consulta_renfe():
    resultados = list(db.estaciones.find(
        {"tieneRenfe": True},
        {"_id": 0, "nombre": 1, "detallesRenfe": 1}
    ))
    return jsonify(resultados)

@app.route('/api/consultas/accesibilidad-zona', methods=['GET'])
def consulta_accesibilidad():
    zona = request.args.get('zona')
    resultados = list(db.estaciones.find(
        {"zona": zona, "grado_accesibilidad": {"$ne": "N"}},
        {"_id": 0, "nombre": 1, "grado_accesibilidad": 1}
    ))
    return jsonify(resultados)

@app.route('/api/consultas/campus-universidad', methods=['GET'])
def consulta_campus_uni():
    uni = request.args.get('universidad')
    resultados = list(db.campus.find(
        {"universidad": uni},
        {"_id": 0, "nombre": 1, "universidad": 1}
    ))
    return jsonify(resultados)

@app.route('/api/consultas/campus-estacion', methods=['GET'])
def consulta_campus_estacion():
    estacion = request.args.get('estacion_nombre')
    resultados = list(db.campus.find(
        {"estaciones_cercanas": {"$elemMatch": {"nombre": estacion.upper(), "rol": "principal"}}},
        {"_id": 0, "nombre": 1, "universidad": 1}
    ))
    return jsonify(resultados)

@app.route('/api/consultas/grados-detalle', methods=['GET'])
def consulta_grados():
    nombre_grado = request.args.get('nombre_grado')
    
    pipeline = [
        {"$unwind":"$estudios"},
        {"$match":{"estudios.tipo":"GRADO"}}
    ]
    # Usuario escribió un nombre (caso alternativo)
    if nombre_grado:
        pipeline.append({"$match": {"estudios.nombre": {"$regex": nombre_grado, "$options": "i"}}})
        
    pipeline.extend([
        {"$project": {"_id": 0, "nombre": "$estudios.nombre", "nombreCampus": "$nombre", "universidad": 1}},
        {"$sort": {"nombre": 1}}
    ])
    
    resultados = list(db.campus.aggregate(pipeline))
    return jsonify(resultados)


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)