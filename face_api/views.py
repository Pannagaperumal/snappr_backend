# face_api/views.py

from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from .models import UploadedImage, DetectedFace
from snappr_backend import settings
import os
import cv2

@api_view(['POST'])
def upload_images(request):
    uploaded_files = request.FILES.getlist('images')
    print("Received files:", uploaded_files)
    
    if not uploaded_files:
        return Response({"error": "No files uploaded"}, status=status.HTTP_400_BAD_REQUEST)
    
    for uploaded_file in uploaded_files:
        uploaded_image = UploadedImage.objects.create(image=uploaded_file)
        print("Created UploadedImage:", uploaded_image)
        uploaded_image.detect_faces()
    
    return Response(status=status.HTTP_201_CREATED)

@api_view(['POST'])
def search_by_reference_face(request):
    reference_image = request.FILES['reference_image']

    # Save the reference image temporarily
    reference_image_path = os.path.join(settings.MEDIA_ROOT, 'reference.jpg')
    with open(reference_image_path, 'wb+') as temp_file:
        for chunk in reference_image.chunks():
            temp_file.write(chunk)

    # Perform face detection on the reference image
    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
    ref_img = cv2.imread(reference_image_path)
    ref_gray = cv2.cvtColor(ref_img, cv2.COLOR_BGR2GRAY)
    ref_faces = face_cascade.detectMultiScale(ref_gray, 1.3, 5)

    if len(ref_faces) == 0:
        return Response({"error": "No face detected in reference image"}, status=status.HTTP_400_BAD_REQUEST)

    (x, y, w, h) = ref_faces[0]
    ref_face_img = ref_img[y:y+h, x:x+w]

    matched_images = []
    for detected_face in DetectedFace.objects.all():
        detected_face_img_path = os.path.join(settings.MEDIA_ROOT, str(detected_face.face_image))
        detected_face_img = cv2.imread(detected_face_img_path)

        if detected_face_img is None:
            continue  # Skip if the image couldn't be read

        detected_gray = cv2.cvtColor(detected_face_img, cv2.COLOR_BGR2GRAY)
        detected_faces = face_cascade.detectMultiScale(detected_gray, 1.3, 5)

        if len(detected_faces) == 0:
            continue  # Skip if no face is detected in the database image

        (dx, dy, dw, dh) = detected_faces[0]
        detected_face_region = detected_face_img[dy:dy+dh, dx:dx+dw]

        if detected_face_region.shape == ref_face_img.shape:
            difference = cv2.subtract(detected_face_region, ref_face_img)
            if not np.any(difference):
                matched_images.append(detected_face.uploaded_image.url)
            else:
                print(f"Faces did not match: {detected_face_img_path}")
        else:
            print(f"Shapes did not match: {detected_face_img_path}")

    if not matched_images:
        print("No matched images found")

    return Response(matched_images, status=status.HTTP_200_OK)


