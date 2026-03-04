from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="AgroOS API", version="1.0")

# Чтобы Streamlit/Flutter могли обращаться к API без проблем
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class AdviceReq(BaseModel):
    crop: str
    stage: str
    symptoms: str

@app.get("/")
def home():
    return {"ok": True, "service": "AgroOS API"}

@app.post("/advice")
def advice(req: AdviceReq):
    # ВАЖНО: тут потом будет твой AI/логика
    return {
        "crop": req.crop,
        "stage": req.stage,
        "advice": f"По симптомам '{req.symptoms}' нужно проверить питание и болезни. Дай больше деталей."
    }