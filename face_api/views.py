from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status
# from django.conf import settings
from .utils import *
import os
import pickle
import logging
from werkzeug.utils import secure_filename

from .mongodb_utils import save_image_to_gridfs, get_image_from_gridfs, save_embeddings_to_mongo, get_embeddings_from_mongo
from .utils import (
    get_image_paths, process_images, draw_graph, chinese_whispers, sort_images, compute_embedding, get_person,UPLOAD_FOLDER,
)


logger = logging.getLogger(__name__)

import os
from .mongodb_utils import save_image_to_gridfs, get_image_from_gridfs, save_embeddings_to_mongo, get_embeddings_from_mongo
from .utils import (
    get_image_paths, process_images, draw_graph, chinese_whispers, sort_images, compute_embedding, get_person
)

class UploadFilesView(APIView):
    parser_classes = (MultiPartParser, FormParser)

    def post(self, request, *args, **kwargs):
        files = request.FILES.getlist('files')
        if not files:
            return Response({"error": "No file part"}, status=status.HTTP_400_BAD_REQUEST)

        for file in files:
            filename = secure_filename(file.name)
            file_path = os.path.join(settings.UPLOAD_FOLDER, filename)
            with open(file_path, 'wb+') as destination:
                for chunk in file.chunks():
                    destination.write(chunk)

        image_paths = get_image_paths(settings.UPLOAD_FOLDER)
        data = process_images(image_paths)

        # Save embeddings to MongoDB
        save_embeddings_to_mongo(data)

        # Save images to GridFS
        for entry in data:
            file_id = save_image_to_gridfs(entry['path'], os.path.basename(entry['path']))
            entry['file_id'] = file_id

        threshold = float(request.data.get('threshold', settings.DEFAULT_THRESHOLD))
        iterations = int(request.data.get('iterations', settings.DEFAULT_ITERATIONS))

        G = draw_graph(data, threshold)
        G = chinese_whispers(G, iterations)
        sort_images(G)

        return Response({"message": "Files uploaded and processed successfully"}, status=status.HTTP_200_OK)


class GetImagesView(APIView):
    parser_classes = (MultiPartParser, FormParser)

    def post(self, request, *args, **kwargs):
        reference_image = request.FILES.get('reference_image')
        if not reference_image:
            return Response({"error": "No reference image provided"}, status=status.HTTP_400_BAD_REQUEST)

        reference_path = os.path.join(settings.UPLOAD_FOLDER, secure_filename(reference_image.name))
        with open(reference_path, 'wb+') as destination:
            for chunk in reference_image.chunks():
                destination.write(chunk)

        reference_embedding = compute_embedding(reference_path, facenet_model)

        if reference_embedding is None or reference_embedding.shape[0] != 1:
            return Response({"error": "Invalid reference image"}, status=status.HTTP_400_BAD_REQUEST)

        data = get_embeddings_from_mongo()
        data.append({"path": reference_path, "embedding": reference_embedding[0]})

        threshold = float(request.data.get('threshold', settings.DEFAULT_THRESHOLD))
        iterations = int(request.data.get('iterations', settings.DEFAULT_ITERATIONS))

        G = draw_graph(data, threshold)
        G = chinese_whispers(G, iterations)

        reference_node = len(data)
        destination = os.path.join(settings.SORTED_FOLDER, "reference_matches")
        similar_images = get_person(G, reference_node, destination)

        # Fetch similar images from GridFS
        similar_images_files = [get_image_from_gridfs(entry['file_id']) for entry in similar_images if 'file_id' in entry]

        return Response({"similar_images": similar_images_files}, status=status.HTTP_200_OK)
