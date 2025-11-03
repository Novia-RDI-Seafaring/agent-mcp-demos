
from agent import agent, StateDeps, AppState

app = agent.to_ag_ui(deps=StateDeps(AppState()))

if __name__ == "__main__":
    # run the app
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
