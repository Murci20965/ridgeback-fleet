"use client";

import { ArrowUp, ArrowUpRight, ChevronDown, Database, MessageCircle, RotateCcw, X } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { useChatBridge } from "@/components/ChatBridge";
import { useFilters } from "@/components/FilterProvider";
import { BarChart } from "@/components/ReportCharts";
import { shortDate } from "@/lib/format";
import type { AnswerChart, ChatEvent, Coverage, DashboardLink, TraceStep } from "@/lib/types";

const MAX_QUESTION_LENGTH = 500;
const MAX_HISTORY_MESSAGES = 6;
const DOCKED_KEY = "chat-docked";
const SUGGESTIONS = [
  "Which forklift ran the most hours on Tuesday?",
  "Which driver had the most impacts this week?",
  "Which branch was busiest this week?",
  "Which machines didn't run this week?",
];

interface Message {
  id: number;
  role: "user" | "assistant";
  text: string;
  failed?: boolean;
  trace?: TraceStep[];
  chart?: AnswerChart | null;
  dashboardLink?: DashboardLink | null;
}

const TOOL_LABEL: Record<string, string> = {
  get_run_hours: "Run hours",
  get_event_counts: "Event counts",
  get_fleet: "Fleet list",
  get_data_coverage: "Data coverage",
  calculate: "Calculation",
};

function describeStep(step: TraceStep) {
  const args = step.arguments ?? {};
  const parts = [TOOL_LABEL[step.tool] ?? step.tool];
  const from = args.from_date as string | undefined;
  const to = args.to_date as string | undefined;
  if (from) parts.push(from === to || !to ? shortDate(from) : `${shortDate(from)} to ${shortDate(to)}`);
  for (const key of ["machine_type", "branch", "ref_no", "driver"]) {
    if (args[key]) parts.push(String(args[key]));
  }
  if (Array.isArray(args.event_types)) parts.push(args.event_types.join(", "));
  if (args.group_by) parts.push(`by ${String(args.group_by).replace("_", " ")}`);
  if (args.operation) parts.push(String(args.operation));
  if (Array.isArray(args.values)) parts.push(args.values.join(", "));
  if (step.error) parts.push("no result");
  return parts.join(" · ");
}

function AnswerTrace({ trace }: { trace: TraceStep[] }) {
  return (
    <details className="group mt-2 border-t border-line pt-1.5 text-xs text-ink-2">
      <summary className="flex cursor-pointer list-none items-center gap-1.5 rounded py-0.5 [&::-webkit-details-marker]:hidden">
        <Database size={12} aria-hidden />
        How I got this
        <ChevronDown size={12} className="group-open:rotate-180" aria-hidden />
      </summary>
      <ul className="mt-1 grid gap-0.5 pl-[18px]">
        {trace.map((step, index) => (
          <li key={index}>{describeStep(step)}</li>
        ))}
      </ul>
    </details>
  );
}

