from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from src.models.search import LegalCaseSearch

# Initialize FastAPI
app = FastAPI(
    title="Legal Case Search API",
    description="Semantic search API for Indian Supreme Court cases",
    version="1.0.0"
)

# CORS middleware (allows frontend to access API)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize search engine
search_engine = None

@app.on_event("startup")
async def startup_event():
    """Initialize search engine on startup"""
    global search_engine
    print("🚀 Starting Legal Case Search API...")
    search_engine = LegalCaseSearch()
    print("✅ API Ready!")

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    if search_engine:
        search_engine.close()
    print("👋 API Shutdown")

# Request/Response Models
class SearchRequest(BaseModel):
    query: str
    top_k: int = 10
    court: Optional[str] = None

class SearchResult(BaseModel):
    case_id: str
    title: str
    court: str
    date: Optional[str]
    similarity_score: float
    similarity_percentage: str
    summary: str
    citations: List[str]
    petitioner: str
    respondent: str

class SearchResponse(BaseModel):
    query: str
    total_results: int
    results: List[SearchResult]

# API Endpoints
@app.get("/")
async def root():
    """Root endpoint - API information"""
    return {
        "message": "Legal Case Search API",
        "version": "1.0.0",
        "total_cases": "26,604 Supreme Court cases",
        "endpoints": {
            "/search": "Search for similar cases",
            "/case/{case_id}": "Get case details",
            "/similar/{case_id}": "Find similar cases",
            "/stats": "Get system statistics",
            "/docs": "API documentation (Swagger UI)",
            "/health": "Health check"
        }
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "search_engine": "initialized" if search_engine else "not initialized",
        "database": "connected"
    }

@app.get("/stats")
async def get_statistics():
    """Get system statistics"""
    if not search_engine:
        raise HTTPException(status_code=500, detail="Search engine not initialized")
    
    stats = search_engine.get_statistics()
    return stats

@app.post("/search", response_model=SearchResponse)
async def search_cases(request: SearchRequest):
    """
    Search for similar legal cases using semantic search
    
    Args:
        query: Natural language search query
        top_k: Number of results to return (default: 10)
        court: Optional court filter
    
    Returns:
        Search results with similarity scores
    """
    if not search_engine:
        raise HTTPException(status_code=500, detail="Search engine not initialized")
    
    try:
        filters = {}
        if request.court:
            filters['court'] = {'$regex': request.court, '$options': 'i'}
        
        results = search_engine.search_similar_cases(
            query=request.query,
            top_k=request.top_k,
            filters=filters if filters else None
        )
        
        return {
            "query": request.query,
            "total_results": len(results),
            "results": results
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/search")
async def search_cases_get(
    q: str = Query(..., description="Search query", example="employment termination"),
    top_k: int = Query(10, description="Number of results", ge=1, le=50),
    court: Optional[str] = Query(None, description="Court filter", example="Supreme Court")
):
    """
    Search for similar legal cases (GET method for easy browser testing)
    
    Example: /search?q=property dispute&top_k=5
    """
    request = SearchRequest(query=q, top_k=top_k, court=court)
    return await search_cases(request)

@app.get("/case/{case_id}")
async def get_case_details(case_id: str):
    """
    Get full details of a specific case
    
    Args:
        case_id: Unique case identifier
    
    Returns:
        Complete case information
    """
    if not search_engine:
        raise HTTPException(status_code=500, detail="Search engine not initialized")
    
    case = search_engine.get_case_details(case_id)
    
    if not case:
        raise HTTPException(status_code=404, detail=f"Case {case_id} not found")
    
    return case

@app.get("/similar/{case_id}")
async def find_similar_cases(
    case_id: str,
    top_k: int = Query(10, description="Number of results", ge=1, le=50)
):
    """
    Find cases similar to a specific case
    
    Args:
        case_id: Case to find similar cases for
        top_k: Number of results
    
    Returns:
        List of similar cases with similarity scores
    """
    if not search_engine:
        raise HTTPException(status_code=500, detail="Search engine not initialized")
    
    try:
        results = search_engine.search_by_case_id(case_id, top_k)
        
        if not results:
            raise HTTPException(
                status_code=404, 
                detail=f"No similar cases found for {case_id}"
            )
        
        return {
            "source_case_id": case_id,
            "total_results": len(results),
            "results": results
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Run the API
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)