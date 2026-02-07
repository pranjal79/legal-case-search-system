import numpy as np
from pymongo import MongoClient
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import os
from dotenv import load_dotenv
from config_loader import load_config
load_dotenv()


class LegalCaseSearch:
    """
    Semantic search for legal cases using embeddings
    """

    def __init__(self):
        config = load_config()

        mongo_uri = os.getenv(
            "MONGODB_URI",
             config["mongodb"]["uri"]
        )

        db_name = os.getenv(
            "MONGODB_DB",
            config["mongodb"]["database"]
        )
        self.client = MongoClient(mongo_uri)
        self.db = self.client[db_name]
        self.cases_collection = self.db["cases"]

        print(f"✅ Connected to MongoDB: {db_name}")

        print("📥 Loading search model...")
        self.model = SentenceTransformer(
            config["nlp"]["embedding_model"]
        )
        print("✅ Model loaded!")

    # --------------------------------------------------
    # MAIN SEARCH
    # --------------------------------------------------
    def search_similar_cases(self, query, top_k=10, filters=None):
        print(f"\n🔍 Searching for: '{query}'")
        print(f"📊 Returning top {top_k} results\n")

        query_embedding = self.model.encode(query, convert_to_numpy=True)

        mongo_query = {"embedding": {"$exists": True}}
        if filters:
            mongo_query.update(filters)

        cases = list(self.cases_collection.find(mongo_query))

        if not cases:
            print("❌ No cases found with embeddings!")
            return []

        print(f"📚 Searching through {len(cases):,} cases...")

        case_embeddings = np.array([case["embedding"] for case in cases])
        similarities = cosine_similarity([query_embedding], case_embeddings)[0]

        top_indices = np.argsort(similarities)[::-1][:top_k]

        results = []
        for idx in top_indices:
            case = cases[idx]
            score = float(similarities[idx])

            result = {
                "case_id": case.get("case_id"),
                "title": case.get("title", "Unknown"),
                "court": case.get("court", "Unknown"),
                "date": case.get("date"),
                "summary": self._create_summary(case),
                "citations": case.get("citations", [])[:5],
                "petitioner": case.get("petitioner", ""),
                "respondent": case.get("respondent", ""),
                "similarity_score": score,
                "similarity_percentage": f"{score * 100:.2f}%",
            }

            results.append(result)

        return results

    # --------------------------------------------------
    # SUMMARY
    # --------------------------------------------------
    def _create_summary(self, case, max_words=200):
        text = case.get("cleaned_text") or case.get("judgment_text", "")

        if not text:
            return "No summary available"

        words = text.split()[:max_words]
        summary = " ".join(words)

        if len(text.split()) > max_words:
            summary += "..."

        return summary

    # --------------------------------------------------
    # SEARCH BY CASE ID
    # --------------------------------------------------
    def search_by_case_id(self, case_id, top_k=10):
        source_case = self.cases_collection.find_one({"case_id": case_id})

        if not source_case or "embedding" not in source_case:
            return []

        query_embedding = np.array(source_case["embedding"])

        cases = list(
            self.cases_collection.find(
                {"embedding": {"$exists": True}, "case_id": {"$ne": case_id}}
            )
        )

        if not cases:
            return []

        case_embeddings = np.array([case["embedding"] for case in cases])
        similarities = cosine_similarity([query_embedding], case_embeddings)[0]

        top_indices = np.argsort(similarities)[::-1][:top_k]

        results = []
        for idx in top_indices:
            case = cases[idx]
            score = float(similarities[idx])

            result = {
                "case_id": case.get("case_id"),
                "title": case.get("title", "Unknown"),
                "court": case.get("court", "Unknown"),
                "date": case.get("date"),
                "summary": self._create_summary(case),
                "citations": case.get("citations", [])[:5],
                "similarity_score": score,
                "similarity_percentage": f"{score * 100:.2f}%",
            }

            results.append(result)

        return results

    # --------------------------------------------------
    # ADVANCED SEARCH
    # --------------------------------------------------
    def advanced_search(self, query, court=None, year_from=None, year_to=None, top_k=10):
        filters = {}
        if court:
            filters["court"] = {"$regex": court, "$options": "i"}
        return self.search_similar_cases(query, top_k, filters)

    # --------------------------------------------------
    # CASE DETAILS
    # --------------------------------------------------
    def get_case_details(self, case_id):
        case = self.cases_collection.find_one({"case_id": case_id})
        if not case:
            return None

        case.pop("embedding", None)
        if "_id" in case:
            case["_id"] = str(case["_id"])

        return case

    # --------------------------------------------------
    # STATISTICS
    # --------------------------------------------------
    def get_statistics(self):
        total_cases = self.cases_collection.count_documents({})
        cases_with_embeddings = self.cases_collection.count_documents(
            {"embedding": {"$exists": True}}
        )

        return {
            "total_cases": total_cases,
            "searchable_cases": cases_with_embeddings,
            "coverage_percentage": f"{(cases_with_embeddings / total_cases * 100):.2f}%",
            "embedding_model": "all-MiniLM-L6-v2",
            "embedding_dimension": 384,
        }

    def close(self):
        self.client.close()
