"use client";

import React, { useState, useRef, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Send, Upload, Sparkles, CheckCircle2, Circle, Loader2, ArrowRight } from "lucide-react";

type RunState = {
    run_id?: string;
    prompt?: string;
    plan?: Array<{ tool: string; args: any }>;
    cursor?: number;
    tool_results?: Array<any>;
    status?: string;
    message?: string;
};

type StreamEvent = {
    node: string;
    state: RunState;
};

export default function Home() {
    const [prompt, setPrompt] = useState("");
    const [events, setEvents] = useState<StreamEvent[]>([]);
    const [isStreaming, setIsStreaming] = useState(false);
    const scrollRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        if (scrollRef.current) {
            scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
        }
    }, [events]);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!prompt.trim() || isStreaming) return;

        setIsStreaming(true);
        setEvents([]);

        try {
            const response = await fetch("http://localhost:8000/api/runs/stream", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ prompt, file_refs: [] }),
            });

            if (!response.body) throw new Error("No response body");

            const reader = response.body.getReader();
            const decoder = new TextDecoder("utf-8");
            let buffer = "";

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                buffer += decoder.decode(value, { stream: true });
                const lines = buffer.split("\n\n");
                buffer = lines.pop() || "";

                for (const line of lines) {
                    if (line.startsWith("data: ")) {
                        const dataStr = line.replace("data: ", "");
                        if (dataStr === "[DONE]") {
                            setIsStreaming(false);
                            break;
                        }
                        try {
                            const data = JSON.parse(dataStr) as StreamEvent;
                            setEvents((prev) => [...prev, data]);
                        } catch (err) {
                            console.error("Error parsing SSE JSON:", err);
                        }
                    }
                }
            }
        } catch (error) {
            console.error("Stream failed:", error);
            setIsStreaming(false);
        }
    };

    const currentState = events.length > 0 ? events[events.length - 1].state : null;
    const currentPlan = currentState?.plan || [];
    const cursor = currentState?.cursor ?? 0;
    const toolResults = currentState?.tool_results || [];

    return (
        <div className="flex flex-col h-screen bg-[#0A0A0A] text-white font-sans overflow-hidden selection:bg-indigo-500/30">
            {/* Header */}
            <header className="flex items-center px-6 py-4 border-b border-white/5 shrink-0 bg-white/[0.02]">
                <Sparkles className="w-5 h-5 text-indigo-400 mr-2" />
                <h1 className="text-lg font-medium tracking-tight">AutoOps AI</h1>
                <div className="ml-auto text-xs font-mono text-neutral-400 bg-white/5 px-2.5 py-1 rounded-md border border-white/10 uppercase tracking-widest">
                    {currentState?.status || "Ready"}
                </div>
            </header>

            {/* Main Content Area */}
            <main className="flex-1 overflow-y-auto p-6 md:p-12 space-y-8 no-scrollbar" ref={scrollRef}>
                {!currentState && !isStreaming ? (
                    <div className="flex flex-col items-center justify-center h-full text-center space-y-5 opacity-60">
                        <div className="w-16 h-16 rounded-2xl bg-indigo-500/10 flex items-center justify-center border border-indigo-500/20">
                            <Sparkles className="w-8 h-8 text-indigo-400 mb-0.5 ml-0.5" />
                        </div>
                        <div className="space-y-2">
                            <h2 className="text-2xl font-semibold tracking-tight text-neutral-100">What do you want to automate?</h2>
                            <p className="text-sm text-neutral-400 max-w-md mx-auto leading-relaxed">
                                Describe a sequence of tasks like document summarization, data extraction, or email drafting. The agent figures out the rest.
                            </p>
                        </div>
                    </div>
                ) : (
                    <div className="max-w-3xl mx-auto space-y-8 pb-10">
                        <div className="bg-white/[0.03] border border-white/10 rounded-2xl p-6 mb-8 shadow-sm">
                            <div className="flex items-center space-x-2 text-xs text-indigo-400/80 uppercase tracking-widest font-semibold mb-3">
                                <ArrowRight className="w-3.5 h-3.5" />
                                <span>Goal</span>
                            </div>
                            <p className="text-lg text-neutral-200 leading-relaxed font-light">{currentState?.prompt}</p>
                        </div>

                        {/* Workflow Visualization */}
                        {currentPlan.length > 0 && (
                            <div className="space-y-6">
                                <div className="flex items-center space-x-3 mb-6">
                                    <div className="h-px flex-1 bg-gradient-to-r from-transparent via-white/10 to-transparent" />
                                    <h3 className="text-xs font-semibold text-neutral-500 uppercase tracking-widest">
                                        Execution Plan
                                    </h3>
                                    <div className="h-px flex-1 bg-gradient-to-r from-white/10 via-transparent to-transparent" />
                                </div>

                                <div className="space-y-4 relative before:absolute before:inset-0 before:ml-6 before:-translate-x-px md:before:mx-auto md:before:translate-x-0 before:h-full before:w-0.5 before:bg-gradient-to-b before:from-white/10 before:via-white/10 before:to-transparent">
                                    <AnimatePresence>
                                        {currentPlan.map((step, idx) => {
                                            const isCompleted = idx < cursor;
                                            const isActive = idx === cursor && isStreaming;
                                            const isPending = idx > cursor;
                                            const result = toolResults.length > idx ? toolResults[idx] : null;

                                            return (
                                                <div key={idx} className="relative flex items-start md:justify-between group">
                                                    {/* Timeline dot */}
                                                    <div className="absolute left-6 -translate-x-1/2 md:left-1/2 flex items-center justify-center mt-6">
                                                        <div className={`w-3 h-3 rounded-full border-2 bg-[#0A0A0A] z-10 transition-colors duration-500 ${isCompleted ? "border-emerald-500 shadow-[0_0_10px_rgba(16,185,129,0.4)]" : isActive ? "border-indigo-400 bg-indigo-400 shadow-[0_0_15px_rgba(99,102,241,0.5)]" : "border-neutral-700"
                                                            }`} />
                                                    </div>

                                                    {/* Card */}
                                                    <motion.div
                                                        initial={{ opacity: 0, y: 20 }}
                                                        animate={{ opacity: 1, y: 0 }}
                                                        transition={{ delay: idx * 0.15, type: "spring", stiffness: 100 }}
                                                        className={`w-full md:w-[calc(50%-2.5rem)] ml-14 md:ml-0 p-5 rounded-2xl border transition-all duration-500 relative backdrop-blur-sm ${idx % 2 === 0 ? "md:mr-auto" : "md:ml-auto"
                                                            } ${isActive
                                                                ? "bg-indigo-500/5 border-indigo-500/20 shadow-[0_0_30px_rgba(99,102,241,0.05)]"
                                                                : isCompleted
                                                                    ? "bg-white/[0.02] border-white/5"
                                                                    : "bg-transparent border-white/5 opacity-40 grayscale"
                                                            }`}
                                                    >
                                                        <div className="flex items-center space-x-3 mb-2">
                                                            {isCompleted ? (
                                                                <CheckCircle2 className="w-5 h-5 text-emerald-500 shrink-0" />
                                                            ) : isActive ? (
                                                                <Loader2 className="w-5 h-5 text-indigo-400 animate-spin shrink-0" />
                                                            ) : (
                                                                <Circle className="w-5 h-5 text-neutral-600 shrink-0" />
                                                            )}
                                                            <span className="font-mono text-sm text-neutral-100 font-medium">
                                                                {step.tool}
                                                            </span>
                                                        </div>

                                                        {step.args && (
                                                            <div className="text-[13px] font-mono text-neutral-400 mt-2 bg-black/30 p-2.5 rounded-lg border border-white/5">
                                                                {Object.entries(step.args).map(([k, v]) => (
                                                                    <div key={k} className="truncate"><span className="text-neutral-500">{k}:</span> {JSON.stringify(v)}</div>
                                                                ))}
                                                            </div>
                                                        )}

                                                        {/* Tool Result Expansion */}
                                                        {isCompleted && result && (
                                                            <motion.div
                                                                initial={{ height: 0, opacity: 0 }}
                                                                animate={{ height: "auto", opacity: 1 }}
                                                                className="mt-4 pt-4 border-t border-white/5 flex flex-col space-y-2 overflow-hidden"
                                                            >
                                                                <span className="text-[10px] uppercase tracking-widest font-semibold text-neutral-500">Output</span>
                                                                <div className="text-xs font-mono p-3 bg-black/40 rounded-xl overflow-x-auto border border-emerald-500/10 text-emerald-200/80 scrollbar-thin scrollbar-thumb-white/10">
                                                                    <pre>{JSON.stringify(result.output || result.error, null, 2)}</pre>
                                                                </div>
                                                            </motion.div>
                                                        )}
                                                    </motion.div>
                                                </div>
                                            );
                                        })}
                                    </AnimatePresence>
                                </div>

                                {/* Final status */}
                                {currentState?.status === "completed" && (
                                    <motion.div
                                        initial={{ opacity: 0, scale: 0.95 }}
                                        animate={{ opacity: 1, scale: 1 }}
                                        transition={{ delay: 0.5 }}
                                        className="p-6 mt-12 border border-emerald-500/20 bg-emerald-500/5 rounded-2xl flex items-center space-x-4 shadow-[0_0_40px_rgba(16,185,129,0.05)] mx-auto max-w-md"
                                    >
                                        <div className="w-10 h-10 rounded-full bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center shrink-0">
                                            <Sparkles className="w-5 h-5 text-emerald-400" />
                                        </div>
                                        <div>
                                            <p className="font-semibold text-emerald-300">Automated Workflow Complete</p>
                                            {currentState.message && <p className="text-sm opacity-80 mt-1 text-emerald-200/60 font-medium">{currentState.message}</p>}
                                        </div>
                                    </motion.div>
                                )}
                            </div>
                        )}
                    </div>
                )}
            </main>

            {/* Input Area */}
            <footer className="p-6 bg-gradient-to-t from-[#0A0A0A] to-[#0A0A0A]/80 border-t border-white/5 shrink-0 backdrop-blur-xl z-20">
                <form onSubmit={handleSubmit} className="max-w-4xl mx-auto relative group">
                    <div className="flex items-end bg-white/[0.03] hover:bg-white/[0.04] focus-within:bg-white/[0.05] border border-white/10 focus-within:border-indigo-500/50 rounded-3xl p-2 transition-all shadow-2xl">
                        <button
                            type="button"
                            className="p-3 mb-1 text-neutral-500 hover:text-white transition-colors rounded-xl hover:bg-white/5"
                            title="Upload file"
                        >
                            <Upload className="w-5 h-5" />
                        </button>
                        <textarea
                            value={prompt}
                            onChange={(e) => setPrompt(e.target.value)}
                            placeholder="E.g., Generate a sales report, create sub-tasks for the team, and draft an update email..."
                            className="flex-1 bg-transparent border-none outline-none text-white px-3 py-4 placeholder:text-neutral-600 resize-none min-h-[60px] max-h-[200px]"
                            rows={1}
                            disabled={isStreaming}
                            onKeyDown={(e) => {
                                if (e.key === 'Enter' && !e.shiftKey) {
                                    e.preventDefault();
                                    handleSubmit(e);
                                }
                            }}
                        />
                        <button
                            type="submit"
                            disabled={!prompt.trim() || isStreaming}
                            className="p-3 mb-1 m-1 bg-white text-black hover:bg-neutral-200 rounded-xl transition-all disabled:opacity-30 disabled:hover:bg-white flex items-center justify-center shrink-0 shadow-sm"
                        >
                            <ArrowRight className="w-5 h-5" />
                        </button>
                    </div>
                </form>
                <p className="text-center text-[11px] text-neutral-600 mt-4 font-medium tracking-wide">
                    AutoOps AI operates via LangGraph workflows. Review tasks before executing locally.
                </p>
            </footer>
        </div>
    );
}
