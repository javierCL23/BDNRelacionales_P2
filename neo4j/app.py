from flask import Flask, render_template, request, jsonify
from neo4j import GraphDatabase
import os

app = Flask(__name__)

URI = os.environ.get("NEO_URL", "neo4j://localhost:7687")
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
                    
                    # Etiqueta visible por defecto
                    label_show = props.get('nombre') or props.get('Universidad') or "Nodo"
                    group = labels[0] if labels else "Default"
                    
                    # Tooltip básico (propiedades del nodo)
                    tooltip_lines = []
                    for k, v in props.items():
                        if k not in ['nombre', 'X', 'Y', 'Renfe']: 
                            tooltip_lines.append(f"{k}: {v}")
                    
                    # Icono Renfe si existe
                    if group == 'Estacion' and props.get('Renfe') and props.get('Renfe') != "[]":
                        label_show += "\n"
                        tooltip_lines.append(f"Renfe: {props.get('Renfe')}")

                    nodes[node_id] = {
                        "id": node_id,
                        "label": label_show,
                        "group": group,
                        "title": "\n".join(tooltip_lines) if tooltip_lines else label_show
                    }

            # 2. SI ES UN CAMINO (resultado de rutas SHORTEST)
            elif hasattr(item, 'nodes') and hasattr(item, 'relationships'):
                sub_nodes, sub_edges = construir_grafo([{"n": n} for n in item.nodes])
                nodes.update({n['id']: n for n in sub_nodes})
                
                for rel in item.relationships:
                    start = rel.start_node.element_id if hasattr(rel.start_node, 'element_id') else rel.start_node.id
                    end = rel.end_node.element_id if hasattr(rel.end_node, 'element_id') else rel.end_node.id
                    props = dict(rel)
                    lbl = rel.type
                    
                    edge_config = {
                        "from": start, 
                        "to": end, 
                        "color": "red", 
                        "width": 3
                    }

                    if lbl == 'CONEXION':
                        edge_config["label"] = props.get('linea', '')
                        edge_config["arrows"] = {"to": {"enabled": False}} # Sin flecha (bidireccional)
                    else:
                        edge_config["label"] = lbl
                        edge_config["arrows"] = "to"

                    edges.append(edge_config)

            # 3. SI ES RELACIÓN SUELTA (Consultas directas)
            elif hasattr(item, 'start_node'):
                start = item.start_node.element_id if hasattr(item.start_node, 'element_id') else item.start_node.id
                end = item.end_node.element_id if hasattr(item.end_node, 'element_id') else item.end_node.id
                
                type_rel = item.type
                props = dict(item)
                
                # Configuración base
                edge_conf = {
                    "from": start, 
                    "to": end, 
                    "arrows": "to",
                    "font": {"align": "top", "size": 10}
                }

                # PERSONALIZACIÓN POR TIPO

                if type_rel == 'TIENE_ESTACION':
                    edge_conf["label"] = f"Orden {props.get('orden','')}"
                
                elif type_rel == 'CERCANA':
                    lbl = f"{props.get('minutos','?')} min"
                    if props.get('rol'):
                        lbl += f"\n({props.get('rol')})"
                    edge_conf["label"] = lbl

                elif type_rel == 'CONEXION':
                    edge_conf["label"] = props.get('linea', 'Conexión')
                    edge_conf["arrows"] = {"to": {"enabled": False}} 
                    edge_conf["color"] = "red"
                    edge_conf["width"] = 3

                elif type_rel == 'OFRECE':
                    edge_conf["label"] = "Imparte"
                    edge_conf["color"] = "#f39c12"
                    
                    info_tooltip = []
                    if props.get('coordinador'): info_tooltip.append(f"{props.get('coordinador')}")
                    if props.get('creditos'): info_tooltip.append(f"{props.get('creditos')} ECTS")
                    if props.get('rama'): info_tooltip.append(f"{props.get('rama')}")
                    
                    if info_tooltip:
                        edge_conf["title"] = "\n".join(info_tooltip)

                edges.append(edge_conf)

    return list(nodes.values()), edges

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/init')
def init_data():
    with driver.session() as session:
        # Consultas básicas de carga
        estaciones = [r['n'] for r in session.run("MATCH (e:Estacion) RETURN e.nombre as n ORDER BY n")]
        campus = [r['n'] for r in session.run("MATCH (c:Campus) RETURN c.nombre as n ORDER BY n")]
        estudios = [r['n'] for r in session.run("MATCH (e:Estudio) RETURN e.nombre as n ORDER BY n")]
        
        # Obtener líneas limpias (quitando comillas si existen)
        lineas_raw = session.run("MATCH (l:Linea) RETURN l.nombre as n ORDER BY n")
        lineas = sorted(list(set([l['n'].replace("'", "").replace("L", "") for l in lineas_raw])))
        
    return jsonify({
        "estaciones": estaciones, "campus": campus, "estudios": estudios, "lineas": lineas
    })

