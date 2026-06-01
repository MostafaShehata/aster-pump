import React, { useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import {
  BookOpenText,
  Bot,
  BrainCircuit,
  Database,
  FileImage,
  Loader2,
  Mail,
  MessageSquareText,
  Network,
  Paperclip,
  Send,
  Ticket,
  Trash2,
  Wrench,
  X,
} from "lucide-react";
import "./styles.css";

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

const examples = [
  {
    label: "Create text ticket",
    message: "Create ticket. The display shows E-77 on my AsterPump X17.",
    useRag: true,
  },
  {
    label: "List tickets",
    message: "List my tickets",
    useRag: false,
  },
  {
    label: "Latest status",
    message: "Get latest ticket status",
    useRag: false,
  },
  {
    label: "Ask manual",
    message: "What is Bluefin mode?",
    useRag: true,
  },
  {
    label: "General question",
    message: "Where is Egypt?",
    useRag: false,
  },
];

function App() {
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      role: "assistant",
      content:
        "Hello. I can create support tickets from text or an uploaded pump screen image, list your tickets, check latest status, answer from the AsterPump manual, or answer general questions.",
    },
  ]);
  const [email, setEmail] = useState("customer@example.com");
  const [draft, setDraft] = useState("");
  const [photo, setPhoto] = useState<File | null>(null);
  const [useRag, setUseRag] = useState(true);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  async function sendMessage(event?: React.FormEvent) {
    event?.preventDefault();
    const text = draft.trim();
    if (!text && !photo) {
      setError("Type a message or attach an image first.");
      return;
    }

    const userText = buildUserMessage(text, photo);
    const history = messages.slice(-8);
    const formData = new FormData();
    formData.append("message", text || "Create a support ticket from the uploaded image.");
    formData.append("customer_email", email.trim());
    formData.append("history", JSON.stringify(history));
    formData.append("use_rag", String(useRag));
    if (photo) {
      formData.append("photo", photo);
    }

    setLoading(true);
    setError(null);
    setMessages((current) => [...current, { role: "user", content: userText }]);

    try {
      const response = await fetch("/api/chat/upload", {
        method: "POST",
        body: formData,
      });
      if (!response.ok) {
        throw new Error(`Backend returned HTTP ${response.status}`);
      }

      const data = (await response.json()) as ChatResponse;
      const sources = data.sources.length > 0 ? `\n\nSources: ${data.sources.join(", ")}` : "";
      setMessages((current) => [
        ...current,
        {
          role: "assistant",
          content: `${data.reply}${sources}`,
        },
      ]);
      setDraft("");
      setPhoto(null);
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
    } catch (caught) {
      const message = caught instanceof Error ? caught.message : "Unknown chat failure";
      setError(message);
      setMessages((current) => [...current, { role: "assistant", content: message }]);
    } finally {
      setLoading(false);
    }
  }

  function applyExample(message: string, exampleUseRag: boolean) {
    setDraft(message);
    setUseRag(exampleUseRag);
    setError(null);
  }

  function clearConversation() {
    setMessages([]);
    setDraft("");
    setPhoto(null);
    setError(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  }

  return (
    <main className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <Wrench size={28} />
          <div>
            <strong>Aster Pump Aftercare</strong>
            <span>Chat-first local support console</span>
          </div>
        </div>

        <section className="side-section">
          <p>What this chat can do</p>
          <div className="capability"><Ticket size={17} /> Create a ticket from text or image</div>
          <div className="capability"><Database size={17} /> List tickets and latest status</div>
          <div className="capability"><BookOpenText size={17} /> Answer from the pump manual</div>
          <div className="capability"><BrainCircuit size={17} /> Answer normal model questions</div>
        </section>

        <section className="side-section">
          <p>How the flow is wired</p>
          <div className="flow-step"><MessageSquareText size={17} /> Browser sends one chat request</div>
          <div className="flow-step"><Bot size={17} /> Backend LLM chooses answer or tool</div>
          <div className="flow-step"><Network size={17} /> MCP calls image, DB, and email tools</div>
          <div className="flow-step"><Mail size={17} /> Reply returns to chat</div>
        </section>
      </aside>

      <section className="chat-page">
        <header className="page-header">
          <div>
            <p>Local Docker PoC</p>
            <h1>Aftercare Chat</h1>
          </div>
          <button className="secondary-button" type="button" onClick={clearConversation}>
            <Trash2 size={18} />
            Clear
          </button>
        </header>

        <section className="customer-strip" aria-label="Customer identity">
          <label>
            <span><Mail size={17} /> Customer email</span>
            <input
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              type="email"
              placeholder="customer@example.com"
            />
          </label>
          <p>This email is sent with every chat request and used when the assistant needs ticket tools.</p>
        </section>

        <section className="chat-card" aria-label="Aftercare chat">
          <div className="example-row">
            {examples.map((example) => (
              <button
                className="example-button"
                key={example.label}
                type="button"
                onClick={() => applyExample(example.message, example.useRag)}
              >
                {example.label}
              </button>
            ))}
          </div>

          <div className="chat-log" aria-live="polite">
            {messages.length === 0 && (
              <div className="empty-chat">
                <MessageSquareText size={38} />
                <span>Start with a ticket request, ticket lookup, manual question, or general question.</span>
              </div>
            )}

            {messages.map((message, index) => (
              <article className={`chat-message ${message.role}`} key={`${message.role}-${index}`}>
                <strong>{message.role === "user" ? "You" : "Assistant"}</strong>
                <p>{message.content}</p>
              </article>
            ))}

            {loading && (
              <article className="chat-message assistant">
                <strong>Assistant</strong>
                <p><Loader2 className="spin inline-icon" size={16} /> Thinking and checking tools...</p>
              </article>
            )}
          </div>

          {error && <div className="error">{error}</div>}

          {photo && (
            <div className="attachment-pill">
              <FileImage size={17} />
              <span>{photo.name}</span>
              <button
                aria-label="Remove attachment"
                type="button"
                onClick={() => {
                  setPhoto(null);
                  if (fileInputRef.current) {
                    fileInputRef.current.value = "";
                  }
                }}
              >
                <X size={16} />
              </button>
            </div>
          )}

          <form className="composer" onSubmit={sendMessage}>
            <input
              ref={fileInputRef}
              className="hidden-file"
              type="file"
              accept="image/*"
              onChange={(event) => setPhoto(event.target.files?.[0] ?? null)}
            />
            <button
              className="icon-button"
              type="button"
              title="Attach error screen image"
              onClick={() => fileInputRef.current?.click()}
            >
              <Paperclip size={20} />
            </button>
            <textarea
              aria-label="Message"
              value={draft}
              onChange={(event) => setDraft(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === "Enter" && !event.shiftKey) {
                  event.preventDefault();
                  void sendMessage();
                }
              }}
              placeholder="Ask a question, create a ticket, list tickets, or attach an image..."
              rows={3}
            />
            <div className="composer-actions">
              <label className="rag-toggle">
                <input
                  checked={useRag}
                  onChange={(event) => setUseRag(event.target.checked)}
                  type="checkbox"
                />
                <span><BookOpenText size={17} /> Use manual</span>
              </label>
              <button className="primary-button" disabled={loading} type="submit">
                {loading ? <Loader2 className="spin" size={18} /> : <Send size={18} />}
                Send
              </button>
            </div>
          </form>
        </section>
      </section>
    </main>
  );
}

function buildUserMessage(text: string, photo: File | null): string {
  if (text && photo) {
    return `${text}\n\nAttached image: ${photo.name}`;
  }
  if (photo) {
    return `Attached image: ${photo.name}`;
  }
  return text;
}

createRoot(document.getElementById("root")!).render(<App />);
