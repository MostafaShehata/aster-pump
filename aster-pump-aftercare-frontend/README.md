# Aster Pump Aftercare Frontend

React user interface for the Aster Pump Aftercare PoC.

This app is the customer-facing screen. It lets the user:

- enter customer email
- upload an error photo
- start a support ticket
- see a simple virtual-agent message
- check the latest ticket status
- view returned troubleshooting steps
- ask product-manual questions with RAG enabled
- ask general questions with RAG disabled

## Technology Brief

### React

React is used for the UI because it is lightweight, familiar, and works well for
interactive forms and state updates.

### Vite

Vite builds the React app into static files in `dist`.

### Nginx

The Docker container uses Nginx only to serve the already-built `dist` folder
and proxy browser `/api/*` calls to the backend.

## Important Files

| File | Function |
| --- | --- |
| `src/main.tsx` | Main React app, form handling, status lookup, modal, result rendering, and chat UI. |
| `src/styles.css` | UI layout and component styling. |
| `nginx.conf` | Serves React and proxies `/api` to backend. |
| `build-app.ps1` | Builds React locally into `dist`. |
| `build-image.ps1` | Runs app build, then builds local Docker image. |
| `Dockerfile` | Packages `dist` into Nginx. |

## Code Walkthrough

### React State

```tsx
const [email, setEmail] = useState("customer@example.com");
const [description, setDescription] = useState("");
const [photo, setPhoto] = useState<File | null>(null);
const [ticket, setTicket] = useState<TicketResponse | null>(null);
const [status, setStatus] = useState<TicketStatus | null>(null);
const [chatQuestion, setChatQuestion] = useState("What is Bluefin mode?");
const [chatMessages, setChatMessages] = useState<ChatMessage[]>([]);
const [useRag, setUseRag] = useState(true);
```

Explanation:

- `email`, `description`, and `photo` hold the form inputs.
- `ticket` stores the response after creating a new ticket.
- `status` stores the response when checking latest ticket status.
- `chatQuestion` stores the current assistant question.
- `chatMessages` stores the visible chat history.
- `useRag` controls whether the backend searches the Aster manual before
  calling the model.

### Submit Ticket

```tsx
const formData = new FormData();
formData.append("customer_email", email);
formData.append("description", description);
formData.append("photo", photo);
```

Explanation:

- Image upload requires `FormData`.
- Field names must match the backend endpoint:
  `customer_email`, `description`, and `photo`.

```tsx
const response = await fetch("/api/support/tickets", {
  method: "POST",
  body: formData,
});
```

Explanation:

- The browser calls `/api/support/tickets`.
- Nginx forwards `/api/*` to the backend container.

### Check Latest Status

```tsx
const response = await fetch(`/api/support/tickets?email=${encodeURIComponent(email)}`);
```

Explanation:

- This asks the backend for the latest ticket for the entered email.
- `encodeURIComponent` makes the email safe inside a URL.

### Result Panel

```tsx
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
```

Explanation:

- `ResultCard` is reused for new-ticket results and status results.
- Latest status does not return detected object labels, so `objects={[]}`.

### Assistant Chat

```tsx
const response = await fetch("/api/chat", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    message,
    history,
    use_rag: useRag,
  }),
});
```

Explanation:

- The chat panel calls the backend `/api/chat` endpoint.
- `message` is the current user question.
- `history` is the recent chat history so the model has short conversation
  context.
- `use_rag` tells the backend whether to search the Aster Pump manual.

```tsx
<input
  checked={useRag}
  onChange={(event) => setUseRag(event.target.checked)}
  type="checkbox"
/>
```

Explanation:

- When checked, the model receives retrieved Aster manual context.
- Use this for questions like `What is Bluefin mode?`.
- When unchecked, the model answers from general knowledge.
- Use this for questions like `Where is Egypt?`.

```tsx
const sourceLine = data.sources.length > 0 ? `\n\nSources: ${data.sources.join(", ")}` : "";
```

Explanation:

- RAG answers can include source file names.
- General answers normally have no sources.

### Fixed Form Height

```css
.content-grid {
  align-items: start;
}

.support-form {
  align-self: start;
  height: 560px;
}
```

Explanation:

- CSS grid normally stretches columns to match the tallest content.
- `align-items: start` prevents the form from stretching when the ticket result
  is long.
- The form keeps a stable desktop height.

## Nginx Proxy

```nginx
location /api/ {
    proxy_pass http://aster-pump-aftercare-backend:8000/api/;
}
```

Explanation:

- The browser only talks to the frontend container.
- Nginx forwards API calls to the backend over the Docker Compose network.

## Build And Deployment

See:

```text
BUILD_AND_DEPLOY.md
```
