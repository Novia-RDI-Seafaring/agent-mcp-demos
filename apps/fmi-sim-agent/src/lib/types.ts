// State of the agent, make sure this aligns with your agent's state.
//export type AgentState = {
//  proverbs: string[];
//}

// New state above or below AgentState
export type SimulationSignal = {
  name: string;
  values: number[];
};

export type SimulationSnapshot = {
  timestamps: number[];
  signals: SimulationSignal[];
};

export type AgentState = {
    proverbs: { proverbs: string[] };
    fmi: {
      available_models: string[];
      current_simulation: any | null;
      simulation_history: any[];
    };
    simulationSnapshot: SimulationSnapshot | null;
    isRunningTool: boolean;
};

