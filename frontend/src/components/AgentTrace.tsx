"use client";
import { CheckCircle, Clock, Brain, Wrench, Eye } from "lucide-react";

interface AgentStep {
  node: string;
  data: { plan?: string[]; final_answer?: string; confidence?: number };
  timestamp?: string;
}

const NODE_ICONS: Record<string, any> = {
  memory_retrieval: Eye,
  planner:          Brain,
  executor:         Wrench,
  critic:           CheckCircle,
  handle_error:     Clock,
};

const NODE_COLORS: Record<string, string> = {
  memory_retrieval: "text-blue-400",
  planner:          "text-yellow-400",
  executor:         "text-green-400",
  critic:           "text-violet-400",
  handle_error:     "text-red-400",
};

export function AgentTrace({ steps, className }: { steps: AgentStep[]; className?: string }) {
  return (
    <aside className={`flex flex-col bg-gray-950 p-4 overflow-y-auto ${className}`}>
      <h2 className="text-sm font-semibold text-gray-400 mb-4 uppercase tracking-wider">
        Agent Reasoning
      </h2>
      <div className="space-y-3">
        {steps.map((step, i) => {
          const Icon = NODE_ICONS[step.node] ?? Brain;
          const color = NODE_COLORS[step.node] ?? "text-gray-400";
          return (
            <div key={i} className="flex gap-3 p-3 bg-gray-900 rounded-lg border border-gray-800">
              <Icon className={`w-4 h-4 mt-0.5 flex-shrink-0 ${color}`} />
              <div className="flex-1 min-w-0">
                <p className={`text-xs font-medium capitalize ${color}`}>
                  {step.node.replace(/_/g, " ")}
                </p>
                {step.data.plan && (
                  <ul className="mt-1 space-y-1">
                    {step.data.plan.map((s, j) => (
                      <li key={j} className="text-xs text-gray-400 truncate">
                        {j + 1}. {s}
                      </li>
                    ))}
                  </ul>
                )}
                {step.data.confidence !== undefined && (
                  <div className="mt-1">
                    <div className="w-full bg-gray-800 rounded-full h-1.5">
                      <div
                        className="bg-violet-500 h-1.5 rounded-full"
                        style={{ width: `${step.data.confidence * 100}%` }}
                      />
                    </div>
                    <p className="text-xs text-gray-500 mt-0.5">
                      {(step.data.confidence * 100).toFixed(0)}% confidence
                    </p>
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </aside>
  );
}
