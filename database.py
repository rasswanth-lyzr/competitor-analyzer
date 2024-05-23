import os
import urllib

from dotenv import load_dotenv
from pymongo import MongoClient

# client = MongoClient("mongodb://localhost:27017/")
# db = client['competitor_analysis']
# competitors_list_collection = db['competitors_list']
# base_research_collection = db['base_research']
# metrics_collection = db['metrics']
# news_collection = db['news']

load_dotenv()

MONGO_USER = os.getenv("MONGO_USER")
MONGO_PWD = os.getenv("MONGO_PWD")
MONGO_PWD = urllib.parse.quote(MONGO_PWD)

uri = f"mongodb+srv://{MONGO_USER}:{MONGO_PWD}@cluster0.dx1ictn.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"

client = MongoClient(uri)

db = client["competitor_analysis"]
competitors_list_collection = db["competitors_list"]
base_research_collection = db["base_research"]
metrics_collection = db["metrics"]
news_collection = db["news"]
