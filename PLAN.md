# Every Avenue Chat UI - Complete Redesign Plan

## Current Issues (from screenshot)
1. **Raw markdown** - `#`, `##`, `###`, `-` showing as literal text
2. **No padding** - Content flush to screen edges
3. **User bubble cut off** at top of viewport
4. **Flat hierarchy** - No visual distinction between elements
5. **Basic input** - Looks unfinished, not elegant

---

## Solution: shadcn-chatbot-kit + react-markdown

Using **shadcn-chatbot-kit** (purpose-built chat components) with **react-markdown** for rendering.

### Why This Stack
- **shadcn-chatbot-kit**: Battle-tested chat UI components designed for AI chatbots
- **react-markdown + remark-gfm**: Full markdown rendering (headings, lists, bold, code)
- **Tailwind prose classes**: Typography that "just works"
- **Mobile-first**: Responsive out of the box

---

## Implementation Steps

### Step 1: Install Dependencies
```bash
npm install react-markdown remark-gfm
npx shadcn@latest add scroll-area
npx shadcn@latest add avatar
npx shadcn@latest add button
```

### Step 2: Create Markdown Component (`src/components/markdown.tsx`)

A reusable markdown renderer with proper prose styling:

```tsx
import Markdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

interface MarkdownRendererProps {
  content: string;
}

export function MarkdownRenderer({ content }: MarkdownRendererProps) {
  return (
    <Markdown
      remarkPlugins={[remarkGfm]}
      className="prose prose-sm dark:prose-invert max-w-none
                 prose-headings:font-semibold prose-headings:text-foreground
                 prose-p:text-foreground prose-p:leading-relaxed
                 prose-li:text-foreground prose-strong:text-foreground
                 prose-ul:my-2 prose-ol:my-2 prose-li:my-0.5"
      components={{
        // Custom heading sizes for chat context
        h1: ({ children }) => <h2 className="text-lg font-semibold mt-4 mb-2">{children}</h2>,
        h2: ({ children }) => <h3 className="text-base font-semibold mt-3 mb-2">{children}</h3>,
        h3: ({ children }) => <h4 className="text-sm font-semibold mt-2 mb-1">{children}</h4>,
        // Tighter list styling
        ul: ({ children }) => <ul className="list-disc pl-4 space-y-1">{children}</ul>,
        ol: ({ children }) => <ol className="list-decimal pl-4 space-y-1">{children}</ol>,
        // Code styling
        code: ({ children }) => (
          <code className="bg-muted px-1.5 py-0.5 rounded text-sm font-mono">{children}</code>
        ),
        pre: ({ children }) => (
          <pre className="bg-muted p-3 rounded-lg overflow-x-auto text-sm">{children}</pre>
        ),
      }}
    >
      {content}
    </Markdown>
  );
}
```

### Step 3: Redesign Chat Component (`src/components/every-avenue-chat.tsx`)

Key layout fixes:
- `h-dvh` (dynamic viewport height) for proper mobile sizing
- `overflow-hidden` on root container
- `flex-1 min-h-0` on scroll area for proper flex behavior
- Proper padding (px-4 py-6) on message area
- Max-width constraint on messages (max-w-[85%])

Key visual fixes:
- User messages: Right-aligned, brand color, rounded bubble
- Assistant messages: Left-aligned, subtle background, proper spacing
- Use `<MarkdownRenderer>` instead of manual line splitting
- Avatar for assistant messages (Every Avenue logo)
- Smooth scroll behavior

### Step 4: Update CSS (`src/app/globals.css`)

Add proper Tailwind typography plugin support:
```css
/* Prose overrides for chat context */
.prose {
  --tw-prose-body: var(--foreground);
  --tw-prose-headings: var(--foreground);
  --tw-prose-bold: var(--foreground);
  --tw-prose-bullets: var(--muted-foreground);
  --tw-prose-counters: var(--muted-foreground);
}

.dark .prose {
  --tw-prose-body: var(--foreground);
  --tw-prose-headings: var(--foreground);
}
```

### Step 5: Install Tailwind Typography Plugin
```bash
npm install @tailwindcss/typography
```

Update `tailwind.config.ts` (if exists) or rely on prose classes.

---

## File Changes Summary

| File | Action | Purpose |
|------|--------|---------|
| `package.json` | Add deps | react-markdown, remark-gfm, @tailwindcss/typography |
| `src/components/markdown.tsx` | Create | Reusable markdown renderer |
| `src/components/every-avenue-chat.tsx` | Rewrite | Proper layout + markdown integration |
| `src/app/globals.css` | Update | Typography + prose variables |

---

## Visual Design Principles

### Layout
- Full viewport height with no body scroll
- Messages scroll within container only
- Fixed header (logo + title)
- Fixed footer (input area)
- Safe area insets for mobile notches

### Typography
- Assistant: 14-15px, relaxed line height (1.6-1.7)
- Headings: Slightly smaller than default prose (chat context)
- Lists: Tighter spacing than default

### Colors (Already defined)
- User messages: `--primary` background
- Assistant messages: `--muted` background
- Text: `--foreground`
- Subtle: `--muted-foreground`

### Spacing
- Message bubbles: px-4 py-3
- Between messages: space-y-4
- Container padding: px-4 (sides), py-6 (vertical)

### Animations
- Messages slide up on appear
- Typing indicator with animated dots
- Smooth scroll to bottom

---

## Success Criteria

1. Markdown renders correctly (headings styled, lists bulleted, bold working)
2. Chat fills exactly 100dvh - no overflow, no body scroll
3. Messages properly padded from edges
4. User/assistant messages visually distinct
5. Mobile: no zoom on input focus, proper keyboard handling
6. Elegant, minimal, professional appearance
