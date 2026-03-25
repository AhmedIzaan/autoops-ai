"use client";

import React, { useEffect, useRef, useState } from "react";
import { motion } from "framer-motion";
import Link from "next/link";
import { ArrowRight, Sparkles, FileText, Mail, BarChart3, ListChecks } from "lucide-react";

// ─── Animated terminal data ───────────────────────────────────────────────────
type LogLine = {
    text: string;
    color: string;
    delay: number; // ms after previous line finishes
};

const WORKFLOW_LINES: LogLine[] = [
    { text: '> user: "Generate weekly sales pipeline report, then email the team"', color: "text-neutral-300", delay: 0 },
    { text: "⚙  Planner Node  →  identifying execution path...", color: "text-indigo-400", delay: 900 },
    { text: "   └─ step 1 : csv_analyzer   { path: 'sales_q1.csv' }", color: "text-neutral-500", delay: 600 },
    { text: "   └─ step 2 : report_generator { title: 'Q1 Sales Report' }", color: "text-neutral-500", delay: 300 },
    { text: "   └─ step 3 : email_draft    { to: 'team@acme.com' }", color: "text-neutral-500", delay: 300 },
    { text: "▶  Executing  csv_analyzer...", color: "text-amber-400", delay: 700 },
    { text: "   rows: 1,240  |  cols: 8  |  numeric cols: 5", color: "text-neutral-500", delay: 500 },
    { text: "   insight: «Revenue up 18% MoM; 3 outlier deals flagged»", color: "text-emerald-300", delay: 400 },
    { text: "✔  csv_analyzer  completed", color: "text-emerald-400", delay: 500 },
    { text: "▶  Executing  report_generator...", color: "text-amber-400", delay: 600 },
    { text: "   generated 2-page markdown report with 6 highlights", color: "text-neutral-500", delay: 700 },
    { text: "✔  report_generator  completed", color: "text-emerald-400", delay: 400 },
    { text: "▶  Executing  email_draft...", color: "text-amber-400", delay: 600 },
    { text: "   subject: \"Q1 Sales Recap – action required\"", color: "text-neutral-500", delay: 500 },
    { text: "✔  email_draft  completed", color: "text-emerald-400", delay: 400 },
    { text: "✦  Workflow completed  ·  3 steps  ·  2.4 s", color: "text-indigo-300", delay: 800 },
];

const CHAR_DELAY = 22; // ms per character

function AnimatedTerminal() {
    const [visibleLines, setVisibleLines] = useState<{ text: string; color: string; partial: string; done: boolean }[]>([]);
    const containerRef = useRef<HTMLDivElement>(null);
    const cycleRef = useRef<ReturnType<typeof setTimeout> | null>(null);

    useEffect(() => {
        let cancelled = false;

        async function runCycle() {
            setVisibleLines([]);
            await sleep(600);

            for (let i = 0; i < WORKFLOW_LINES.length; i++) {
                if (cancelled) return;
                const { text, color, delay } = WORKFLOW_LINES[i];
                await sleep(delay);
                if (cancelled) return;

                // Append a new blank line
                setVisibleLines(prev => [...prev, { text, color, partial: "", done: false }]);

                // Type it out character by character
                for (let c = 1; c <= text.length; c++) {
                    if (cancelled) return;
                    await sleep(CHAR_DELAY);
                    setVisibleLines(prev => {
                        const next = [...prev];
                        next[next.length - 1] = { ...next[next.length - 1], partial: text.slice(0, c) };
                        return next;
                    });
                }

                // Mark done (removes cursor)
                setVisibleLines(prev => {
                    const next = [...prev];
                    next[next.length - 1] = { ...next[next.length - 1], done: true };
                    return next;
                });

                // Scroll to bottom
                if (containerRef.current) {
                    containerRef.current.scrollTop = containerRef.current.scrollHeight;
                }
            }

            // Pause before looping
            await sleep(2800);
            if (!cancelled) runCycle();
        }

        runCycle();
        return () => { cancelled = true; if (cycleRef.current) clearTimeout(cycleRef.current); };
    }, []);

    return (
        <div
            ref={containerRef}
            className="p-6 font-mono text-[13px] space-y-2 text-neutral-400 bg-black/40 min-h-[220px] max-h-[280px] overflow-hidden"
        >
            {visibleLines.map((line, idx) => (
                <p key={idx} className={line.color}>
                    {line.partial}
                    {!line.done && (
                        <span className="inline-block w-[2px] h-[1em] bg-current align-middle ml-0.5 animate-pulse" />
                    )}
                </p>
            ))}
        </div>
    );
}

function sleep(ms: number) {
    return new Promise(r => setTimeout(r, ms));
}

