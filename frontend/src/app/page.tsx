"use client";
import { useState } from "react";
import { ChatUI } from "@/components/ChatUI";
import { AgentTrace } from "@/components/AgentTrace";
import { Sidebar } from "@/components/Sidebar";

export default function Home() {
  const [activeThread, setActiveThread] = useState<string | null>(null);
  const [agentSteps, setAgentSteps] = useState<any[]>([]);

  return (
    <div className="flex h-screen bg-gray-950 text-white overflow-hidden">
      <Sidebar onSelectThread={setActiveThread} activeThread={activeThread} />
      <main className="flex-1 flex gap-0">
        <ChatUI
          threadId={activeThread}
          onAgentStep={(step) => setAgentSteps((prev) => [...prev, step])}
        />
        {agentSteps.length > 0 && (
          <AgentTrace steps={agentSteps} className="w-80 border-l border-gray-800" />
        )}
      </main>
    </div>
  );
}
