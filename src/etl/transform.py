import os
from pymongo import MongoClient
from sentence_transformers import SentenceTransformer
import numpy as np
from tqdm import tqdm
from datetime import datetime
from dotenv import load_dotenv
import time

# Load environment variables
load_dotenv()

class CaseEmbeddingGenerator:
    """
    Generate embeddings for legal cases using Sentence-BERT
    Enables semantic search functionality
    """
    
    def __init__(self):
        # MongoDB connection
        mongo_uri = os.getenv('MONGODB_URI', 'mongodb://localhost:27017/')
        db_name = os.getenv('MONGODB_DB', 'legal_cases')
        
        self.client = MongoClient(mongo_uri)
        self.db = self.client[db_name]
        self.cases_collection = self.db['cases']
        
        print(f"✅ Connected to MongoDB: {db_name}")
        
        # Load embedding model
        print("\n📥 Loading Sentence-BERT model...")
        print("   Model: all-MiniLM-L6-v2 (Fast and efficient)")
        print("   This may take 1-2 minutes on first run...")
        
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        # Alternatives: 'all-mpnet-base-v2' (better quality but slower)
        #               'paraphrase-multilingual-MiniLM-L12-v2' (for Hindi text)
        
        print("✅ Model loaded successfully!")
        
        self.embedding_dim = 384  # Dimension of all-MiniLM-L6-v2
        
        # Statistics
        self.stats = {
            'total': 0,
            'processed': 0,
            'skipped': 0,
            'failed': 0,
            'start_time': None,
            'end_time': None
        }
    
    def generate_embeddings_batch(self, batch_size=32, limit=None, skip_existing=True):
        """
        Generate embeddings for all cases in batches
        
        Args:
            batch_size (int): Number of cases to process at once
            limit (int): Limit number of cases (None for all)
            skip_existing (bool): Skip cases that already have embeddings
        """
        print("\n" + "="*70)
        print("EMBEDDING GENERATION PIPELINE")
        print("="*70)
        
        # Query for cases without embeddings (if skip_existing)
        if skip_existing:
            query = {"embedding": {"$exists": False}}
            print("📊 Mode: Processing only cases without embeddings")
        else:
            query = {}
            print("📊 Mode: Regenerating all embeddings")
        
        # Count total cases to process
        total_cases = self.cases_collection.count_documents(query)
        
        if limit:
            total_cases = min(total_cases, limit)
        
        self.stats['total'] = total_cases
        self.stats['start_time'] = datetime.now()
        
        print(f"📊 Total cases to process: {total_cases:,}")
        print(f"📦 Batch size: {batch_size}")
        print(f"⏰ Started at: {self.stats['start_time'].strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*70 + "\n")
        
        if total_cases == 0:
            print("✅ All cases already have embeddings!")
            return
        
        # Process in batches
        cursor = self.cases_collection.find(query).limit(limit) if limit else self.cases_collection.find(query)
        
        batch_texts = []
        batch_ids = []
        
        with tqdm(total=total_cases, desc="Generating embeddings", unit="case") as pbar:
            for case in cursor:
                try:
                    # Get text to embed
                    text = self._prepare_text_for_embedding(case)
                    
                    if not text or len(text.strip()) < 50:
                        self.stats['skipped'] += 1
                        pbar.update(1)
                        continue
                    
                    batch_texts.append(text)
                    batch_ids.append(case['_id'])
                    
                    # Process batch when full
                    if len(batch_texts) >= batch_size:
                        self._process_batch(batch_texts, batch_ids)
                        batch_texts = []
                        batch_ids = []
                        pbar.update(batch_size)
                
                except Exception as e:
                    self.stats['failed'] += 1
                    print(f"\n❌ Error processing case {case.get('case_id', 'unknown')}: {e}")
                    pbar.update(1)
            
            # Process remaining cases
            if batch_texts:
                self._process_batch(batch_texts, batch_ids)
                pbar.update(len(batch_texts))
        
        self.stats['end_time'] = datetime.now()
        self._print_statistics()
        
        # Create index for faster similarity search
        self._create_embedding_index()
    
    def _prepare_text_for_embedding(self, case):
        """
        Prepare text from case document for embedding
        Combines title, summary, and key portions of judgment
        """
        parts = []##Creates empty container
        
        # Add title (weighted more)
        title = case.get('title', '')
        if title and title != 'Unknown':
            parts.append(f"{title}. {title}. {title}.")  # Repeat for emphasis
        
        # Add summary if exists
        summary = case.get('summary', '')
        if summary:
            parts.append(summary)
        
        # Add main judgment text (truncated to avoid very long texts)
        text = case.get('cleaned_text') or case.get('judgment_text', '')
        if text:
            # Take first 2000 words (balance between context and speed)
            words = text.split()[:2000]
            parts.append(' '.join(words))
        
        # Add metadata for better matching
        court = case.get('court', '')
        if court:
            parts.append(f"Court: {court}")
        
        # Combine all parts
        combined_text = ' '.join(parts)
        
        # Truncate to model's max length (512 tokens ≈ 2000 characters for safety)
        if len(combined_text) > 5000:
            combined_text = combined_text[:5000]
        
        return combined_text
    
    def _process_batch(self, texts, case_ids):
        """
        Generate embeddings for a batch of texts and save to MongoDB
        """
        try:
            # Generate embeddings
            embeddings = self.model.encode(
                texts,
                batch_size=len(texts),
                show_progress_bar=False,
                convert_to_numpy=True
            )
            
            # Save to MongoDB
            for case_id, embedding in zip(case_ids, embeddings):
                self.cases_collection.update_one(
                    {'_id': case_id},
                    {
                        '$set': {
                            'embedding': embedding.tolist(),
                            'embedding_model': 'all-MiniLM-L6-v2',
                            'embedding_dim': self.embedding_dim,
                            'embedding_generated_at': datetime.now()
                        }
                    }
                )
            
            self.stats['processed'] += len(texts)
            
        except Exception as e:
            print(f"\n❌ Batch processing error: {e}")
            self.stats['failed'] += len(texts)
    
    def _create_embedding_index(self):
        """
        Create index on case_id for faster lookups
        (Vector indexes for similarity search will be created later)
        """
        print("\n🔧 Creating database indexes...")
        try:
            self.cases_collection.create_index('case_id')
            self.cases_collection.create_index('embedding_generated_at')
            print("✅ Indexes created successfully")
        except Exception as e:
            print(f"⚠️ Index creation warning: {e}")
    
    def _print_statistics(self):
        """
        Print generation statistics
        """
        duration = (self.stats['end_time'] - self.stats['start_time']).total_seconds()
        hours = int(duration // 3600)
        minutes = int((duration % 3600) // 60)
        seconds = int(duration % 60)
        
        print("\n" + "="*70)
        print("EMBEDDING GENERATION COMPLETE!")
        print("="*70)
        print(f"📊 Total cases: {self.stats['total']:,}")
        print(f"✅ Successfully processed: {self.stats['processed']:,}")
        print(f"⏭️  Skipped (too short): {self.stats['skipped']:,}")
        print(f"❌ Failed: {self.stats['failed']:,}")
        
        if self.stats['processed'] > 0:
            success_rate = (self.stats['processed'] / self.stats['total']) * 100
            print(f"📈 Success rate: {success_rate:.2f}%")
            
            cases_per_second = self.stats['processed'] / duration if duration > 0 else 0
            print(f"⚡ Speed: {cases_per_second:.2f} cases/second")
        
        print(f"⏱️  Total time: {hours}h {minutes}m {seconds}s")
        print(f"⏰ Finished at: {self.stats['end_time'].strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*70 + "\n")
    
    def verify_embeddings(self, sample_size=5):
        """
        Verify that embeddings were generated correctly
        """
        print("\n🔍 VERIFYING EMBEDDINGS...\n")
        
        # Count cases with embeddings
        total = self.cases_collection.count_documents({})
        with_embeddings = self.cases_collection.count_documents({'embedding': {'$exists': True}})
        
        print(f"📊 Total cases: {total:,}")
        print(f"✅ Cases with embeddings: {with_embeddings:,}")
        print(f"📈 Coverage: {(with_embeddings/total*100):.2f}%")
        
        # Check sample embeddings
        print(f"\n🔬 Checking {sample_size} sample embeddings:\n")
        
        samples = self.cases_collection.find({'embedding': {'$exists': True}}).limit(sample_size)
        
        for i, case in enumerate(samples, 1):
            embedding = case.get('embedding', [])
            print(f"{i}. Case: {case.get('title', 'Unknown')[:50]}...")
            print(f"   Embedding dimension: {len(embedding)}")
            print(f"   Embedding sample: [{embedding[0]:.4f}, {embedding[1]:.4f}, ...]")
            print(f"   Generated: {case.get('embedding_generated_at', 'N/A')}\n")
        
        print("✅ Verification complete!\n")
    
    def close(self):
        """Close MongoDB connection"""
        self.client.close()
        print("✅ MongoDB connection closed")


# Main execution
if __name__ == "__main__":
    print("""
    ╔══════════════════════════════════════════════════════════════╗
    ║        LEGAL CASE EMBEDDING GENERATION PIPELINE              ║
    ║                  Semantic Search Preparation                 ║
    ╚══════════════════════════════════════════════════════════════╝
    """)
    
    # Initialize generator
    generator = CaseEmbeddingGenerator()
    
    # TEST MODE: Process first 100 cases
    print("\n🧪 TEST MODE: Processing first 100 cases")
    print("💡 To process all cases, change limit=None below\n")
    
    # Generate embeddings
    # For testing: limit=100
    # For production: limit=None
    generator.generate_embeddings_batch(
        batch_size=32,      # Process 32 cases at a time
        limit=100,          # Change to None for all cases
        skip_existing=True  # Skip cases that already have embeddings
    )
    
    # Verify embeddings
    generator.verify_embeddings(sample_size=3)
    
    # Close connection
    generator.close()
    
    print("\n✅ Embedding generation complete!")
    print("📁 Embeddings saved in MongoDB")
    print("\n💡 Next step: Build semantic search API")