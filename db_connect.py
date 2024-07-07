import pymongo

url = "mongodb+srv://admin_snappr:3QXicaeVRNhrw5a@cluster0.iy3i2dt.mongodb.net/"

try:
    # Attempt to connect to MongoDB
    client = pymongo.MongoClient(url)

    # Access your database (replace 'mydatabase' with your database name)
    db = client['admin_snappr']

    # Create a collection (replace 'mycollection' with your desired collection name)
    collection = db['Users']

    # Insert a document to ensure collection creation
    collection.insert_one({"example": "data"})

    print("Connected to MongoDB successfully!")
except pymongo.errors.ConnectionFailure as e:
    print(f"Error connecting to MongoDB: {e}")