// ─── Page ─────────────────────────────────────────────────────────────────────
export default function LandingPage() {
    const features = [
        {
            icon: <BarChart3 className="w-5 h-5 text-indigo-400" />,
            title: "Data Analysis",
            description: "Upload CSVs and instantly extract insights, generate summaries, and prepare structured reports."
        },
        {
            icon: <FileText className="w-5 h-5 text-emerald-400" />,
            title: "Document Extraction",
            description: "Summarize large PDFs automatically. Extract key metrics without reading pages of text."
        },
        {
            icon: <Mail className="w-5 h-5 text-blue-400" />,
            title: "Automated Comms",
            description: "Draft ready-to-send emails based on extracted data, perfectly formatted for your team."
        },
        {
            icon: <ListChecks className="w-5 h-5 text-rose-400" />,
            title: "Task Delegation",
            description: "Creates tasks and assigns them automatically using smart workflow orchestration."
        }
    ];

    return (
        <div className="min-h-screen bg-[#0A0A0A] text-white font-sans selection:bg-indigo-500/30 overflow-x-hidden">

            {/* Navbar */}
            <nav className="fixed top-0 left-0 right-0 z-50 flex items-center justify-between px-6 py-4 backdrop-blur-md border-b border-white/5 bg-[#0A0A0A]/50">
                <div className="flex items-center space-x-2">
                    <Sparkles className="w-5 h-5 text-indigo-500" />
                    <span className="text-lg font-medium tracking-tight">AutoOps AI</span>
                </div>
            </nav>

            <main className="pt-32 pb-24">

                {/* Hero Section */}
                <section className="relative px-6 flex flex-col items-center justify-center text-center max-w-5xl mx-auto mt-16 md:mt-24">
                    {/* Background Glow */}
                    <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[800px] h-[400px] bg-indigo-500/20 blur-[120px] rounded-full pointer-events-none -z-10" />

                    <motion.div
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ duration: 0.5 }}
                        className="inline-flex items-center space-x-2 bg-white/5 border border-white/10 rounded-full px-3 py-1 mb-8"
                    >
                        <span className="flex h-2 w-2 rounded-full bg-emerald-500 animate-pulse"></span>
                        <span className="text-xs font-medium text-neutral-300">LangGraph Orchestration V1</span>
                    </motion.div>

                    <motion.h1
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ duration: 0.5, delay: 0.1 }}
                        className="text-5xl md:text-7xl font-bold tracking-tight text-transparent bg-clip-text bg-gradient-to-b from-white to-white/60 mb-6"
                    >
                        The Autonomous Agent <br className="hidden md:block" /> for Business Operations
                    </motion.h1>

                    <motion.p
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ duration: 0.5, delay: 0.2 }}
                        className="text-lg md:text-xl text-neutral-400 max-w-2xl mb-10 leading-relaxed font-light"
                    >
                        Stop connecting tools manually. Tell AutoOps what you want, and watch it seamlessly sequence CSV analysis, document summarization, and email drafting.
                    </motion.p>

                    <motion.div
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ duration: 0.5, delay: 0.3 }}
                        className="flex flex-col sm:flex-row items-center space-y-4 sm:space-y-0 sm:space-x-4"
                    >
                        <Link
                            href="/chat"
                            className="flex items-center space-x-2 px-8 py-4 bg-white text-black text-sm font-semibold rounded-full hover:bg-neutral-200 transition-all hover:scale-105"
                        >
                            <span>Start Automating</span>
                            <ArrowRight className="w-4 h-4" />
                        </Link>
                        <a
                            href="#features"
                            className="px-8 py-4 bg-white/5 text-white text-sm font-medium border border-white/10 rounded-full hover:bg-white/10 transition-colors"
                        >
                            How it works
                        </a>
                    </motion.div>
                </section>

                {/* Animated Console Demo */}
                <motion.section
                    initial={{ opacity: 0, y: 40 }}
                    whileInView={{ opacity: 1, y: 0 }}
                    viewport={{ once: true }}
                    transition={{ duration: 0.7, delay: 0.4 }}
                    className="max-w-4xl mx-auto mt-24 px-6 relative z-10"
                >
                    <div className="rounded-2xl border border-white/10 overflow-hidden bg-[#0A0A0A] shadow-[0_0_50px_rgba(99,102,241,0.1)]">
                        {/* Terminal title bar */}
                        <div className="flex items-center px-4 py-3 border-b border-white/5 bg-white/[0.02]">
                            <div className="flex space-x-2">
                                <div className="w-3 h-3 rounded-full bg-rose-500/80" />
                                <div className="w-3 h-3 rounded-full bg-amber-500/80" />
                                <div className="w-3 h-3 rounded-full bg-emerald-500/80" />
                            </div>
                            <div className="ml-4 text-xs font-mono text-neutral-500">agent-workflow.log</div>
                            <div className="ml-auto flex items-center gap-1.5">
                                <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
                                <span className="text-[10px] font-mono text-neutral-600 uppercase tracking-widest">live</span>
                            </div>
                        </div>
                        {/* Animated body */}
                        <AnimatedTerminal />
                    </div>
                </motion.section>

                {/* Features Section */}
                <section id="features" className="max-w-6xl mx-auto px-6 mt-32">
                    <div className="text-center mb-16">
                        <h2 className="text-3xl font-semibold tracking-tight">One Prompt. Multiple Tools.</h2>
                        <p className="mt-4 text-neutral-400">Powered by LangGraph for deterministic, reliable orchestration.</p>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                        {features.map((f, i) => (
                            <motion.div
                                key={i}
                                initial={{ opacity: 0, y: 20 }}
                                whileInView={{ opacity: 1, y: 0 }}
                                viewport={{ once: true }}
                                transition={{ duration: 0.5, delay: i * 0.1 }}
                                className="p-6 rounded-2xl border border-white/5 bg-white/[0.02] hover:bg-white/[0.04] transition-colors"
                            >
                                <div className="w-12 h-12 rounded-xl bg-white/5 flex items-center justify-center border border-white/10 mb-6">
                                    {f.icon}
                                </div>
                                <h3 className="text-lg font-medium text-neutral-200 mb-2">{f.title}</h3>
                                <p className="text-neutral-500 text-sm leading-relaxed">{f.description}</p>
                            </motion.div>
                        ))}
                    </div>
                </section>

            </main>

            <footer className="border-t border-white/10 py-8 text-center text-sm text-neutral-600 bg-black/20">
                <p>© 2026 AutoOps AI. Built for multi-agent workflows.</p>
            </footer>
        </div>
    );
}

