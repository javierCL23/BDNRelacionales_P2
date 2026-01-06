from flask import Flask, render_template, request, jsonify
from neo4j import GraphDatabase
import os

app = Flask(__name__)

URI = os.environ.get("NEO_URL","neo4j://localhost:7687")
AUTH = ("neo4j", "password_seguro")
driver = GraphDatabase.driver(URI, auth=AUTH)


def construir_grafo(result):
    nodes = {}
    edges = []
    
    for record in result:
        for key, item in record.items():
            
            # 1. SI ES NODO
            if hasattr(item, 'labels'):
                node_id = item.element_id if hasattr(item, 'element_id') else item.id
                if node_id not in nodes:
                    labels = list(item.labels)
                    props = dict(item)
                    
                    label_show = props.get('nombre') or props.get('Universidad') or "Nodo"
                    group = labels[0] if labels else "Default"
                    
                    title_tooltip = str(props)
                    
                    if group == 'Estacion' and props.get('Renfe'):
                        label_show += "\n🚆" 
                    
                    nodes[node_id] = {
                        "id": node_id,
                        "label": label_show,
                        "group": group,
                        "title": title_tooltip
                    }

            # 2. SI ES UN CAMINO (Path) 
            elif hasattr(item, 'nodes') and hasattr(item, 'relationships'):
                # Recursivamente extraer los nodos
                sub_nodes, sub_edges = construir_grafo([{"n": n} for n in item.nodes])
                nodes.update({n['id']: n for n in sub_nodes})
                
                # Procesar las relaciones del camino manualmente
                for rel in item.relationships:
                    start = rel.start_node.element_id if hasattr(rel.start_node, 'element_id') else rel.start_node.id
                    end = rel.end_node.element_id if hasattr(rel.end_node, 'element_id') else rel.end_node.id
                    props = dict(rel)
                    
                    # Intentar sacar nombre de la línea, si no, el tipo
                    lbl = props.get('linea', rel.type)
                    
                    edges.append({
                        "from": start, 
                        "to": end, 
                        "label": lbl, 
                        "arrows": "to", 
                        "color": "red", 
                        "width": 3
                    })

            # 3. SI ES RELACIÓN (Sueltas)
            elif hasattr(item, 'start_node'):
                start = item.start_node.element_id if hasattr(item.start_node, 'element_id') else item.start_node.id
                end = item.end_node.element_id if hasattr(item.end_node, 'element_id') else item.end_node.id
                
                lbl = item.type
                props = dict(item)
                
                if lbl == 'TIENE_ESTACION': lbl = f"Orden {props.get('orden','')}"
                if lbl == 'CERCANA': lbl = f"{props.get('minutos','')} min"
                if lbl == 'SIGUIENTE': lbl = props.get('linea', 'Metro')
                if lbl == 'OFRECE': lbl = "Imparte"

                edges.append({
                    "from": start, "to": end, "label": lbl, "arrows": "to",
                    "font": {"align": "top", "size": 10}
                })

    return list(nodes.values()), edges

@app.route('/')
def index():
    return render_template('index.html')

# --- CARGA DE SELECTORES (Estaciones, Campus, Estudios, Lineas) ---
@app.route('/api/init')
def init_data():
    with driver.session() as session:
        estaciones = [r['n'] for r in session.run("MATCH (e:Estacion) RETURN e.nombre as n ORDER BY n")]
        campus = [r['n'] for r in session.run("MATCH (c:Campus) RETURN c.nombre as n ORDER BY n")]
        estudios = [r['n'] for r in session.run("MATCH (e:Estudio) RETURN e.nombre as n ORDER BY n")]
        # Extraemos líneas únicas
        lineas_raw = session.run("MATCH (l:Linea) RETURN l.nombre as n ORDER BY n")
        lineas = sorted(list(set([l['n'].replace("'", "").replace("L", "") for l in lineas_raw])))
        
    return jsonify({
        "estaciones": estaciones, "campus": campus, "estudios": estudios, "lineas": lineas
    })

# --- GESTOR CENTRAL DE CONSULTAS (Switch Case visual) ---
@app.route('/api/accion', methods=['POST'])
def accion():
    opcion = request.json.get('opcion')
    data = request.json.get('data', {})
    
    query = ""
    params = {}

    # 1. CONSULTAR LÍNEA
    if opcion == '1':
        linea_fmt = f"'R'" if data['linea'] == 'R' else f"'L{data['linea']}'"
        # Traer la línea, sus estaciones y las conexiones internas para ver el dibujo
        query = f"""
        MATCH (l:Linea {{nombre: {linea_fmt}}})
        MATCH (l)-[r:TIENE_ESTACION]->(e:Estacion)
        OPTIONAL MATCH (e)-[s:SIGUIENTE {{linea: {linea_fmt}}}]->(e2:Estacion)
        RETURN l, r, e, s, e2
        """

    # 2. HUBS UNIVERSITARIOS
    elif opcion == '2':
        query = """
        MATCH (c:Campus)-[r:CERCANA]->(e:Estacion)
        WITH e, collect(c) as campuses, collect(r) as rels
        WHERE size(campuses) > 1
        UNWIND campuses as c
        UNWIND rels as rel
        RETURN e, c, rel
        """

    # 3. RENFE Y CAMPUS
    elif opcion == '3':
        query = """
        MATCH (c:Campus)-[r:CERCANA]->(e:Estacion)
        WHERE e.Renfe IS NOT NULL AND e.Renfe <> 'NULL'
        RETURN c, r, e
        """

    # 4. CAMPUS POR ESTUDIO
    elif opcion == '4':
        params = {'estudio': data['estudio']}
        query = """
        MATCH (est:Estudio {nombre: $estudio})
        MATCH (c:Campus)-[r:OFRECE]->(est)
        RETURN est, r, c
        """

    # 5. RESUMEN UNIS (Visualización Jerárquica)
    elif opcion == '5':
        query = """
        MATCH (c:Campus)
        // Creamos nodo ficticio visual para la uni si queremos agrupar, 
        // pero aquí basta con mostrar los campus agrupados por propiedad 'Universidad'
        RETURN c
        """

    # 6. RUTA ESTACIÓN -> CAMPUS
    elif opcion == '6':
        params = {'origen': data['origen'], 'destino': data['campus']}
        query = """
        MATCH (start:Estacion {nombre: $origen})
        MATCH (c:Campus {nombre: $destino})-[:CERCANA]-(end:Estacion)
        MATCH p = SHORTEST 1 (start)-[:SIGUIENTE*]->(end)
        RETURN start, c, p
        """

    # 7. RUTA ESTACIÓN -> GRADO
    elif opcion == '7':
        params = {'origen': data['origen'], 'estudio': data['estudio']}
        query = """
        MATCH (start:Estacion {nombre: $origen})
        
        // 1. Capturar la relación entre Campus y Estudio (r_ofrece)
        MATCH (est:Estudio {nombre: $estudio})<-[r_ofrece:OFRECE]-(c:Campus)
        
        // 2. Capturar la relación entre Campus y su estación cercana (r_cercana)
        MATCH (c)-[r_cercana:CERCANA]-(end:Estacion)
        
        // 3. Calcular el camino
        MATCH p = SHORTEST 1 (start)-[:SIGUIENTE*]->(end)
        
        RETURN start, est, c, p, r_ofrece, r_cercana
        """

    with driver.session() as session:
        result = session.run(query, params)
        nodes, edges = construir_grafo(result)

    return jsonify({"nodes": nodes, "edges": edges})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)
