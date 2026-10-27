
from pymongo import MongoClient
from pymongo.errors import PyMongoError

servers = {
    "Bengaluru": "mongodb://127.0.0.1:27017/",
    "Mysuru": "mongodb://127.0.0.1:27018/",
    "Backup": "mongodb://127.0.0.1:27019/"
}

for name, uri in servers.items():
    client = MongoClient(uri, serverSelectionTimeoutMS=2000)

    try:
        client.admin.command("ping")
        print(f"{name}: SERVER AVAILABLE")
    except PyMongoError:
        print(f"{name}: SERVER UNAVAILABLE")
    finally:
        client.close()