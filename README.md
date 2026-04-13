# 🌊 Bluetide

**Bluetide** is a modern, high-density Intelligent Document Processing (IDP) Hub and Analytics dashboard. Designed for scalability and visual excellence, it provides a "Clean & Smart" interface for managing document lifecycles, processing pipelines, and conversational AI interactions.

[![React](https://img.shields.io/badge/React-19-61DAFB?logo=react&logoColor=black)](https://react.dev/)
[![Vite](https://img.shields.io/badge/Vite-7-646CFF?logo=vite&logoColor=white)](https://vitejs.dev/)
[![Tailwind CSS](https://img.shields.io/badge/Tailwind_CSS-4-06B6D4?logo=tailwind-css&logoColor=white)](https://tailwindcss.com/)
[![TanStack](https://img.shields.io/badge/TanStack-Router%2FQuery-FF4154?logo=react-query&logoColor=white)](https://tanstack.com/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5-3178C6?logo=typescript&logoColor=white)](https://www.typescriptlang.org/)

---

## ✨ Key Features

- 🏢 **IDP Hub**: Centralized management for document processing from sources like SharePoint and AWS S3.
- 📊 **Smart Analytics**: High-density dashboards built with Shadcn/ui for actionable insights.
- 💬 **Conversational AI**: Integrated chat interface for document querying and processing logs.
- 🌍 **Linguistic Fluidity**: Native support for RTL (Arabic/Urdu) and LTR (English) layouts using logical CSS properties.
- 🌗 **Theme Savvy**: Full dark/light mode support with 100% semantic theme variables.
- ⚡ **Command Rail**: A streamlined navigation architecture with feature-isolated sidebars and headers.

## 🏗️ Architecture

Bluetide follows a **Feature-Driven Modular Architecture**:

- **Domain-Centricity**: Code grouped by business features (e.g., `chat`, `documents`, `processing`).
- **Provider-Slot Pattern**: Decouples state logic from UI rendering, ensuring highly maintainable components.
- **Atomic Design**: Shared components follow atomic principles for maximum reusability.

```text
src/
├── features/       # Business domains (Chat, Documents, Processing)
├── shared/         # Foundation (UI components, Hooks, Global Types)
├── routes/         # TanStack Router definitions
└── styles.css      # Semantic theme variables
```

## 🚀 Getting Started

### Prerequisites

- Node.js (Latest LTS recommended)
- npm or pnpm
- [Python 3.12+](https://www.python.org/downloads/)
- [uv](https://github.com/astral-sh/uv) (Extremely fast Python package installer and resolver)

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/Asad-333/bluetide.git
   cd bluetide
   ```

2. Install dependencies for the UI:
   ```bash
   cd bluetide-ui
   npm install
   cd ..
   ```

3. Setup the Backend:
   ```bash
   cd backend
   uv venv
   source .venv/bin/activate  # On Windows use `.venv\Scripts\activate`
   uv sync
   cd ..
   ```

### Running the Application

#### Frontend (UI)
```bash
cd bluetide-ui
npm run dev
```
The UI will be available at `http://localhost:3000`.

#### Backend (API)
```bash
cd backend
# With virtual environment activated:
uvicorn main:app --reload
```
The API will be available at `http://localhost:8000`.
- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

## 🛠️ Tech Stack

### Frontend
- **Framework**: [React 19](https://react.dev/)
- **Build Tool**: [Vite 7](https://vitejs.dev/)
- **Routing**: [TanStack Router](https://tanstack.com/router)
- **State & Data**: [TanStack Query](https://tanstack.com/query) & [Zustand](https://docs.pmnd.rs/zustand)
- **Styling**: [Tailwind CSS 4](https://tailwindcss.com/)
- **UI Components**: [Shadcn UI](https://ui.shadcn.com/)
- **Icons**: [Lucide React](https://lucide.dev/)

### Backend
- **Framework**: [FastAPI](https://fastapi.tiangolo.com/)
- **Server**: [Uvicorn](https://www.uvicorn.org/)
- **Package Management**: [uv](https://github.com/astral-sh/uv)
- **Language**: Python 3.12+

## 🚢 Deployment

- Active deployment guide: [`DEPLOYMENT_CLOUDFLARE_LAMBDA.md`](/Users/zuhairhussain/Desktop/bluetide-B-5-2/DEPLOYMENT_CLOUDFLARE_LAMBDA.md)
- Archived App Runner files: [`ex-apprunner/`](/Users/zuhairhussain/Desktop/bluetide-B-5-2/ex-apprunner)

## 🧪 Testing

### Frontend
```bash
cd bluetide-ui
npm run test
```

### Backend
*(Tests coming soon)*

---

Built with 🌊 by the Bluetide Team.
