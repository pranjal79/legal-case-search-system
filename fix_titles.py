from pymongo import MongoClient
import re
from tqdm import tqdm

def fix_titles_from_summary():
    """
    Extract better titles from case summaries
    """
    client = MongoClient('mongodb://localhost:27017/')
    db = client['legal_cases']
    cases = db['cases']
    
    # Find cases with "Unknown" title
    unknown_cases = cases.find({'title': 'Unknown'})
    count = cases.count_documents({'title': 'Unknown'})
    
    print(f"📊 Found {count:,} cases with 'Unknown' title")
    print("🔧 Extracting titles from summaries...\n")
    
    fixed = 0
    
    for case in tqdm(unknown_cases, total=count, desc="Fixing titles"):
        summary = case.get('summary', '') or case.get('cleaned_text', '')[:500]
        
        # Try to extract title from summary
        # Pattern: "Name vs Name on Date"
        pattern = r'^(.+?)\s+(?:vs?\.?|versus)\s+(.+?)\s+on\s+\d'
        match = re.search(pattern, summary, re.IGNORECASE)
        
        if match:
            petitioner = match.group(1).strip()
            respondent = match.group(2).strip()
            
            # Clean up
            petitioner = petitioner.replace('...', '').strip()
            respondent = respondent.replace('Ors.', 'Others').strip()
            
            new_title = f"{petitioner} vs {respondent}"
            
            # Update in MongoDB
            cases.update_one(
                {'_id': case['_id']},
                {'$set': {'title': new_title}}
            )
            
            fixed += 1
    
    print(f"\n✅ Fixed {fixed:,} titles!")
    print(f"⏭️  Remaining 'Unknown': {count - fixed:,}")
    
    client.close()

if __name__ == "__main__":
    fix_titles_from_summary()