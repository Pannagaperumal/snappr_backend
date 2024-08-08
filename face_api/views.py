from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

# from django.conf import settings
from .utils import *
import os
import pickle
import logging
from werkzeug.utils import secure_filename

from .utils import (
    get_image_paths, process_images, draw_graph, chinese_whispers, sort_images, compute_embedding, get_person,UPLOAD_FOLDER,
)


logger = logging.getLogger(__name__)

import os
from .utils import (
    get_image_paths, process_images, draw_graph, chinese_whispers, sort_images, compute_embedding, get_person
)

class UploadFilesView(APIView):
    """
    API view for uploading and processing files.

    This view accepts a list of files and saves them to a specified upload folder.
    It then processes the uploaded images and performs various operations on them.

    Supported HTTP Methods:
        - POST: Uploads and processes the files.

    Request Parameters:
        - files: List of files to be uploaded.

    Optional Request Parameters:
        - threshold: Threshold value for image processing (default: DEFAULT_THRESHOLD).
        - iterations: Number of iterations for image processing (default: DEFAULT_ITERATIONS).

    Returns:
        - If successful, returns a response with a success message.
        - If no files are provided, returns a response with an error message.

    """

    parser_classes = (MultiPartParser, FormParser)
    @swagger_auto_schema(
        operation_description="Upload and process images.",
        manual_parameters=[
            openapi.Parameter(
                name='files',
                in_=openapi.IN_FORM,
                type=openapi.TYPE_FILE,
                description='List of files to upload',
                required=True,
            ),
            openapi.Parameter(
                name='threshold',
                in_=openapi.IN_FORM,
                type=openapi.TYPE_NUMBER,
                description='Threshold value for image processing (default: 0.5)',
                required=False,
            ),
            openapi.Parameter(
                name='iterations',
                in_=openapi.IN_FORM,
                type=openapi.TYPE_INTEGER,
                description='Number of iterations for image processing (default: 10)',
                required=False,
            ),
        ],
        responses={200: "Files uploaded and processed successfully", 400: "No file part"},
        tags=["Face API"]

    )
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
    """
    API view for getting similar images based on a reference image.

    This view accepts a POST request with a reference image file and optional parameters for threshold and iterations.
    It computes the embedding of the reference image, compares it with other embeddings stored in a file,
    and returns a list of similar images based on a graph-based clustering algorithm.

    Parameters:
    - reference_image: The reference image file to compare with.
    - threshold (optional): The threshold value for similarity comparison (default: 0.5).
    - iterations (optional): The number of iterations for the clustering algorithm (default: 10).

    Returns:
    - similar_images: A list of similar images to the reference image.

    If the reference image is not provided or is invalid, an error response is returned.

    Note: This view assumes the presence of the following variables/constants:
    - UPLOAD_FOLDER: The folder path where uploaded images are stored.
    - EMBEDDINGS_FILE: The file path where embeddings are stored.
    - SORTED_FOLDER: The folder path where sorted images will be saved.
    - DEFAULT_THRESHOLD: The default threshold value for similarity comparison.
    - DEFAULT_ITERATIONS: The default number of iterations for the clustering algorithm.
    """

    parser_classes = (MultiPartParser, FormParser)
    @swagger_auto_schema(
        operation_description="Get similar images based on a reference image.",
        manual_parameters=[
            openapi.Parameter(
                name='reference_image',
                in_=openapi.IN_FORM,
                type=openapi.TYPE_FILE,
                description='The reference image file',
                required=True,
            ),
            openapi.Parameter(
                name='threshold',
                in_=openapi.IN_FORM,
                type=openapi.TYPE_NUMBER,
                description='Threshold value for similarity comparison (default: 0.5)',
                required=False,
            ),
            openapi.Parameter(
                name='iterations',
                in_=openapi.IN_FORM,
                type=openapi.TYPE_INTEGER,
                description='Number of iterations for clustering (default: 10)',
                required=False,
            ),
        ],
        responses={200: "Similar images retrieved successfully", 400: "No reference image provided"},
        tags=["Face API"]

    )
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
