from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth.hashers import make_password, check_password
from .models import User
import jwt
import datetime
from django.conf import settings
import json
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

class SignupView(APIView):
    @swagger_auto_schema(
        operation_description="Sign up a new user.",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'username': openapi.Schema(type=openapi.TYPE_STRING, description='Username for the new user'),
                'email': openapi.Schema(type=openapi.TYPE_STRING, description='Email for the new user'),
                'password': openapi.Schema(type=openapi.TYPE_STRING, description='Password for the new user'),
            },
            required=['username', 'email', 'password'],
        ),
        responses={
            201: "User created successfully",
            400: "Username or email already exists",
        },
        tags=["Auth API"]
    )
    def post(self, request):
        data = request.data
        username = data['username']
        email = data['email']
        password = make_password(data['password'])
        
        if User.find_by_username(username):
            return Response({'error': 'Username already exists.'}, status=status.HTTP_400_BAD_REQUEST)
        
        if User.find_by_email(email):
            return Response({'error': 'Email already exists.'}, status=status.HTTP_400_BAD_REQUEST)
        
        user = User(username=username, email=email, password=password)
        user.save()
        
        return Response({'message': 'User created successfully.'}, status=status.HTTP_201_CREATED)


class LoginView(APIView):
    @swagger_auto_schema(
            operation_description="Log in an existing user.",
            request_body=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'username': openapi.Schema(type=openapi.TYPE_STRING, description='Username of the user'),
                    'password': openapi.Schema(type=openapi.TYPE_STRING, description='Password of the user'),
                },
                required=['username', 'password'],
            ),
            responses={
                200: "Login successful with JWT token",
                401: "Invalid credentials",
            },
            tags=["Auth API"]
        )
    def post(self, request):
        data = request.data
        username = data['username']
        password = data['password']
        
        user_data = User.find_by_username(username)
        
        if user_data and check_password(password, user_data['password']):
            # Create JWT token
            payload = {
                'username': user_data['username'],
                'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=24),
                'iat': datetime.datetime.utcnow()
            }
            token = jwt.encode(payload, "udgyfiudsyfgidusyfg", algorithm='HS256')

            return Response({'username': username, 'token': token, 'message': 'Login successful.'}, status=status.HTTP_200_OK)

        return Response({'error': 'Invalid credentials.'}, status=status.HTTP_401_UNAUTHORIZED)
