# server.py
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import uvicorn
import json
from modelBuilder import ModelBuilder  # This imports the builder from earlier!

app = FastAPI()


# This defines the data structure the frontend will send us
class ModelData(BaseModel):
    model_json: dict


@app.post("/solve")
def solve_model(data: ModelData):
    try:
        # 1. Save the frontend's JSON to a temporary file
        with open("../temp_model.json", "w") as f:
            json.dump(data.model_json, f)

        # 2. Use our ModelBuilder to convert JSON -> SCIP Model
        builder = ModelBuilder("../temp_model.json")
        scip_model = builder.build()

        # 3. Solve it!
        scip_model.hideOutput()  # Hides solver logs from console
        scip_model.optimize()

        status = scip_model.getStatus()

        # 4. Extract the results
        solution = {}
        objective_value = None

        if status == "optimal":
            objective_value = scip_model.getObjVal()
            # Only keep variables that were chosen (value > 0)
            for v in scip_model.getVars():
                val = scip_model.getVal(v)
                if abs(val) > 1e-6:
                    solution[v.name] = val

        return {
            "status": status,
            "objective": objective_value,
            "solution": solution
        }

    except Exception as e:
        return {"status": "error", "message": str(e)}


# This tells Python to host your frontend folder directly!
app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")

if __name__ == "__main__":
    print("Starting Optimization Game Server at http://localhost:8000")
    uvicorn.run(app, host="127.0.0.1", port=8000)