"use client";
import { useState } from "react";
import { Plus, MessageSquare, Zap } from "lucide-react";

interface SidebarProps {
  onSelectThread: (id: string) => void;
  activeThread: string | null;
}

export function Sidebar({ onSelectThread, activeThread }: SidebarProps) {
  const [threads] = useState([
    { id: "t1", title: "Q4 Revenue Analysis", date: "Today" },
    { id: "t2", title: "Customer churn research", date: "Yesterday" },
    { id: "t3", title: "Compliance report draft", date: "May 29" },
  ]);

  return (
    <aside className="w-64 bg-gray-900 border-r border-gray-800 flex flex-col">
      <div className="p-4 border-b border-gray-800">
        <div className="flex items-center gap-2 mb-4">
          <Zap className="w-6 h-6 text-violet-400" />
          <span className="font-bold text-white">AgentAI</span>
        </div>
        <button
          onClick={() => onSelectThread(crypto.randomUUID())}
          className="w-full flex items-center gap-2 px-3 py-2 bg-violet-600 hover:bg-violet-700 rounded-lg text-sm font-medium transition-colors"
        >
          <Plus className="w-4 h-4" /> New Thread
        </button>
      </div>
      <nav className="flex-1 overflow-y-auto p-3 space-y-1">
        {threads.map((t) => (
          <button
            key={t.id}
            onClick={() => onSelectThread(t.id)}
            className={`w-full flex items-start gap-3 px-3 py-2.5 rounded-lg text-left transition-colors ${
              activeThread === t.id ? "bg-gray-800 text-white" : "text-gray-400 hover:bg-gray-800 hover:text-white"
            }`}
          >
            <MessageSquare className="w-4 h-4 mt-0.5 flex-shrink-0" />
            <div>
              <p className="text-sm font-medium truncate">{t.title}</p>
              <p className="text-xs text-gray-500">{t.date}</p>
            </div>
          </button>
        ))}
      </nav>
    </aside>
  );
}
