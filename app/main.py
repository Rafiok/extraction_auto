from fastapi import FastAPI
from app.routes import extract

app = FastAPI()
app.include_router(extract.router)

#url de test 
#https://sgg.gouv.bj/doc/decret-2024-003/download 
#code test : uvicorn app.main:app --reload
