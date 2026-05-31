import React, { useState } from "react";
import { createRoot } from "react-dom/client";
import { BookOpenText, Bot, BrainCircuit, Camera, CheckCircle2, Database, Info, Loader2, Mail, MessageSquareText, Network, Search, Send, Wrench, X } from "lucide-react";
import "./styles.css";

type TicketResponse = {
  ticket_id: number;
  customer_email: string;
  status: string;
  detected_objects: string[];
  detected_error_code: string | null;
  technical_steps: string;
  reply_subject: string;
  reply_body: string;
  email_sent: boolean;
};

type TicketStatus = {
  ticket_id: number;
  customer_email: string;
  status: string;
  detected_error_code: string | null;
  technical_steps: string | null;
  email_sent: boolean;
};

type ChatMessage = {
  role: "user" | "assistant";
  content: string;
};

type ChatResponse = {
  reply: string;
  model: string;
  used_rag: boolean;
  sources: string[];
};

function App() {
  const [email, setEmail] = useState("customer@example.com");
  const [description, setDescription] = useState("");
  const [photo, setPhoto] = useState<File | null>(null);
  const [ticket, setTicket] = useState<TicketResponse | null>(null);
  const [status, setStatus] = useState<TicketStatus | null>(null);
  const [loading, setLoading] = useState(false);
  const [statusLoading, setStatusLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [agentModalOpen, setAgentModalOpen] = useState(false);
  const [chatQuestion, setChatQuestion] = useState("What is Bluefin mode?");
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([]);
  const [useRag, setUseRag] = useState(true);
  const [chatLoading, setChatLoading] = useState(false);
  const [chatError, setChatError] = useState<string | null>(null);

  async function submitTicket(event: React.FormEvent) {
    event.preventDefault();
    if (!photo && !description.trim()) {
      setError("Please add an error photo, a text description, or both.");
      return;
    }

    const formData = new FormData();
    formData.append("customer_email", email);
    formData.append("description", description);
    if (photo) {
      formData.append("photo", photo);
    }

    setLoading(true);
    setError(null);
    setTicket(null);
    setStatus(null);
    setAgentModalOpen(true);

    try {
      const response = await fetch("/api/support/tickets", {
        method: "POST",
        body: formData,
      });
      if (!response.ok) {
        throw new Error(`Backend returned HTTP ${response.status}`);
      }
      setTicket((await response.json()) as TicketResponse);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unknown support request failure");
    } finally {
      setLoading(false);
    }
  }

  async function lookupStatus() {
    setStatusLoading(true);
    setError(null);
    setStatus(null);

    try {
      const response = await fetch(`/api/support/tickets?email=${encodeURIComponent(email)}`);
      if (!response.ok) {
        throw new Error(`Backend returned HTTP ${response.status}`);
      }
      setStatus((await response.json()) as TicketStatus);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unknown status lookup failure");
    } finally {
      setStatusLoading(false);
    }
  }

  async function sendChatQuestion(event: React.FormEvent) {
    event.preventDefault();
    const message = chatQuestion.trim();
    if (!message) {
      setChatError("Please enter a question.");
      return;
    }

    const history = chatMessages.slice(-6);
    setChatLoading(true);
    setChatError(null);
    setChatMessages((current) => [...current, { role: "user", content: message }]);

    try {
      const response = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message,
          history,
          use_rag: useRag,
        }),
      });
      if (!response.ok) {
        throw new Error(`Backend returned HTTP ${response.status}`);
      }
      const data = (await response.json()) as ChatResponse;
      const sourceLine = data.sources.length > 0 ? `\n\nSources: ${data.sources.join(", ")}` : "";
      setChatMessages((current) => [
        ...current,
        { role: "assistant", content: `${data.reply}${sourceLine}` },
      ]);
      setChatQuestion("");
    } catch (caught) {
      setChatError(caught instanceof Error ? caught.message : "Unknown chat failure");
    } finally {
      setChatLoading(false);
    }
  }

  return (
    <main className="app-shell">
      <AgentWorkModal
        open={agentModalOpen}
        ticket={ticket}
        error={error}
        onClose={() => {
          setAgentModalOpen(false);
          setTicket(null);
          setStatus(null);
        }}
        onCheckStatus={() => {
          setAgentModalOpen(false);
          setTicket(null);
          void lookupStatus();
        }}
      />

      <aside className="sidebar">
        <div className="brand">
          <Wrench size={28} />
          <div>
            <strong>Aster Pump Aftercare</strong>
            <span>Local agentic support desk</span>
          </div>
        </div>

        <div className="system-summary">
          <p>System flow</p>
          <strong>Photo to ticket, manual to answer, agent to reply.</strong>
        </div>

        <div className="stack-list">
          <div><Bot size={17} /> Customer Service Agent</div>
          <div><BookOpenText size={17} /> Technical Assistant + RAG</div>
          <div><Mail size={17} /> Reply Agent</div>
        </div>

        <div className="system-map">
          <div>
            <Network size={18} />
            <span>MCP tools</span>
            <small>image, tickets, email</small>
          </div>
          <div>
            <Database size={18} />
            <span>Qdrant + PostgreSQL</span>
            <small>manual search and ticket store</small>
          </div>
          <div>
            <BrainCircuit size={18} />
            <span>Local model</span>
            <small>qwen3:1.7b on Ollama</small>
          </div>
        </div>

        <div className="sidebar-note">
          <CheckCircle2 size={17} />
          <span>Runs locally in Docker Desktop with no cloud account required.</span>
        </div>
      </aside>

      <section className="support-panel">
        <header className="page-header">
          <div>
            <p>Fictional product support</p>
            <h1>AsterPump X17 Aftercare</h1>
          </div>
          <button className="secondary-button" onClick={lookupStatus} disabled={statusLoading} type="button">
            {statusLoading ? <Loader2 className="spin" size={18} /> : <Search size={18} />}
            Check latest status
          </button>
        </header>

        <div className="content-grid">
          <form className="panel support-form" onSubmit={submitTicket}>
            <label>
              Customer email
              <span className="input-icon">
                <Mail size={17} />
                <input value={email} onChange={(event) => setEmail(event.target.value)} type="email" required />
              </span>
            </label>

            <label>
              Error photo
              <span className="file-input">
                <Camera size={18} />
                <input
                  onChange={(event) => setPhoto(event.target.files?.[0] ?? null)}
                  type="file"
                  accept="image/*,.txt"
                />
              </span>
              <small>Optional. Upload a screen image, or describe the issue in text below.</small>
            </label>

            <label>
              Description
              <textarea
                rows={5}
                value={description}
                onChange={(event) => setDescription(event.target.value)}
              />
            </label>

            <button className="primary-button" disabled={loading} type="submit">
              {loading ? <Loader2 className="spin" size={18} /> : <Send size={18} />}
              Start Support Ticket
            </button>
          </form>

          <section className="panel result-panel" aria-live="polite">
            {!ticket && !status && !error && (
              <div className="empty-state">
                <Wrench size={42} />
                <h2>Ready for an aftercare request</h2>
                <p>Upload an error photo and the LangGraph workflow will create a ticket, retrieve steps, and send a reply.</p>
              </div>
            )}

            {error && <div className="error">{error}</div>}

            {ticket && (
              <ResultCard
                title={`Ticket #${ticket.ticket_id} completed`}
                email={ticket.customer_email}
                status={ticket.status}
                errorCode={ticket.detected_error_code}
                objects={ticket.detected_objects}
                steps={ticket.technical_steps}
                emailSent={ticket.email_sent}
              />
            )}

            {status && (
              <ResultCard
                title={`Latest ticket #${status.ticket_id}`}
                email={status.customer_email}
                status={status.status}
                errorCode={status.detected_error_code}
                objects={[]}
                steps={status.technical_steps ?? "No technical steps stored yet."}
                emailSent={status.email_sent}
              />
            )}
          </section>
        </div>

        <section className="panel chat-panel" aria-labelledby="chat-title">
          <div className="chat-header">
            <div>
              <p>Ask the assistant</p>
              <h2 id="chat-title">Product manual or general questions</h2>
            </div>
            <label className="rag-toggle">
              <input
                checked={useRag}
                onChange={(event) => setUseRag(event.target.checked)}
                type="checkbox"
              />
              <span>
                <BookOpenText size={17} />
                Use Aster manual
              </span>
            </label>
          </div>

          <div className="chat-log" aria-live="polite">
            {chatMessages.length === 0 && (
              <div className="chat-empty">
                <MessageSquareText size={34} />
                <span>Ask about the Aster manual or switch the manual off for a general question.</span>
              </div>
            )}

            {chatMessages.map((message, index) => (
              <article className={`chat-message ${message.role}`} key={`${message.role}-${index}`}>
                <strong>{message.role === "user" ? "You" : "Assistant"}</strong>
                <p>{message.content}</p>
              </article>
            ))}
          </div>

          {chatError && <div className="error">{chatError}</div>}

          <form className="chat-form" onSubmit={sendChatQuestion}>
            <input
              aria-label="Question"
              value={chatQuestion}
              onChange={(event) => setChatQuestion(event.target.value)}
              placeholder={useRag ? "Ask about Bluefin, E-77, C2..." : "Ask a general question..."}
            />
            <button className="primary-button" disabled={chatLoading} type="submit">
              {chatLoading ? <Loader2 className="spin" size={18} /> : <Send size={18} />}
              Ask
            </button>
          </form>
        </section>
      </section>
    </main>
  );
}

