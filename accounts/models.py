from django.db import models

# Create your models here.
# models.py

from pymongo import MongoClient
from django.conf import settings

client = MongoClient(settings.MONGO_DB['CLIENT']['host'], 
                     settings.MONGO_DB['CLIENT']['port'])
db = client[settings.MONGO_DB['NAME']]

class User:
    def __init__(self, username, email, password):
        self.username = username
        self.email = email
        self.password = password
    
    def save(self):
        db.users.insert_one({
            'username': self.username,
            'email': self.email,
            'password': self.password
            # Add more custom fields as needed
        })

    @staticmethod
    def find_by_username(username):
        return db.users.find_one({'username': username})

    @staticmethod
    def find_by_email(email):
        return db.users.find_one({'email': email})
