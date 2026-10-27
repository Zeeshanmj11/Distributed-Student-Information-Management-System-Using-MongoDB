
from pymongo import MongoClient

# Connect to the three MongoDB servers
servers = {
    "Bengaluru": "mongodb://127.0.0.1:27017/",
    "Mysuru": "mongodb://127.0.0.1:27018/",
    "Backup": "mongodb://127.0.0.1:27019/"
}

clients = {}

try:
    for name, uri in servers.items():
        client = MongoClient(
            uri,
            serverSelectionTimeoutMS=3000
        )

        # Test the connection
        client.admin.command("ping")

        clients[name] = client
        print(f"{name} server connected successfully!")

    print("\nAll three MongoDB servers are working correctly.")

except Exception as error:
    print("\nConnection failed:", error)

finally:
    for client in clients.values():
        client.close()