function AgentWorkModal({
  open,
  ticket,
  error,
  onClose,
  onCheckStatus,
}: {
  open: boolean;
  ticket: TicketResponse | null;
  error: string | null;
  onClose: () => void;
  onCheckStatus: () => void;
}) {
  if (!open) {
    return null;
  }

  return (
    <div className="modal-backdrop" role="presentation">
      <section className="simple-info-modal" role="dialog" aria-modal="true" aria-labelledby="agent-modal-title">
        <button className="icon-button" type="button" aria-label="Close" onClick={onClose}>
          <X size={18} />
        </button>

        <span className="modal-icon">
          <Info size={30} />
        </span>

        <h2 id="agent-modal-title">Our Virtual Agent will work on your request</h2>

        <p className="modal-copy">
          Response will be sent to you in email. You can also check the latest request status here.
        </p>

        {ticket && (
          <div className="simple-ticket-number">
            Ticket #{ticket.ticket_id}
          </div>
        )}

        {error && <div className="error">{error}</div>}

        <div className="modal-actions">
          <button className="secondary-button" type="button" onClick={onCheckStatus}>
            <Search size={18} />
            Check status here
          </button>
          <button className="primary-button" type="button" onClick={onClose}>
            Back to home
          </button>
        </div>
      </section>
    </div>
  );
}

function ResultCard({
  title,
  email,
  status,
  errorCode,
  objects,
  steps,
  emailSent,
}: {
  title: string;
  email: string;
  status: string;
  errorCode: string | null;
  objects: string[];
  steps: string;
  emailSent: boolean;
}) {
  return (
    <article className="result-card">
      <div className="result-header">
        <h2>{title}</h2>
        <span>{status}</span>
      </div>
      <dl>
        <div>
          <dt>Email</dt>
          <dd>{email}</dd>
        </div>
        <div>
          <dt>Error code</dt>
          <dd>{errorCode ?? "Not detected"}</dd>
        </div>
        <div>
          <dt>Email sent</dt>
          <dd>{emailSent ? "Yes" : "No"}</dd>
        </div>
      </dl>
      {objects.length > 0 && (
        <div className="chips">
          {objects.map((item) => <span key={item}>{item}</span>)}
        </div>
      )}
      <h3>Technical steps</h3>
      <p className="steps">{steps}</p>
    </article>
  );
}

createRoot(document.getElementById("root")!).render(<App />);
