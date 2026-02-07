from src.etl.transform import CaseEmbeddingGenerator
import time
from datetime import datetime

def main():
    """
    Generate embeddings for all 25,000+ cases
    This will take 2-4 hours
    """
    
    print("""
    ╔══════════════════════════════════════════════════════════════╗
    ║     FULL EMBEDDING GENERATION - ALL 25,000+ CASES            ║
    ╚══════════════════════════════════════════════════════════════╝
    """)
    
    
    
    # Confirm
    response = input("Continue? (yes/no): ")
    if response.lower() != 'yes':
        print("Cancelled.")
        return
    
    print(f"\n⏰ Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    start_time = time.time()
    
    # Initialize generator
    generator = CaseEmbeddingGenerator()
    
    # Generate embeddings for ALL cases
    generator.generate_embeddings_batch(
        batch_size=32,       # Process 32 cases at once (optimal for most CPUs)
        limit=None,          # Process ALL cases
        skip_existing=True   # Skip if already done (safe for resuming)
    )
    
    # Verify
    generator.verify_embeddings(sample_size=5)
    
    # Close
    generator.close()
    
    # Calculate time
    end_time = time.time()
    duration = end_time - start_time
    hours = int(duration // 3600)
    minutes = int((duration % 3600) // 60)
    
    print(f"\n⏱️ Total time: {hours}h {minutes}m")
    print(f"⏰ Finished at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("\n✅ All embeddings generated!")
    print("🎯 Ready for semantic search!")

if __name__ == "__main__":
    main()