export function Chat({ coverage }: { coverage: Coverage | null }) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [status, setStatus] = useState<string | null>(null);
  // A phone starts with the sheet closed, and a large screen starts with the panel docked.
  const [isOpen, setIsOpen] = useState(false);
  const [isDocked, setIsDocked] = useState(true);
  const launcherRef = useRef<HTMLButtonElement>(null);
  const { pending, clearPending } = useChatBridge();
  const { setFilters } = useFilters();
  const nextId = useRef(1);
  const abort = useRef<AbortController | null>(null);
  const scroller = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const isBusy = status !== null;

  useEffect(() => {
    scroller.current?.scrollTo({ top: scroller.current.scrollHeight });
  }, [messages, status]);

  useEffect(() => () => abort.current?.abort(), []);

  // Remembers a closed panel between visits. Storage can be blocked, and then it just stays open.
  useEffect(() => {
    try {
      if (localStorage.getItem(DOCKED_KEY) === "false") setIsDocked(false);
    } catch {}
  }, []);

  function setPanelOpen(open: boolean) {
    setIsOpen(open);
    setIsDocked(open);
    try {
      localStorage.setItem(DOCKED_KEY, String(open));
    } catch {}
    // Keyboard users continue from the control that took its place.
    requestAnimationFrame(() => {
      if (open) inputRef.current?.focus({ preventScroll: true });
      else launcherRef.current?.focus({ preventScroll: true });
    });
  }

  // "/" jumps to the chat from anywhere, unless someone is already typing.
  useEffect(() => {
    function onKey(event: KeyboardEvent) {
      const target = event.target as HTMLElement;
      const isTyping = target.closest("input, textarea, select, [contenteditable]");
      if (event.key === "/" && !isTyping && !event.metaKey && !event.ctrlKey) {
        event.preventDefault();
        setPanelOpen(true);
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  // A question sent from elsewhere on the page, such as an Ask button.
  useEffect(() => {
    if (!pending) return;
    clearPending();
    setPanelOpen(true);
    if (isBusy) setInput(pending);
    else ask(pending);
    // Only a new pending question should run this.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pending]);

  function addMessage(message: Omit<Message, "id">) {
    const id = nextId.current++;
    setMessages((current) => [...current, { ...message, id }]);
  }

  async function ask(question: string) {
    const text = question.trim();
    if (!text || isBusy) return;
    const history = messages
      .filter((message) => !message.failed)
      .slice(-MAX_HISTORY_MESSAGES)
      .map(({ role, text: content }) => ({ role, content }));

    addMessage({ role: "user", text });
    setInput("");
    setStatus("Thinking");
    abort.current = new AbortController();

    try {
      const response = await fetch("/api/v1/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: text, history }),
        signal: abort.current.signal,
      });
      if (response.status === 429) {
        addMessage({ role: "assistant", text: "Too many questions. Try again in a minute.", failed: true });
        return;
      }
      if (!response.ok || !response.body) throw new Error(`Chat failed with ${response.status}`);

      // The response is one JSON object per line, and a read can end mid-line.
      const reader = response.body.pipeThrough(new TextDecoderStream()).getReader();
      let buffer = "";
      let finished = false;
      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        buffer += value;
        const lines = buffer.split("\n");
        buffer = lines.pop() ?? "";
        for (const line of lines) {
          if (!line.trim()) continue;
          const event = JSON.parse(line) as ChatEvent;
          if (event.type === "status") setStatus(event.text);
          if (event.type === "answer") {
            finished = true;
            setStatus(null);
            addMessage({
              role: "assistant",
              text: event.text,
              trace: event.trace,
              chart: event.chart,
              dashboardLink: event.dashboard_link,
            });
          }
          if (event.type === "error") {
            finished = true;
            setStatus(null);
            addMessage({ role: "assistant", text: event.message, failed: true });
          }
        }
      }
      if (!finished) throw new Error("Chat stream ended early");
    } catch (error) {
      if ((error as Error).name === "AbortError") return;
      addMessage({ role: "assistant", text: "Couldn't reach the assistant. Try again.", failed: true });
    } finally {
      setStatus(null);
      inputRef.current?.focus({ preventScroll: true });
    }
  }

  function restart() {
    abort.current?.abort();
    setMessages([]);
    setStatus(null);
    inputRef.current?.focus();
  }

  const lastQuestion = [...messages].reverse().find((message) => message.role === "user")?.text;
  const lastFailed = messages.at(-1)?.failed;

  return (
    <>
      <button
        ref={launcherRef}
        onClick={() => setPanelOpen(true)}
        className={`pressable fixed right-5 bottom-5 z-30 flex min-h-11 items-center gap-2 rounded-full bg-ink px-4 text-sm font-medium text-surface shadow-[0_4px_20px_rgba(0,0,0,0.18)] ${
          isDocked ? "lg:hidden" : ""
        }`}
      >
        <MessageCircle size={18} aria-hidden />
        Ask about your fleet
      </button>
      {isOpen && (
        <div
          className="fixed inset-0 z-30 bg-black/40 lg:hidden"
          onClick={() => setPanelOpen(false)}
          aria-hidden
        />
      )}

      <aside
        aria-label="Fleet assistant"
        data-open={isOpen}
        data-docked={isDocked}
        onKeyDown={(event) => {
          if (event.key === "Escape") setPanelOpen(false);
        }}
        className="chat-panel card flex min-h-0 flex-col overflow-hidden"
      >
        <header className="flex items-center justify-between gap-2 py-3.5 pr-3 pl-5">
          <div className="min-w-0">
            <h2 className="text-[17px] font-semibold tracking-tight">Ask about your fleet</h2>
            {coverage && (
              <p className="text-xs text-ink-2">
                Data from {shortDate(coverage.first_date)} to {shortDate(coverage.last_date)}
              </p>
            )}
          </div>
          <div className="flex shrink-0">
            {messages.length > 0 && (
              <button
                onClick={restart}
                aria-label="Start a new conversation"
                className="pressable grid size-9 place-items-center rounded-lg text-ink-2 hover:bg-surface-2"
              >
                <RotateCcw size={15} aria-hidden />
              </button>
            )}
            <button
              onClick={() => setPanelOpen(false)}
              aria-label="Close the assistant"
              className="pressable grid size-9 place-items-center rounded-lg text-ink-2 hover:bg-surface-2"
            >
              <X size={16} aria-hidden />
            </button>
          </div>
        </header>

        <div ref={scroller} className="min-h-0 flex-1 overflow-y-auto px-5 pb-4" aria-live="polite">
          {messages.length === 0 ? (
            <div>
              <p className="text-sm text-ink-2">
                Ask in plain language. Answers come only from your fleet data, and it&apos;ll tell
                you when the data can&apos;t answer.
              </p>
              <ul className="mt-3 grid gap-1.5">
                {SUGGESTIONS.map((suggestion) => (
                  <li key={suggestion}>
                    <button
                      onClick={() => ask(suggestion)}
                      className="pressable flex w-full items-center justify-between gap-2 rounded-[14px] bg-surface-2 px-3.5 py-3 text-left text-[13px]"
                    >
                      {suggestion}
                      <ArrowUpRight size={14} className="shrink-0 text-ink-2" aria-hidden />
                    </button>
                  </li>
                ))}
              </ul>
            </div>
          ) : (
            <ul className="grid gap-3">
              {messages.map((message) =>
                message.role === "user" ? (
                  <li
                    key={message.id}
                    className="soft-in ml-8 justify-self-end rounded-[18px] rounded-br-[6px] bg-accent px-3 py-2 text-sm break-words text-on-accent"
                  >
                    {message.text}
                  </li>
                ) : (
                  <li key={message.id} className="soft-in text-sm leading-relaxed break-words">
                    <p className={`whitespace-pre-line ${message.failed ? "text-ink-2" : ""}`}>
                      {message.text}
                    </p>
                    {message.chart && (
                      <div className="mt-3 rounded-[14px] bg-surface-2 p-3 [--page:var(--filter)]">
                        <BarChart
                          title={message.chart.title}
                          points={message.chart.points.map((point) => ({
                            ...point,
                            detail: `${point.label}: ${point.display}`,
                          }))}
                        />
                      </div>
                    )}
                    {message.dashboardLink && (
                      <button
                        onClick={() => {
                          const { day, branch, type } = message.dashboardLink!;
                          setFilters({ day, branch, type });
                          // On a phone the sheet covers the dashboard, so it moves aside.
                          setIsOpen(false);
                        }}
                        className="pressable mt-2 flex min-h-9 items-center gap-1 text-left text-[13px] text-accent-ink hover:underline"
                      >
                        {message.dashboardLink.label}
                        <ArrowUpRight size={14} className="shrink-0" aria-hidden />
                      </button>
                    )}
                    {message.trace && message.trace.length > 0 && (
                      <AnswerTrace trace={message.trace} />
                    )}
                  </li>
                ),
              )}
              {status && (
                <li className="flex items-center gap-2 text-[13px] text-ink-2" role="status">
                  <span className="size-3 animate-spin rounded-full border-2 border-line-strong border-t-accent motion-reduce:animate-none" />
                  {status}
                </li>
              )}
              {lastFailed && lastQuestion && !isBusy && (
                <li>
                  <button
                    onClick={() => ask(lastQuestion)}
                    className="pressable min-h-9 rounded-lg border border-line px-3 text-[13px] hover:border-line-strong"
                  >
                    Try again
                  </button>
                </li>
              )}
            </ul>
          )}
        </div>

        <form
          className="p-3"
          onSubmit={(event) => {
            event.preventDefault();
            ask(input);
          }}
        >
          <div className="flex items-end gap-2 rounded-[18px] bg-surface-2 p-1.5">
            <textarea
              ref={inputRef}
              rows={1}
              value={input}
              maxLength={MAX_QUESTION_LENGTH}
              onChange={(event) => setInput(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === "Enter" && !event.shiftKey) {
                  event.preventDefault();
                  ask(input);
                }
              }}
              placeholder="Which driver had the most impacts?"
              aria-label="Your question"
              className="max-h-28 min-h-9 flex-1 resize-none bg-transparent px-2 py-1.5 text-base outline-none [field-sizing:content] placeholder:text-ink-2 lg:text-sm"
            />
            {!input && (
              <kbd className="mb-2 hidden rounded-md border border-line-strong px-1.5 text-[11px] text-ink-2 lg:block">
                /
              </kbd>
            )}
            <button
              type="submit"
              aria-label="Send your question"
              className={`pressable grid size-8 shrink-0 place-items-center rounded-full ${
                input.trim() ? "bg-accent text-on-accent" : "bg-line-strong text-surface"
              }`}
            >
              <ArrowUp size={16} aria-hidden />
            </button>
          </div>
        </form>
      </aside>
    </>
  );
}
