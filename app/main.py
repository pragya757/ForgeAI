import os
from typing import Optional, List, Dict, Any
from fastapi import FastAPI, HTTPException, File, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from app.config import settings
from app.llm import get_llm_client
from app.tools.registry import registry
from app.retrieval.ingestion import IngestionManager
from app.factory.pipeline import ForgeAIFactory
from app.runtime.chat_runner import GenericChatRunner

app = FastAPI(
    title="ForgeAI - Autonomous AI Agent Factory API",
    version="1.0.0",
    description="Generic factory pipeline that autonomously designs, evaluates, refines, and serves AI agents."
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class BuildRequest(BaseModel):
    brief: str
    doc_folder: str
    output_dir: str
    max_iterations: int = 3
    clarification_answers: Optional[Dict[str, str]] = None

class ChatRequest(BaseModel):
    definition_path: str
    query: str
    doc_folder: Optional[str] = None

@app.get("/health")
def health_check():
    try:
        llm = get_llm_client()
        available, msg = llm.is_available()
    except Exception as e:
        available, msg = False, str(e)

    return {
        "status": "healthy",
        "llm_provider": settings.llm_provider,
        "llm_available": available,
        "llm_status": msg,
        "available_tools": registry.list_tools()
    }

@app.get("/tools")
def get_tools():
    return {
        "tools": registry.get_definitions()
    }

@app.post("/api/factory/build")
def build_agent_endpoint(req: BuildRequest):
    if not os.path.exists(req.doc_folder):
        raise HTTPException(status_code=400, detail=f"Document folder not found: {req.doc_folder}")

    try:
        factory = ForgeAIFactory(max_iterations=req.max_iterations)
        results = factory.build_agent(
            brief=req.brief,
            doc_folder=req.doc_folder,
            output_dir=req.output_dir,
            clarification_answers=req.clarification_answers,
            unattended=True
        )
        return {
            "status": "success",
            "agent_name": results["requirements"].agent_name,
            "pass_rate": results["scorecards"][-1].pass_rate if results["scorecards"] else 0.0,
            "output_dir": req.output_dir
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Factory execution error: {str(e)}")

@app.post("/api/factory/upload-and-build")
async def upload_and_build_endpoint(
    brief: str = Form(..., description="Natural language brief describing the agent"),
    iterations: int = Form(3, description="Maximum optimization iterations (1-3)"),
    files: List[UploadFile] = File(..., description="List of documents to ingest (PDF, TXT, CSV, MD)"),
    session_id: Optional[str] = Form(None, description="Optional custom session identifier")
):
    """
    Universal Multipart Upload and Agent Build Endpoint
    - Accepts arbitrary user brief and uploaded documents (.pdf, .txt, .csv, .md)
    - Validates files and saves them to an isolated session directory
    - Generates SHA-256 manifest and executes full autonomous factory pipeline
    - Returns complete agent metadata and evaluation scorecard summary
    """
    if not brief or not brief.strip():
        raise HTTPException(status_code=400, detail="User brief cannot be empty.")
    if not files:
        raise HTTPException(status_code=400, detail="At least one document file must be uploaded.")

    # 1. Ingest files into isolated session directory
    try:
        ingestion_res = IngestionManager.ingest_files(files=files, session_id=session_id)
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Document ingestion error: {str(e)}")

    # 2. Invoke generic factory pipeline
    try:
        factory = ForgeAIFactory(max_iterations=min(max(iterations, 1), 3))
        results = factory.build_agent(
            brief=brief.strip(),
            doc_folder=ingestion_res.document_dir,
            output_dir=ingestion_res.artifacts_dir,
            unattended=True
        )

        final_sc = results["scorecards"][-1] if results["scorecards"] else None

        return {
            "status": "success",
            "session_id": ingestion_res.session_id,
            "agent_name": results["requirements"].agent_name,
            "domain": results["requirements"].domain,
            "pass_rate": final_sc.pass_rate if final_sc else 0.0,
            "passed_tests": final_sc.passed_tests if final_sc else 0,
            "total_tests": final_sc.total_tests if final_sc else 0,
            "status_verdict": final_sc.status if final_sc else "UNKNOWN",
            "documents_ingested": [d.filename for d in ingestion_res.documents],
            "document_directory": ingestion_res.document_dir,
            "artifacts_directory": ingestion_res.artifacts_dir,
            "agent_definition_path": os.path.join(ingestion_res.artifacts_dir, "agent_definition.json"),
            "manifest_path": ingestion_res.manifest_path
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Factory execution error: {str(e)}")

@app.post("/api/chat")
def chat_endpoint(req: ChatRequest):
    if not os.path.exists(req.definition_path):
        raise HTTPException(status_code=404, detail=f"Agent definition not found: {req.definition_path}")

    try:
        runner = GenericChatRunner(
            definition_path=req.definition_path,
            doc_folder=req.doc_folder
        )
        response = runner.ask(req.query)
        return {
            "answer": response.answer,
            "sources": response.sources,
            "citations": response.citations,
            "tool_calls": response.tool_calls,
            "refused": response.refused
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Runtime error: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
