from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import pandas as pd
import io
import json
from typing import Optional

from core import prepare_network, calculate_node_positions
from parser import parse_obsidian_zip

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/process")
async def process_data(
    file: UploadFile = File(...),
    layer_file: Optional[UploadFile] = File(None),
    config: str = Form("{}")
):
    try:
        cfg = json.loads(config)
        contents = await file.read()
        buf = io.BytesIO(contents)

        if file.filename.lower().endswith('.csv'):
            edges_df = pd.read_csv(buf)
            layer_df = None
        else:
            excel = pd.ExcelFile(buf)
            edges_df = pd.read_excel(excel, sheet_name="edges")
            layer_df = pd.read_excel(excel, sheet_name="layers") if "layers" in excel.sheet_names else None

        if layer_file:
            layer_contents = await layer_file.read()
            layer_buf = io.BytesIO(layer_contents)
            layer_df = (
                pd.read_csv(layer_buf)
                if layer_file.filename.lower().endswith('.csv')
                else pd.read_excel(layer_buf)
            )

        network_data = prepare_network(edges_df, layer_df, manual_order=cfg.get('manual_order'))
        pos = calculate_node_positions(network_data, cfg)
        return {"network_data": network_data, "positions": pos, "config": cfg}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/process-obsidian")
async def process_obsidian(
    file: UploadFile = File(...),
    config: str = Form("{}")
):
    try:
        cfg = json.loads(config)
        contents = await file.read()
        edges_df = parse_obsidian_zip(contents)
        if edges_df.empty:
            raise ValueError("No interlinkages found in the ZIP. Check that it contains 'Actors', 'Instruments', and 'Interlinkages' folders.")
        network_data = prepare_network(edges_df, manual_order=cfg.get('manual_order'))
        pos = calculate_node_positions(network_data, cfg)
        return {"network_data": network_data, "positions": pos, "config": cfg}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


app.mount("/", StaticFiles(directory="static", html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)