@app.route('/api/accion', methods=['POST'])
def accion():
    opcion = request.json.get('opcion')
    data = request.json.get('data', {})
    
    query = ""
    params = {}

    # 5: Tabla Resumen
    if opcion == '5':
        query = """
        MATCH (c:Campus)-[:OFRECE]->(e:Estudio)
        RETURN c.Universidad as universidad, e.nombre as estudio
        """
        stats = {}
        with driver.session() as session:
            result = session.run(query)
            for record in result:
                uni = record['universidad']
                estudio = record['estudio']
                
                if uni not in stats:
                    stats[uni] = {"grados": 0, "masters": 0}
                
                if "GRADO EN" in estudio.upper():
                    stats[uni]["grados"] += 1
                else:
                    stats[uni]["masters"] += 1
        
        table_data = [{"universidad": k, "grados": v["grados"], "masters": v["masters"]} for k, v in stats.items()]
        return jsonify({"type": "table", "data": table_data})

    # CONSULTAS DE GRAFOS
    
    # 1. Consultar estaciones de una línea
    if opcion == '1':
        linea_fmt = f"'R'" if data['linea'] == 'R' else f"'L{data['linea']}'"
        query = f"""
        MATCH (l:Linea {{nombre: {linea_fmt}}})
        MATCH (l)-[r:TIENE_ESTACION]->(e:Estacion)
        OPTIONAL MATCH (e)-[s:CONEXION {{linea: {linea_fmt}}}]-(e2:Estacion)
        RETURN l, r, e, s, e2
        """

    # 2. Consultar HUBS (Estaciones con > 1 campus cerca)
    elif opcion == '2':
        query = """
        MATCH (c:Campus)-[r:CERCANA]->(e:Estacion)
        WITH e, collect(c) as campuses, collect(r) as rels
        WHERE size(campuses) > 1
        UNWIND campuses as c
        UNWIND rels as rel
        RETURN e, c, rel
        """

    # 3. Consultar estaciones con Renfe y Campus
    elif opcion == '3':
        query = """
        MATCH (c:Campus)-[r:CERCANA]->(e:Estacion)
        WHERE e.Renfe IS NOT NULL AND e.Renfe <> 'NULL' AND e.Renfe <> '[]'
        RETURN c, r, e
        """

    # 4. Consultar Campus por Estudio
    elif opcion == '4':
        params = {'estudio': data['estudio']}
        query = """
        MATCH (est:Estudio {nombre: $estudio})
        MATCH (c:Campus)-[r:OFRECE]->(est)
        RETURN est, r, c
        """

    # 6. Ruta Estación -> Campus
    elif opcion == '6':
        params = {'origen': data['origen'], 'destino': data['campus']}
        query = """
        MATCH (start:Estacion {nombre: $origen})
        MATCH (c:Campus {nombre: $destino})-[r_cercana:CERCANA]-(end:Estacion)
        MATCH p = SHORTEST 1 (start)-[:CONEXION*]-(end)
        RETURN start, c, p, r_cercana, end
        """

    # 7. Ruta Estación -> Grado
    elif opcion == '7':
        params = {'origen': data['origen'], 'estudio': data['estudio']}
        query = """
        MATCH (start:Estacion {nombre: $origen})
        MATCH (est:Estudio {nombre: $estudio})<-[r_ofrece:OFRECE]-(c:Campus)
        MATCH (c)-[r_cercana:CERCANA]-(end:Estacion)
        MATCH p = SHORTEST 1 (start)-[:CONEXION*]-(end)
        RETURN start, est, c, p, r_ofrece, r_cercana
        """

    with driver.session() as session:
        result = session.run(query, params)
        nodes, edges = construir_grafo(result)

    return jsonify({"type": "graph", "nodes": nodes, "edges": edges})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)