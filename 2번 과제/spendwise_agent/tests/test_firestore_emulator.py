import os
import unittest
from uuid import uuid4
from unittest.mock import patch

from web_store import FirestoreStore


@unittest.skipUnless(os.getenv("FIRESTORE_EMULATOR_HOST"), "Firestore emulator is not configured")
class FirestoreTests(unittest.TestCase):
    def test_batch_replay_and_persistence(self):
        host = os.environ["FIRESTORE_EMULATOR_HOST"].split(":")[0]
        self.assertIn(host, {"localhost", "127.0.0.1"})
        with patch.dict(os.environ, GOOGLE_CLOUD_PROJECT="demo-spendwise"):
            store = FirestoreStore()
            key = str(uuid4())
            row = dict(id=key, month="2099-12", kind="expense", amount=1000)
            turn = dict(id=key, created_at="2099-12-01", message="fixture")
            self.addCleanup(store.client.collection("data").document(key).delete)
            self.addCleanup(store.client.collection("conversations").document(key).delete)
            self.assertTrue(store.save([(key,row)],turn))
            fresh = FirestoreStore()
            self.assertEqual(fresh.get("conversations",key),turn)
            self.assertIn(row,fresh.rows("data","2099-12"))
            updated = {**row,"amount":2500}
            self.assertFalse(fresh.save([(key,updated)],turn))
            self.assertEqual(store.get("data",key),row)
            fresh.save([(key,updated)])
            self.assertIn(updated,store.rows("data","2099-12"))
