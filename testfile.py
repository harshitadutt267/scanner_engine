from pymongo import MongoClient

uri = "mongodb+srv://harshitadutt267_db_user:Harshitadutt%4027@cluster-engine.o4cj0fm.mongodb.net/scanner_db?retryWrites=true&w=majority"
client = MongoClient(uri)
db = client["scanner_db"]

print("✅ Connected to MongoDB Atlas successfully!")
