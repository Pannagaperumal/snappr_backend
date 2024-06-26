# face_api/models.py

import cv2
import os
from django.db import models
from django.conf import settings

class UploadedImage(models.Model):
    image = models.ImageField(upload_to='uploaded_images/')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def detect_faces(self):
        print("Detecting faces for image:", self.image)
        image_path = os.path.join(settings.MEDIA_ROOT, str(self.image))
        if not os.path.exists(image_path):
            print("Image path does not exist:", image_path)
            return

        face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        img = cv2.imread(image_path)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, 1.3, 5)
        
        for (x, y, w, h) in faces:
            face_img = img[y:y+h, x:x+w]
            face_image_path = os.path.join(settings.MEDIA_ROOT, 'face_images', f'face_{self.id}_{x}_{y}.jpg')
            if not os.path.exists(os.path.dirname(face_image_path)):
                os.makedirs(os.path.dirname(face_image_path))
            cv2.imwrite(face_image_path, face_img)
            DetectedFace.objects.create(uploaded_image=self, face_image=f'face_images/face_{self.id}_{x}_{y}.jpg')

class DetectedFace(models.Model):
    uploaded_image = models.ForeignKey(UploadedImage, related_name='detected_faces', on_delete=models.CASCADE)
    face_image = models.ImageField(upload_to='face_images/')
