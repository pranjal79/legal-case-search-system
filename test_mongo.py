from pymongo import MongoClient
from datetime import datetime

# Connect to MongoDB
client = MongoClient('mongodb://localhost:27017/')

# Create database
db = client['legal_cases']

# Create collection
cases_collection = db['cases']

# Insert a test case
test_case = {
    'title': 'Test Case v. Example',
    'court': 'Supreme Court',
    'date': datetime.now(),
    'summary': 'This is a test case for our legal search system',
    'status': 'test'
}

# Insert
result = cases_collection.insert_one(test_case)
print(f"✅ Test case inserted with ID: {result.inserted_id}")

# Retrieve
found_case = cases_collection.find_one({'status': 'test'})
print(f"✅ Found case: {found_case['title']}")

# Count
count = cases_collection.count_documents({'status': 'test'})
print(f"✅ Total test cases: {count}")

# Clean up - delete test case
cases_collection.delete_one({'_id': result.inserted_id})
print("✅ Test case deleted. MongoDB connection successful!")

client.close()