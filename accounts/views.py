# views.py

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.hashers import make_password, check_password
from .models import User
import json

@csrf_exempt
def signup(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        username = data['username']
        email = data['email']
        password = make_password(data['password'])
        
        if User.find_by_username(username):
            return JsonResponse({'error': 'Username already exists.'}, status=400)
        
        if User.find_by_email(email):
            return JsonResponse({'error': 'Email already exists.'}, status=400)
        
        user = User(username=username, email=email, password=password)
        user.save()
        
        return JsonResponse({'message': 'User created successfully.'}, status=201)
    else:
        return JsonResponse({'error': 'Method not allowed.'}, status=405)

@csrf_exempt
def login(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        username = data['username']
        password = data['password']
        
        user_data = User.find_by_username(username)
        
        if user_data and check_password(password, user_data['password']):
            return JsonResponse({'message': 'Login successful.'}, status=200)
        else:
            return JsonResponse({'error': 'Invalid credentials.'}, status=401)
    else:
        return JsonResponse({'error': 'Method not allowed.'}, status=405)
