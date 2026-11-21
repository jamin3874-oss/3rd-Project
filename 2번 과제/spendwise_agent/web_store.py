import os
from functools import lru_cache
from threading import RLock


class MemoryStore:
    def __init__(self):
        self.docs = {"data": {}, "conversations": {}}
        self.lock = RLock()

    def rows(self, collection, month=None, recent=None):
        with self.lock:
            rows = list(self.docs[collection].values())
        if month:
            rows = [row for row in rows if row["month"] == month]
        if recent:
            return sorted(rows, key=lambda row: row["created_at"], reverse=True)[:recent]
        return rows

    def get(self, collection, key):
        with self.lock:
            return self.docs[collection].get(key)

    def save(self, changes, turn=None):
        with self.lock:
            if turn and turn["id"] in self.docs["conversations"]:
                return False
            for key, row in changes:
                self.docs["data"][key] = row
            if turn:
                self.docs["conversations"][turn["id"]] = turn
            return True


class FirestoreStore:
    def __init__(self):
        from google.cloud import firestore
        self.client = firestore.Client(project=os.environ["GOOGLE_CLOUD_PROJECT"])

    def rows(self, collection, month=None, recent=None):
        from google.cloud.firestore_v1.base_query import FieldFilter
        query = self.client.collection(collection)
        if month:
            query = query.where(filter=FieldFilter("month", "==", month))
        if recent:
            query = query.order_by("created_at", direction="DESCENDING").limit(recent)
        return [doc.to_dict() for doc in query.stream()]

    def get(self, collection, key):
        return self.client.collection(collection).document(key).get().to_dict()

    def save(self, changes, turn=None):
        from google.api_core.exceptions import AlreadyExists
        batch = self.client.batch()
        for key, row in changes:
            batch.set(self.client.collection("data").document(key), row)
        if turn:
            batch.create(self.client.collection("conversations").document(turn["id"]), turn)
        try:
            batch.commit()
        except AlreadyExists:
            if turn:
                return False
            raise
        return True


@lru_cache
def get_store():
    if os.getenv("SPENDWISE_STORE") == "memory":
        return MemoryStore()
    return FirestoreStore()
