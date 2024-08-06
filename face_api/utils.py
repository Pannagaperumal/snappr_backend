# api/utils.py
import os
import cv2
import numpy as np
import pickle
import shutil
import networkx as nx
from tqdm import tqdm
from multiprocessing import Pool, cpu_count
from math import ceil
from keras_facenet import FaceNet

import logging 

UPLOAD_FOLDER = 'uploads'
SORTED_FOLDER = 'sorted_images'
TEMP_FOLDER = 'temp'
EMBEDDINGS_FILE = 'embeddings.pickle'
DEFAULT_THRESHOLD = 0.67
DEFAULT_ITERATIONS = 30

# Ensure necessary directories exist
for folder in [UPLOAD_FOLDER, SORTED_FOLDER, TEMP_FOLDER]:
    if not os.path.exists(folder):
        os.makedirs(folder)

# Initialize FaceNet model
facenet_model = FaceNet()

logger = logging.getLogger(__name__)

# Utility functions here...
# (Include get_image_paths, compute_embedding, get_similarity, draw_graph, chinese_whispers, save_embeddings, process_images, sort_images, get_person)
def get_image_paths(root_dir):
    paths = []
    for root, _, files in os.walk(root_dir):
        for file in files:
            if file.lower().endswith(('.png', '.jpg', '.jpeg', '.tiff', '.bmp')):
                paths.append(os.path.join(root, file))
    return paths

def compute_embedding(image_path, model):
    img = cv2.imread(image_path)
    if img is None:
        logger.warning(f"Could not read image: {image_path}")
        return None
    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    results = model.extract(img_rgb, threshold=0.95)
    
    if not results:
        return None
    
    return np.array([res['embedding'] for res in results])

def get_similarity(embeddings, current_face_emb):
    return np.sum(embeddings * current_face_emb, axis=1)

def draw_graph(data, threshold):
    G = nx.Graph()
    embeddings = np.array([d['embedding'] for d in data])
    
    for index, embedding in enumerate(tqdm(data, desc="Creating graph")):
        current_node = index + 1
        G.add_node(current_node, cluster=f"Person {current_node}", source=data[index]["path"])
        
        if current_node >= len(data):
            break
        
        similarities = get_similarity(embeddings[index+1:], data[index]["embedding"])
        
        for i, weight in enumerate(similarities):
            if weight > threshold:
                G.add_edge(current_node, current_node+i+1, weight=weight)
    
    return G

def chinese_whispers(G, iterations):
    for _ in tqdm(range(iterations), desc="Iterations"):
        nodes = list(G.nodes())
        np.random.shuffle(nodes)
        
        for node in nodes:
            neighbours = G[node]
            neighbour_clusters = {}
            
            for neighbour in neighbours:
                cluster = G.nodes[neighbour]['cluster']
                neighbour_clusters[cluster] = neighbour_clusters.get(cluster, 0) + G[node][neighbour]['weight']
            
            best_cluster = max(neighbour_clusters, key=neighbour_clusters.get) if neighbour_clusters else None
            
            if best_cluster:
                G.nodes[node]['cluster'] = best_cluster
    
    return G

def save_embeddings(process_data):
    model = FaceNet()
    bar = tqdm(total=len(process_data['image_paths']), position=process_data['process_id'])
    output = []
    
    for path in process_data['image_paths']:
        embeddings = compute_embedding(path, model)
        if embeddings is not None:
            if embeddings.shape[0] > 1:
                for embedding in embeddings:
                    output.append({"path": path, "embedding": embedding})
            else:
                output.append({"path": path, "embedding": embeddings[0]})
        bar.update()
    
    bar.close()
    
    with open(process_data['temp_path'], "wb") as f:
        pickle.dump(output, f)

def process_images(image_paths, processes=cpu_count()):
    imgs_per_process = ceil(len(image_paths) / processes)
    split_paths = [image_paths[i:i + imgs_per_process] for i in range(0, len(image_paths), imgs_per_process)]
    
    split_data = []
    for process_id, batch in enumerate(split_paths):
        temp_path = os.path.join(TEMP_FOLDER, f"process_{process_id}.pickle")
        process_data = {
            "process_id": process_id,
            "image_paths": batch,
            "temp_path": temp_path
        }
        split_data.append(process_data)
    
    with Pool(processes=processes) as pool:
        pool.map(save_embeddings, split_data)
    
    concat_embeddings = []
    for filename in os.listdir(TEMP_FOLDER):
        with open(os.path.join(TEMP_FOLDER, filename), "rb") as f:
            data = pickle.load(f)
        concat_embeddings.extend(data)
    
    with open(EMBEDDINGS_FILE, "wb") as f:
        pickle.dump(concat_embeddings, f)
    
    shutil.rmtree(TEMP_FOLDER)
    logger.info(f"Saved embeddings of {len(concat_embeddings)} faces to disk.")
    
    return concat_embeddings

def sort_images(G):
    for node, attribute in G.nodes.items():
        source = attribute["source"]
        destination = os.path.join(SORTED_FOLDER, attribute["cluster"])
        
        if not os.path.exists(destination):
            os.makedirs(destination)
        
        try:
            shutil.copy(source, destination)
        except FileNotFoundError:
            logger.warning(f"File not found: {source}")

def get_person(graph, user_node, destination):
    user_cluster = graph.nodes[user_node]['cluster']
    user_path = graph.nodes[user_node]['source']
    
    if not os.path.exists(destination):
        os.makedirs(destination)
    
    similar_images = []
    for node, attribute in graph.nodes.items():
        if (attribute['cluster'] == user_cluster) and (attribute['source'] != user_path):
            try:
                shutil.copy(attribute['source'], destination)
                similar_images.append(attribute['source'])
            except FileNotFoundError:
                logger.warning(f"File not found: {attribute['source']}")
    
    return similar_images
