# Architecture Guide: Bluetide

This document defines the architectural standards for the Bluetide frontend. It follows a practical, feature-driven approach for a scalable Document Management System.

🌊 Architectural Philosophy
1. **Domain-Centricity**: Code is grouped by business features (e.g., Documents, Chat, Analytics).
2. **Provider-Slot Pattern**: Features use a Provider to manage logic/data and Slots to render the user interface.
3. **Semantic Theme Standardization**: The UI uses 100% semantic theme variables (e.g., `bg-background`, `text-muted-foreground`, `border-border`). **Hardcoded hex or slate/gray colors are strictly prohibited.**
4. **Linguistic Fluidity**: The UI is script-agnostic. Every component must support RTL (Arabic/Urdu) and LTR (English/Hindi) layouts natively using logical properties (`ps`, `pe`, `border-e`).

📂 Directory Structure
```
src/
├── features/               # Self-contained business domains
│   ├── chat/               # Conversational interface & Language matching
│   ├── documents/          # Library management & SharePoint/S3 syncing
│   └── processing/         # Pipeline status, OCR confidence, & logs
├── shared/                 # Foundation (Atomic Design)
│   ├── components/         # ui/ (Shadcn), layout/ (Hero, Sidebar, Header)
│   ├── hooks/              # use-direction, use-media-query, use-theme
│   ├── lib/                # cn helper, formatters, utils
│   └── types/              # Global schemas (Document, User, Language)
├── routes/                 # TanStack Router definitions
└── styles.css              # Global theme variables & Tailwind @layers
```

## 🛣️ TanStack Router (File-Based Routing)

This project uses **TanStack Router** with file-based routing. Routes are automatically generated from files in `src/routes/`.

### Route File Structure
- Each route file must use `createFileRoute()` to define the route
- The route path is determined by the file location (e.g., `src/routes/documents/upload.tsx` → `/documents/upload`)
- Route files are auto-imported in `src/routeTree.gen.ts` (DO NOT manually edit this file)

### Critical Rules for Route Files
1. **Always export a `Route` constant** using `createFileRoute()`
2. **Component function name doesn't matter** - it's passed to the `component` property
3. **Never leave placeholder/boilerplate content** - always implement the actual page component
4. **Wrap feature pages in their Provider** - e.g., `<Document.Root>` for document pages

### Example Route Implementation
```typescript
// ✅ CORRECT: Full implementation with feature components
import { createFileRoute } from '@tanstack/react-router'
import { Document } from '@/features/documents'

export const Route = createFileRoute('/documents/upload')({
  component: UploadPage,
})

function UploadPage() {
  return (
    <Document.Root>
      <div className="container max-w-7xl mx-auto py-8">
        <Document.Upload />
      </div>
    </Document.Root>
  )
}

// ❌ WRONG: Placeholder boilerplate
function RouteComponent() {
  return <div>Hello "/documents/upload"!</div>
}
```

### Route Generation
- The dev server watches for route file changes and regenerates `routeTree.gen.ts`
- If a new route doesn't appear, the dev server may need to be restarted
- Always verify route files contain actual implementations, not placeholders


🏗️ Core Patterns

1. The Provider-Slot Implementation
Each feature directory follows this structure to ensure state is decoupled from the layout.

```typescript
// features/documents/index.ts
export const Document = {
  Root: DocumentProvider,     // Context & Data fetching
  Table: DocumentTable,       // Data Display
  Filters: DocumentFilters,   // Search & Refinement
};
```

2. Standardized Feature Layout (Hero-Toolbar split)
Every feature page must implement a 3-tier hierarchy for clarity and focus:

```typescript
<Document.Root>
  <div className="space-y-6">
    {/* Tier 1. Minimal Hero: Page Context */}
    <Shared.Hero 
      variant="minimal"
      title="Document Library" 
      subtitle="Managed sources from SharePoint and AWS S3"
      icon={<Files />}
    />

    {/* Tier 2. Action Toolbar: Interaction Layer */}
    <div className="flex items-center justify-between border-y border-border/40 bg-card/30 px-4 py-2 rounded-lg">
       <Document.Filters />
       {/* Other contextual actions */}
    </div>

    {/* Tier 3. Body Content: Data Layer */}
    <div className="grid grid-cols-1 gap-6">
       <Document.Table />
    </div>
  </div>
</Document.Root>
```

🎨 Design Standards
- **Clean & Professional**: Use subtle colors and high-contrast text. Use 10-15% opacity backgrounds for indicators (e.g., `bg-emerald-500/15 text-emerald-400`).
- **Standardized Codes**: IDs and technical identifiers should use `<code>` tags with mono font and subtle borders.
- **Error States**: Use red tints (`bg-destructive/5`) for failed tasks.

🌍 Multi-language Support (RTL/LTR)
- **Flexible Layouts**: Always use "Start" and "End" properties (`ps-*`, `pe-*`, `ms-*`, `me-*`) instead of Left/Right to support languages like Arabic or Urdu automatically.

⚡ Data & Loading
- **Data Fetching**: Use TanStack Query for all API requests.
- **Loading States**: Show clear loading indicators (pulsing or spinning) when data is being processed.

🛠️ Clean Code Rules
- **No Global Props**: Components should get data from their specific feature context, not by passing props deep down.
- **Use Theme Variables**: Never use hardcoded colors. Always use theme tokens like `bg-background` or `text-primary`.
- **Consistent Typing**: Ensure all data matches the defined TypeScript types for reliability.
