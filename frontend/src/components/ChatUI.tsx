"use client";
import { useState, useRef, useEffect, useCallback } from "react";
import { Send, Loader2, Bot, User, Zap } from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  citations?: Array<{ index: number; source: string; score: number }>;
  confidence?: number;
  timestamp: Date;
}

interface ChatUIProps {
  threadId: string | null;
  onAgentStep?: (step: any) => void;
}

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const WS_URL  = process.env.NEXT_PUBLIC_WS_URL  ?? "ws://localhost:8000";

export function ChatUI({ threadId, onAgentStep }: ChatUIProps) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [wsStatus, setWsStatus] = useState<"idle" | "connected" | "error">("idle");
  const wsRef = useRef<WebSocket | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const currentThreadId = threadId ?? crypto.randomUUID();

  const connectWS = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return;
    const ws = new WebSocket(`${WS_URL}/ws/agent/${currentThreadId}`);
    ws.onopen = () => setWsStatus("connected");
    ws.onerror = () => setWsStatus("error");
    ws.onclose = () => setWsStatus("idle");
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.type === "node_update") {
        onAgentStep?.(data);
        if (data.node === "critic" && data.data.final_answer) {
          setMessages((prev) => {
            const last = prev[prev.length - 1];
            if (last?.role === "assistant") {
              return [
                ...prev.slice(0, -1),
                { ...last, content: data.data.final_answer },
              ];
            }
            return [
              ...prev,
              {
                id: crypto.randomUUID(),
                role: "assistant",
                content: data.data.final_answer,
                confidence: data.data.confidence,
                timestamp: new Date(),
              },
            ];
          });
        }
      } else if (data.type === "done") {
        setIsLoading(false);
      } else if (data.type === "error") {
        setIsLoading(false);
        setMessages((prev) => [
          ...prev,
          {
            id: crypto.randomUUID(),
            role: "assistant",
            content: `⚠️ Error: ${data.message}`,
            timestamp: new Date(),
          },
        ]);
      }
    };
    wsRef.current = ws;
  }, [currentThreadId, onAgentStep]);

  const sendMessage = async () => {
    if (!input.trim() || isLoading) return;
    const userMessage: Message = {
      id: crypto.randomUUID(),
      role: "user",
      content: input,
      timestamp: new Date(),
    };
    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setIsLoading(true);

    connectWS();

    const assistantPlaceholder: Message = {
      id: crypto.randomUUID(),
      role: "assistant",
      content: "",
      timestamp: new Date(),
    };
    setMessages((prev) => [...prev, assistantPlaceholder]);

    setTimeout(() => {
      if (wsRef.current?.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify({ task: userMessage.content }));
      } else {
        // Fallback to REST
        fetch(`${API_URL}/api/v1/agent/invoke`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ task: userMessage.content, thread_id: currentThreadId }),
        })
          .then((r) => r.json())
          .then((data) => {
            setMessages((prev) => [
              ...prev.slice(0, -1),
              {
                id: crypto.randomUUID(),
                role: "assistant",
                content: data.answer,
                citations: data.citations,
                confidence: data.confidence,
                timestamp: new Date(),
              },
            ]);
          })
          .finally(() => setIsLoading(false));
      }
    }, 500);
  };

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  return (
    <div className="flex flex-col flex-1 h-full">
      {/* Header */}
      <div className="flex items-center gap-3 px-6 py-4 border-b border-gray-800 bg-gray-900">
        <div className="flex items-center gap-2">
          <Zap className="w-5 h-5 text-violet-400" />
          <h1 className="font-semibold text-white">Enterprise AI Agent</h1>
        </div>
        <span className={`ml-auto text-xs px-2 py-1 rounded-full ${
          wsStatus === "connected" ? "bg-green-900 text-green-400" :
          wsStatus === "error" ? "bg-red-900 text-red-400" :
          "bg-gray-800 text-gray-400"
        }`}>
          {wsStatus === "connected" ? "● Live" : wsStatus === "error" ? "● Error" : "○ Ready"}
        </span>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-6 space-y-4">
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full gap-4 text-gray-500">
            <Bot className="w-12 h-12 text-violet-400 opacity-60" />
            <p className="text-lg font-medium">Ask anything about your enterprise data</p>
            <p className="text-sm">Powered by multi-agent AI with RAG and MCP tools</p>
          </div>
        )}
        {messages.map((msg) => (
          <div key={msg.id} className={`flex gap-3 ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
            {msg.role === "assistant" && (
              <div className="w-8 h-8 rounded-full bg-violet-600 flex items-center justify-center flex-shrink-0">
                <Bot className="w-4 h-4" />
              </div>
            )}
            <div className={`max-w-2xl rounded-2xl px-4 py-3 ${
              msg.role === "user"
                ? "bg-violet-600 text-white"
                : "bg-gray-800 text-gray-100"
            }`}>
              {msg.content ? (
                <ReactMarkdown remarkPlugins={[remarkGfm]} className="prose prose-invert prose-sm max-w-none">
                  {msg.content}
                </ReactMarkdown>
              ) : (
                <div className="flex items-center gap-2 text-gray-400">
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span className="text-sm">Agent working...</span>
                </div>
              )}
              {msg.confidence !== undefined && (
                <div className="mt-2 text-xs text-gray-400">
                  Confidence: {(msg.confidence * 100).toFixed(0)}%
                </div>
              )}
            </div>
            {msg.role === "user" && (
              <div className="w-8 h-8 rounded-full bg-gray-700 flex items-center justify-center flex-shrink-0">
                <User className="w-4 h-4" />
              </div>
            )}
          </div>
        ))}
        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div className="px-6 py-4 border-t border-gray-800 bg-gray-900">
        <div className="flex gap-3 items-end">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); sendMessage(); } }}
            placeholder="Ask a question or describe a task..."
            rows={1}
            className="flex-1 bg-gray-800 text-white rounded-xl px-4 py-3 resize-none focus:outline-none focus:ring-2 focus:ring-violet-500 placeholder-gray-500 text-sm"
          />
          <button
            onClick={sendMessage}
            disabled={!input.trim() || isLoading}
            className="p-3 bg-violet-600 rounded-xl hover:bg-violet-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {isLoading ? <Loader2 className="w-5 h-5 animate-spin" /> : <Send className="w-5 h-5" />}
          </button>
        </div>
      </div>
    </div>
  );
}
