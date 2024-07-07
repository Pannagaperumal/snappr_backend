# api/views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework import status
from django.conf import settings
from werkzeug.utils import secure_filename
import logging

logger = logging.getLogger(__name__)


import os
from .utils import *

class UploadFilesView(APIView):
    parser_classes = (MultiPartParser, FormParser)

    def post(self, request, *args, **kwargs):
        files = request.FILES.getlist('files')
        if not files:
            return Response({"error": "No file part"}, status=status.HTTP_400_BAD_REQUEST)

        for file in files:
            filename = secure_filename(file.name)
            file_path = os.path.join(UPLOAD_FOLDER, filename)
            with open(file_path, 'wb+') as destination:
                for chunk in file.chunks():
                    destination.write(chunk)

        image_paths = get_image_paths(UPLOAD_FOLDER)
        data = process_images(image_paths)

        threshold = float(request.data.get('threshold', DEFAULT_THRESHOLD))
        iterations = int(request.data.get('iterations', DEFAULT_ITERATIONS))

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

        reference_path = os.path.join(UPLOAD_FOLDER, secure_filename(reference_image.name))
        with open(reference_path, 'wb+') as destination:
            for chunk in reference_image.chunks():
                destination.write(chunk)

        reference_embedding = compute_embedding(reference_path, facenet_model)

        if reference_embedding is None or reference_embedding.shape[0] != 1:
            return Response({"error": "Invalid reference image"}, status=status.HTTP_400_BAD_REQUEST)

        with open(EMBEDDINGS_FILE, "rb") as f:
            data = pickle.load(f)

        data.append({"path": reference_path, "embedding": reference_embedding[0]})

        threshold = float(request.data.get('threshold', DEFAULT_THRESHOLD))
        iterations = int(request.data.get('iterations', DEFAULT_ITERATIONS))

        G = draw_graph(data, threshold)
        G = chinese_whispers(G, iterations)

        reference_node = len(data)
        destination = os.path.join(SORTED_FOLDER, "reference_matches")
        similar_images = get_person(G, reference_node, destination)

        return Response({"similar_images": similar_images}, status=status.HTTP_200_OK)
