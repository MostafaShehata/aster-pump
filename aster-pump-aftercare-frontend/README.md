# Aster Pump Aftercare Frontend

React chat UI for the Aster Pump Aftercare PoC.

The frontend is now one simple chat screen. The user enters customer email once
at the top of the page, types a message, attaches an optional pump screen image,
enables or disables manual/RAG context, and sends the request to the backend.

## Technology Brief

### React

React is used because the UI is an interactive chat surface with local state:
messages, upload selection, loading state, RAG toggle, and error display.

### Vite

Vite builds the React app locally into the `dist` folder.

### Nginx

The container does not run Node.js. It only serves the already-built `dist`
folder with Nginx and proxies browser `/api/*` calls to the backend.

## User Functions

- create a ticket from typed text
- create a ticket from an uploaded image plus the page-level email
- list tickets for the page-level email
- get latest ticket status
- ask manual/RAG questions such as `What is Bluefin mode?`
- ask general model questions such as `Where is Egypt?`

## Important Files

| File | Function |
| --- | --- |
| `src/main.tsx` | Single chat UI, image upload, RAG toggle, examples, API call. |
| `src/styles.css` | Layout, sidebar, chat log, composer, responsive styling. |
| `nginx.conf` | Serves React and proxies `/api` to backend. |
| `build-app.ps1` | Runs local frontend build into `dist`. |
| `build-image.ps1` | Builds the React app, then builds the local Nginx image. |
| `Dockerfile` | Copies `dist` into Nginx. |

## Code Walkthrough

### Chat State

```tsx
const [messages, setMessages] = useState<ChatMessage[]>([
  {
    role: "assistant",
    content: "Hello. I can create support tickets from text or an uploaded pump screen image...",
  },
]);
const [draft, setDraft] = useState("");
const [email, setEmail] = useState("customer@example.com");
const [photo, setPhoto] = useState<File | null>(null);
const [useRag, setUseRag] = useState(true);
```

Explanation:

- `messages` is the visible conversation.
- `draft` is the text currently typed by the user.
- `email` is the page-level customer email sent with every request.
- `photo` is the optional image attachment.
- `useRag` controls whether the backend searches the local manual.

### Customer Email

```tsx
<input
  value={email}
  onChange={(event) => setEmail(event.target.value)}
  type="email"
  placeholder="customer@example.com"
/>
```

Explanation:

- The user does not need to type the email inside every chat message.
- The email is sent as a separate multipart field named `customer_email`.
- The backend uses it only when the request needs ticket tools.
- General questions and manual questions remain clean chat text.

### Sending Text And Optional Image

```tsx
const formData = new FormData();
formData.append("message", text || "Create a support ticket from the uploaded image.");
formData.append("customer_email", email.trim());
formData.append("history", JSON.stringify(history));
formData.append("use_rag", String(useRag));
if (photo) {
  formData.append("photo", photo);
}
```

Explanation:

- The route uses multipart form data because it may contain an image.
- The same endpoint handles text-only chat and image-plus-text ticket creation.
- `customer_email` lets the backend list tickets, get latest status, and create
  tickets even when the chat text only says `List my tickets`.
- `history` lets the backend include short conversation context.
- The image is uploaded only when the user attaches one.

### Backend Call

```tsx
const response = await fetch("/api/chat/upload", {
  method: "POST",
  body: formData,
});
```

Explanation:

- The browser calls one route for all chat actions.
- Nginx forwards `/api/chat/upload` to the FastAPI backend.
- The backend asks the local model whether to answer or call an MCP tool.

### Example Buttons

```tsx
const examples = [
  { label: "Create text ticket", message: "Create ticket. The display shows E-77...", useRag: true },
  { label: "List tickets", message: "List my tickets", useRag: false },
  { label: "Ask manual", message: "What is Bluefin mode?", useRag: true },
];
```

Explanation:

- These buttons only fill the composer and set the RAG toggle.
- They do not bypass the chat flow.
- Sending still goes through `/api/chat/upload`.

### Image Attachment

```tsx
<input
  ref={fileInputRef}
  className="hidden-file"
  type="file"
  accept="image/*"
  onChange={(event) => setPhoto(event.target.files?.[0] ?? null)}
/>
```

Explanation:

- The real file input is hidden so the UI can use an icon button.
- Only image files are accepted.
- The backend logs the image size and content type, not raw image bytes.

### Manual/RAG Toggle

```tsx
<input
  checked={useRag}
  onChange={(event) => setUseRag(event.target.checked)}
  type="checkbox"
/>
```

Explanation:

- When checked, backend searches Qdrant for manual chunks.
- When unchecked, backend asks the local model without manual context.
- Ticket creation can still use RAG internally to select troubleshooting steps.

## Build And Deployment

Build the app locally:

```powershell
.\build-app.ps1
```

Build the local Docker image:

```powershell
.\build-image.ps1
```

The Dockerfile expects the built `dist` folder, so the application build remains
outside the container.

For the full stack, see:

```text
BUILD_AND_DEPLOY.md
```
