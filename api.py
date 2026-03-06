from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from agro_assistant import generate_expert_response

app = FastAPI(title="AgroOS API", version="2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class AdviceReq(BaseModel):
    crop: str = "Wheat"
    stage: str = "Vegetative"
    symptoms: str
    field: str = "General"
    mode: str = "Expert"
    include_weather: bool = False


@app.get("/")
def home():
    return {"ok": True, "service": "AgroOS API", "version": "2.0"}


@app.post("/advice")
def advice(req: AdviceReq):
    result = generate_expert_response(
        question=req.symptoms,
        field_name=req.field or "General",
        crop=req.crop,
        stage=req.stage,
        mode=req.mode,
        include_weather=bool(req.include_weather),
    )
    return {
        "crop": req.crop,
        "stage": req.stage,
        "field": req.field,
        "intents": result.get("intents", []),
        "advice": result.get("answer", ""),
    }
