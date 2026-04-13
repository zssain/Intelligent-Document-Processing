# 📘 Teclusion AI — Intelligent Document Processing (IDP)

## Complete User Manual

**Version**: 2.4.0  
**Last Updated**: March 2026  
**Platform URL**: [https://hxqizugaaq.ap-south-1.awsapprunner.com](https://hxqizugaaq.ap-south-1.awsapprunner.com/login?redirect=%2F)

---

## Table of Contents

1. [Introduction](#1-introduction)
2. [Getting Started](#2-getting-started)
   - 2.1 [System Requirements](#21-system-requirements)
   - 2.2 [Accessing the Platform](#22-accessing-the-platform)
   - 2.3 [Logging In](#23-logging-in)
   - 2.4 [Creating an Account (Sign Up)](#24-creating-an-account-sign-up)
   - 2.5 [Demo Access](#25-demo-access)
3. [Understanding User Roles & Permissions](#3-understanding-user-roles--permissions)
   - 3.1 [Role Types](#31-role-types)
   - 3.2 [Clearance Levels](#32-clearance-levels)
   - 3.3 [Source Permissions](#33-source-permissions)
   - 3.4 [Category-Based Access](#34-category-based-access)
4. [Navigation & Interface Overview](#4-navigation--interface-overview)
   - 4.1 [Top Header Bar](#41-top-header-bar)
   - 4.2 [Navigation Rail (Sidebar)](#42-navigation-rail-sidebar)
   - 4.3 [User Profile Menu](#43-user-profile-menu)
   - 4.4 [Theme Toggle (Dark/Light Mode)](#44-theme-toggle-darklight-mode)
   - 4.5 [Language Selector](#45-language-selector)
5. [Dashboard (Admin Only)](#5-dashboard-admin-only)
   - 5.1 [Intelligence Overview](#51-intelligence-overview)
   - 5.2 [Stats Cards](#52-stats-cards)
   - 5.3 [AI Insights](#53-ai-insights)
   - 5.4 [System Health Status](#54-system-health-status)
   - 5.5 [Search / Chat Bar](#55-search--chat-bar)
6. [Document Library](#6-document-library)
   - 6.1 [Page Layout Overview](#61-page-layout-overview)
   - 6.2 [Ingestion Mode Selector](#62-ingestion-mode-selector)
   - 6.3 [Search and Filters](#63-search-and-filters)
   - 6.4 [Document Table](#64-document-table)
   - 6.5 [Document Preview Panel](#65-document-preview-panel)
   - 6.6 [Bulk Actions](#66-bulk-actions)
   - 6.7 [Pagination](#67-pagination)
7. [Document Ingestion](#7-document-ingestion)
   - 7.1 [Direct Upload (Admin Only)](#71-direct-upload-admin-only)
   - 7.2 [Amazon S3 Connector](#72-amazon-s3-connector)
   - 7.3 [Google Drive Connector](#73-google-drive-connector)
   - 7.4 [SharePoint Connector](#74-sharepoint-connector)
   - 7.5 [Connect via Link](#75-connect-via-link)
   - 7.6 [Syncing Files](#76-syncing-files)
   - 7.7 [Processing Files](#77-processing-files)
   - 7.8 [Job Tracker](#78-job-tracker)
8. [Document Processing Pipeline](#8-document-processing-pipeline)
   - 8.1 [Pipeline Stages](#81-pipeline-stages)
   - 8.2 [OCR & Language Detection](#82-ocr--language-detection)
   - 8.3 [AI-Powered Extraction](#83-ai-powered-extraction)
   - 8.4 [Embedding Generation](#84-embedding-generation)
   - 8.5 [Confidence Scores](#85-confidence-scores)
9. [AI Chat (RAG-Powered Q&A)](#9-ai-chat-rag-powered-qa)
   - 9.1 [Starting a Chat Session](#91-starting-a-chat-session)
   - 9.2 [Asking Questions](#92-asking-questions)
   - 9.3 [Document-Isolated Analysis Mode](#93-document-isolated-analysis-mode)
   - 9.4 [Retrieval Panel & Citations](#94-retrieval-panel--citations)
   - 9.5 [Chat Sidebar & Session History](#95-chat-sidebar--session-history)
   - 9.6 [Multilingual Support](#96-multilingual-support)
10. [Intelligence Audit (Analytics)](#10-intelligence-audit-analytics)
    - 10.1 [Metrics Overview](#101-metrics-overview)
    - 10.2 [Intelligence Matrix](#102-intelligence-matrix)
    - 10.3 [Live Processing Queue](#103-live-processing-queue)
    - 10.4 [Extraction Confidence](#104-extraction-confidence)
    - 10.5 [System Health Panel](#105-system-health-panel)
    - 10.6 [Export & Share](#106-export--share)
11. [Admin Panel](#11-admin-panel)
    - 11.1 [Admin Dashboard Overview](#111-admin-dashboard-overview)
    - 11.2 [User Management](#112-user-management)
    - 11.3 [Category Management](#113-category-management)
    - 11.4 [Audit Log](#114-audit-log)
12. [Troubleshooting & FAQ](#12-troubleshooting--faq)
13. [Glossary](#13-glossary)

---

## 1. Introduction

**Teclusion AI — Intelligent Document Processing (IDP)** is an enterprise-grade document intelligence platform that automates the ingestion, extraction, and analysis of documents from multiple sources. It combines advanced OCR, AI-powered semantic extraction, vector-based retrieval, and a conversational AI interface to transform unstructured documents into actionable, searchable knowledge.

### Key Capabilities

| Capability | Description |
|---|---|
| **Multi-Source Ingestion** | Ingest documents from Amazon S3, Google Drive, SharePoint, or direct upload |
| **AI Document Processing** | Automated OCR, language detection, and semantic field extraction using Docling + Gemini |
| **RAG-Powered AI Chat** | Ask questions about your documents with source-grounded citations |
| **Multilingual Support** | Full support for English and Arabic (RTL), with automatic language detection |
| **Role-Based Access Control** | Granular permissions with roles, clearance levels, source permissions, and category filtering |
| **Real-Time Analytics** | Intelligence dashboards with processing metrics, confidence analysis, and system health monitoring |
| **Audit Trail** | Complete audit logging of all user and system activities |

---

## 2. Getting Started

### 2.1 System Requirements

| Requirement | Minimum |
|---|---|
| **Browser** | Chrome 100+, Firefox 100+, Safari 16+, Edge 100+ |
| **Screen Resolution** | 1280 × 720 (1920 × 1080 recommended) |
| **Internet Connection** | Required (cloud-hosted application) |
| **JavaScript** | Must be enabled |

### 2.2 Accessing the Platform

Open your web browser and navigate to:

```
https://hxqizugaaq.ap-south-1.awsapprunner.com
```

If you are not logged in, you will be automatically redirected to the **Login** page.

### 2.3 Logging In

1. Navigate to the platform URL. You will see the **Login** page with the Teclusion AI branding.
2. Enter your **Email** (username) in the first field.
3. Enter your **Password** in the second field.
4. Click the **Sign In** button.
5. Upon successful authentication, you will be redirected to the **Documents** page (or the **Dashboard** if you are an admin).

> **Note**: If you enter incorrect credentials, an error message will appear below the form. Please verify your email and password and try again.

### 2.4 Creating an Account (Sign Up)

1. On the Login page, click the **"Sign Up"** link below the form (if available).
2. Enter your **Email Address**, a **Password** (minimum 6 characters), and **Confirm Password**.
3. Click the **Sign Up** button.
4. The system will create your account and set up your access permissions. This process may take up to 60 seconds.
5. Once setup is complete, you will be redirected to the main application.

> **Note**: Your account will be created with default permissions. An administrator can later modify your role, clearance level, categories, and source permissions.

### 2.5 Demo Access

The Login page includes two **quick-access demo buttons** for evaluation purposes:

| Button | Email | Password | Role |
|---|---|---|---|
| **Admin Demo** | `admin@teclusion.ai` | `qwerty123` | Org Admin (full access) |
| **Viewer Demo** | `user@teclusion.ai` | `qwerty123` | User (limited access) |

Simply click either button to instantly sign in with the corresponding demo account.

---

## 3. Understanding User Roles & Permissions

Teclusion AI uses a multi-layered permission system to control access to features, documents, and data sources.

### 3.1 Role Types

| Role | Description | Access Level |
|---|---|---|
| **`org_admin`** | Organization Administrator | Full access to all features, admin panel, dashboard, analytics, user management |
| **`analyst`** | Data Analyst | Access to documents, chat, analytics; no admin panel |
| **`user`** | Standard User | Access to documents and chat; no admin panel, dashboard, or analytics |
| **`viewer`** | View-Only User | Read-only access to documents; limited interactions |

### 3.2 Clearance Levels

Clearance levels (0–10) provide an additional security layer. Documents are assigned a classification level, and users can only access documents at or below their clearance level.

- **Level 0**: Public / Unrestricted documents
- **Level 1–3**: Internal documents
- **Level 4–7**: Confidential documents
- **Level 8–10**: Top secret / Restricted documents

### 3.3 Source Permissions

Each user can be granted granular permissions for each data source (S3, Google Drive, SharePoint, Direct Upload):

| Permission | Description |
|---|---|
| **View** | Can see files from this source in the document library |
| **Download** | Can download original files from this source |
| **Filter** | Can filter documents by this source |
| **Sync** | Can trigger sync/refresh operations on this source |
| **Preview** | Can open document previews from this source |

> **Note**: Org admins automatically have full permissions across all sources.

### 3.4 Category-Based Access

Documents are organized into categories (e.g., Invoice, Equipment Document, User Manual, Finance, Other). Users can be restricted to specific categories, ensuring they only see documents relevant to their role.

---

## 4. Navigation & Interface Overview

The application uses a modern, compact layout with a Navigation Rail on the left side and a Header bar at the top.

### 4.1 Top Header Bar

The persistent header bar runs across the top of every page and includes:

- **App Logo** and **Teclusion AI** branding
- **Breadcrumb / page context** information
- **Quick action buttons** (varies by page)

### 4.2 Navigation Rail (Sidebar)

The vertical Navigation Rail is fixed on the left side of the screen (64px wide). It provides icon-based navigation with tooltips on hover:

| Icon | Label | Route | Access |
|---|---|---|---|
| 📊 | **Dashboard** | `/` | Admin only |
| 📄 | **Documents** | `/documents` | All users |
| 💬 | **Chat** | `/chat` | All users |
| 📈 | **Analytics** | `/analytics` | Admin only |
| 🛡️ | **Admin** | `/admin` | Admin only |
| ⚙️ | **Settings** | `/admin` (admins) / `/documents` (users) | All users |

At the bottom of the rail you'll find:
- **Language Toggle** — Switch between English and Arabic
- **Settings Icon** — Quick access to admin/settings
- **User Avatar** — Click to open the user profile popover

### 4.3 User Profile Menu

Click your **avatar icon** at the bottom of the Navigation Rail to open a popover that displays:

- Your **email address**
- Your **role** badge (e.g., `org_admin`, `user`)
- Your **clearance level** badge (e.g., `Clearance 3`)
- A **Sign Out** button to log out of the application

### 4.4 Theme Toggle (Dark/Light Mode)

Teclusion AI supports both **dark mode** and **light mode**. To switch themes:

1. Click the **sun/moon icon** in the Navigation Rail or on the Login page.
2. The interface will instantly switch to the alternate theme.
3. Your preference is saved in local storage and persists across sessions.

> **Default**: Dark mode is enabled by default.

### 4.5 Language Selector

The platform supports **English (EN)** and **Arabic (AR)** with full RTL layout support:

1. Click the **language indicator** (e.g., "EN") in the Navigation Rail.
2. Select your preferred language from the dropdown.
3. The entire interface will update to the selected language, including navigation labels, form fields, and table headers.
4. Arabic mode automatically applies right-to-left (RTL) text direction.

---

## 5. Dashboard (Admin Only)

The Dashboard is the landing page for **Org Admin** users. It provides a high-level overview of the document processing system's health and activity.

> **Access**: Only users with the `org_admin` role can view the Dashboard. Other users are redirected to `/documents`.

### 5.1 Intelligence Overview

The Dashboard header displays:
- **Title**: "Intelligence Overview"
- **Subtitle**: "Real-time processing status"
- **System Status**: A live indicator showing the system's operational state (e.g., "OPTIMAL" in green)

### 5.2 Stats Cards

A grid of metric cards showing key system statistics:

| Metric | Description |
|---|---|
| **Total Documents** | Total number of documents in the system |
| **Documents Today** | Documents ingested in the last 24 hours |
| **Documents This Week** | Documents ingested in the last 7 days |
| **Total Chunks** | Total number of document chunks created for RAG |
| **Unique Entities** | Number of distinct named entities extracted |
| **Connected Files** | Files connected from external data sources |

### 5.3 AI Insights

A panel showing recent AI-generated insights about the document corpus, including:
- Processing trends and patterns
- Anomaly detection alerts
- Extraction quality summaries

### 5.4 System Health Status

A real-time health panel displaying:

| Service | Status |
|---|---|
| **Vector DB** | Connection health (Healthy / Degraded / Down) |
| **API Server** | Running state |
| **Firestore** | Database connection status |

### 5.5 Search / Chat Bar

A floating search/chat bar at the bottom of the Dashboard that allows admins to quickly ask questions about the document corpus without navigating to the Chat page.

---

## 6. Document Library

The Document Library (`/documents`) is the central hub for viewing, searching, filtering, and managing all processed documents.

### 6.1 Page Layout Overview

From top to bottom, the Documents page is organized as follows:

1. **Page Header** — "Document Library" title and subtitle
2. **Ingestion Mode Selector** — Four clickable cards to choose the ingestion source
3. **OAuth Connection Status** — Shows connection state for Google Drive/SharePoint
4. **Mode-Specific Content** — Upload form or connector sync UI depending on selected mode
5. **Search & Filter Bar** — Text search and advanced filter controls
6. **Document Table** — Full-featured data table with all documents
7. **Document Preview** — A slide-out panel with document details

### 6.2 Ingestion Mode Selector

At the top of the Documents page, four cards allow you to select the document ingestion mode:

| Mode | Icon | Description |
|---|---|---|
| **Amazon S3** | ☁️ | Connect to an AWS S3 bucket to sync and process files |
| **SharePoint** | 🔗 | Connect to a Microsoft SharePoint folder |
| **Google Drive** | 💾 | Connect to a Google Drive folder via OAuth |
| **Direct Upload** | ⬆️ | Upload files directly from your computer (Admin only) |

Click any card to activate that mode. The active mode is highlighted with a colored gradient and an "ACTIVE" badge.

> **Note**: The modes visible to you depend on your **source permissions**. Admins see all four modes.

### 6.3 Search and Filters

**Search**: Use the search input to filter documents by filename. Type your query and results filter in real-time.

**Advanced Filters**: Click the **Filters** button (gear icon) to open a filter popover with the following filter groups:

| Filter | Options |
|---|---|
| **Source** | Local, S3, SharePoint, Google Drive |
| **Stage** | Parsed, OCR Extraction, Generating Embeddings, Completed, Failed |
| **Language** | English, Arabic |
| **Category** | Invoice, Equipment Document, User Manual, Finance, Other |

- Click a filter chip to activate it (highlighted in primary color).
- Click it again to deactivate.
- Use **"Reset All"** to clear all active filters.
- Active filters are also displayed as badges below the search bar for quick reference and removal.

### 6.4 Document Table

The main table displays all documents with the following columns:

| Column | Description |
|---|---|
| **☐ (Checkbox)** | Select individual documents for bulk actions (Admin only) |
| **Name** | Document filename with file type icon, clickable to open preview |
| **Source** | Origin badge showing S3, SharePoint, GDrive, or LOCAL |
| **Stage** | Processing pipeline stage badge (Parsed → OCR Extraction → Generating Embeddings → Completed / Failed) |
| **Confidence** | AI extraction confidence percentage with color coding (🟢 ≥90%, 🟡 ≥70%, 🔴 <70%) |
| **Timestamp** | Upload date and last modified date |
| **Language** | Detected language (English or Arabic) |
| **Category** | Document category badge (Invoice, Equipment, Manual, Finance, Other) |
| **Identification** | Document fingerprint hash and unique UID |
| **Actions** | Three-dot menu (⋮) with More Info, Ask AI, and Delete options |

**Row Colors**:
- Normal rows have a subtle hover highlight
- **Failed** documents are tinted red for quick visual identification

### 6.5 Document Preview Panel

Click a document's **name** or select **"More Info"** from the actions menu to open the Document Preview sliding panel on the right side. The preview includes:

**Header Section**:
- Document name and unique ID
- Download button (if S3 URL available)
- Open in new tab button

**Stats Grid**:
- **Confidence**: Color-coded extraction confidence percentage
- **File Size**: Document file size

**Tabs**:

1. **Overview Tab** — Detailed document metadata:
   - Language (with Arabic display as عربي)
   - Category
   - Source
   - Classification Level
   - Processed Date

2. **Document Preview Tab** — Embedded iframe preview of the original document (if available via S3 URL), or a "No Visual Preview Available" fallback message.

### 6.6 Bulk Actions

**Admin users** can select multiple documents using the checkboxes and perform bulk actions:

1. **Select documents** using individual checkboxes or the "Select All" checkbox in the header.
2. A **bulk actions toolbar** appears above the table showing:
   - Number of selected documents
   - **Delete Selected** — Delete all selected documents (with a 3-second countdown confirmation)
   - **Ask AI** — Open a chat session pre-loaded with the selected documents for analysis
   - **Cancel** — Clear selection

**Delete Confirmation Process**:
1. Click **"Delete Selected"**.
2. The toolbar turns red with the message *"Are you sure? (3…2…1…)"*.
3. Wait for the countdown to reach 0.
4. Click **"Delete Now"** to confirm, or **"Cancel"** to abort.

### 6.7 Pagination

Below the Document Table, pagination controls are displayed:

- **"Showing X to Y of Z documents"** — Current range indicator
- **Previous / Next** buttons — Navigate between pages
- **"Page X of Y"** — Current page indicator

---

## 7. Document Ingestion

### 7.1 Direct Upload (Admin Only)

When the **Direct Upload** mode is active, admin users see an upload interface:

1. **Drag & Drop Zone** — Drag files from your desktop onto the dropzone area, or click to open a file picker.
2. **File Queue** — Uploaded files appear in a queue showing:
   - File name, size, and status
   - Duplicate detection (skipped files are marked)
   - Remove button for individual files
3. **Action Bar** — A sticky bottom bar appears showing:
   - Count of ready files and skipped (duplicate) files
   - **Cancel** — Clear the queue
   - **Process** — Start processing all queued files through the pipeline

### 7.2 Amazon S3 Connector

When the **S3** mode is active:

1. Files are automatically synced from the configured S3 bucket.
2. Use the **Sync Toolbar** to manually trigger synchronization.
3. The **File Table** displays all files discovered in S3.
4. Select files and click **Process** to run them through the IDP pipeline.

### 7.3 Google Drive Connector

When the **Google Drive** mode is active:

1. **Connection Status Banner** — Shows whether your Google account is connected.
   - If **not connected**: Click the **"Connect"** button to open a Google OAuth popup.
   - Authorize Teclusion AI to access your Google Drive.
   - Once authorized, the banner turns green showing your connected email.
2. Use **"Connect via Link"** to paste a Google Drive folder URL directly.
3. **Sync** to list all files in the connected folder.
4. **Select** files and **Process** them through the pipeline.

**To disconnect Google Drive**:
- Click the **"Disconnect"** button in the connection status banner.

### 7.4 SharePoint Connector

When the **SharePoint** mode is active:

1. SharePoint may use **app-only credentials** (admin-configured) or **per-user OAuth**.
2. If using app-only mode, the status banner shows "SharePoint connected via admin credentials."
3. Paste a SharePoint folder URL using the **"Connect via Link"** dialog.
4. **Sync** and **Process** files as with other connectors.

### 7.5 Connect via Link

The **Connect via Link** section is available in Google Drive and SharePoint modes:

1. Click the collapsible **"Connect via Link"** header to expand the form.
2. Paste a **Google Drive folder URL** (e.g., `https://drive.google.com/drive/folders/...`) or a **SharePoint URL** (e.g., `https://yourorg.sharepoint.com/...`).
3. Optionally add a **label** (e.g., "HR Documents") for easy identification.
4. Click **"Connect & List Files"** to verify access and list the files.
5. On success, a confirmation message shows the number of files found.
6. The connection appears in the **Linked Sources** list below.

**Linked Sources List**:
- Shows the provider icon, label, file count, and connection date.
- Hover to reveal action buttons:
  - **Open original URL** — Opens the source folder in a new tab.
  - **Browse files** — Load the connection's files into the file table.
  - **Disconnect** — Remove the linked source.

### 7.6 Syncing Files

The **Sync Toolbar** provides buttons for refreshing the file list from connected sources:

| Button | Description |
|---|---|
| **Sync Now** | Quick sync — fetches up to 10 new/changed files |
| **Full Resync** | Force rescan — performs a complete scan of the source |
| **Refresh List** | Reload the file list from cache without contacting the source |

After a sync, the toolbar shows a results summary:
- **Ingested**: New files added
- **Updated**: Existing files that were refreshed
- **Skipped**: Files already up-to-date
- **Failed**: Files that failed to sync (shown in red)

### 7.7 Processing Files

To process files through the IDP pipeline:

1. Select files in the **File Table** using checkboxes.
2. A **Process Bar** appears at the bottom showing:
   - Number of selected files.
   - **Process [N] Files** button.
3. Click to start processing. A **processing job** is created.

### 7.8 Job Tracker

When a processing job is created, the **Job Tracker** panel appears:

- Shows the **Job ID** and real-time **status updates**.
- Displays progress as files move through pipeline stages.
- Can be dismissed once the job completes.

---

## 8. Document Processing Pipeline

### 8.1 Pipeline Stages

Every document passes through the following stages:

```
Upload/Sync → Parsed → OCR Extraction → Generating Embeddings → Completed
                                                                    ↘ Failed
```

| Stage | Description |
|---|---|
| **Parsed** | Document has been received and basic metadata extracted |
| **OCR Extraction** | Docling is converting the document to markdown; Gemini is performing semantic extraction |
| **Generating Embeddings** | Text chunks are being converted to vector embeddings for RAG |
| **Completed** | All processing is done; the document is fully searchable and queryable |
| **Failed** | An error occurred during processing; check the error details in the document preview |

### 8.2 OCR & Language Detection

- **Docling** performs local document-to-markdown conversion with built-in OCR.
- **Language Detection**: The system automatically detects the document language (English, Arabic, etc.) during the extraction phase.
- **Arabic Support**: Full OCR support for Arabic text, preserving right-to-left text direction and Arabic script.

### 8.3 AI-Powered Extraction

**Gemini AI** performs intelligent semantic extraction:

- Identifies and extracts structured fields from documents (dates, amounts, entities, etc.)
- Classifies documents into categories (Invoice, Equipment Document, User Manual, Finance, Other)
- Determines the document language with confidence scoring
- Generates document fingerprints for deduplication

### 8.4 Embedding Generation

After extraction, document text is:

1. **Chunked** into semantically meaningful segments
2. **Embedded** into high-dimensional vectors using a vector embedding model
3. **Stored** in a vector database (with pgvector support) for semantic search

### 8.5 Confidence Scores

Each processed document receives a **confidence score** (0–100%) indicating the quality of the AI extraction:

| Range | Color | Meaning |
|---|---|---|
| **90–100%** | 🟢 Green | High confidence — extraction is reliable |
| **70–89%** | 🟡 Amber | Moderate confidence — review recommended |
| **0–69%** | 🔴 Red | Low confidence — manual review strongly advised |

---

## 9. AI Chat (RAG-Powered Q&A)

The AI Chat feature (`/chat`) lets you ask questions about your documents using Retrieval-Augmented Generation (RAG). Answers are grounded in your actual document content with verifiable citations.

### 9.1 Starting a Chat Session

1. Navigate to **Chat** from the Navigation Rail.
2. You'll see the **Chat Start View** with:
   - Language icons (EN / عربي) indicating multilingual support
   - A large heading: *"Ask anything about [N] documents"*
   - Suggestion cards with sample queries (e.g., "Revenue insights", "Document translation")
3. Type your question in the **chat input** at the bottom and press Enter or click Send.

### 9.2 Asking Questions

- Type any natural language question in the **chat input field** at the bottom of the page.
- The AI will search through your document library, find relevant passages, and generate a comprehensive answer.
- Responses include **source citations** as clickable chips showing which documents were used.
- A disclaimer note reminds you to *"verify critical information using the provided source chips."*

**Example Questions**:
- *"What are the payment terms in the latest invoice?"*
- *"Summarize the safety procedures from the equipment manuals"*
- *"What is the total revenue mentioned across all financial documents?"*
- *"ما هي شروط الدفع في الفاتورة الأخيرة؟"* (Arabic queries are fully supported)

### 9.3 Document-Isolated Analysis Mode

You can start the AI chat in **isolated analysis mode** focused on specific documents:

1. In the **Document Library**, select one or more documents using checkboxes.
2. Click **"Ask AI"** from the bulk actions toolbar, or select **"Ask AI"** from a single document's action menu.
3. You'll be taken to the Chat page with those documents as the exclusive context.

When in isolated mode:
- A green **"Analysis Mode"** banner appears showing the number of focused documents.
- A **"Strict Grounding Active"** badge confirms the AI will only use content from those specific documents.
- The Retrieval Panel shows **"STRICT"** mode instead of **"GENERAL"**.
- The AI will not use information from other documents in your library.

### 9.4 Retrieval Panel & Citations

Click the **panel toggle icon** (top-right) to open/close the **Retrieval Panel** sidebar:

**Retrieval Mode Indicator**:
- **GENERAL** — Searching the global document library
- **STRICT** — Isolated to specific documents

**Active Context** (Strict mode only):
- Lists the documents being analyzed with file icons

**Latest Citations**:
- After each AI response, the Retrieval Panel shows the source documents used
- Each citation displays the document name with a verified shield icon
- Click **"View Global Library"** to navigate back to the document library

### 9.5 Chat Sidebar & Session History

The left sidebar in Chat view provides:

- **New Chat** button to start a fresh session
- **Session History** — List of all previous chat sessions with titles
- Click a session to resume it with its full message history

### 9.6 Multilingual Support

The AI Chat system fully supports **English** and **Arabic**:

- Ask questions in either language
- The AI responds in the same language as your question
- Arabic responses maintain proper RTL text direction
- Document citations work correctly for both English and Arabic source documents

---

## 10. Intelligence Audit (Analytics)

The Intelligence Audit page (`/analytics`) provides comprehensive analytics about your document processing pipeline.

> **Access**: Only users with the `org_admin` role can view Analytics. Other users will not see the Analytics item in the navigation.

### 10.1 Metrics Overview

The top of the analytics page shows **Smart Metric Cards** with key performance indicators:

- Total documents processed
- Processing success rate
- Average confidence score
- Active processing jobs

A **Top Insight** banner highlights the most important trend or recommendation.

### 10.2 Intelligence Matrix

An interactive matrix visualization showing:
- Document type distribution
- Source distribution
- Language breakdown
- Category breakdown

### 10.3 Live Processing Queue

A real-time view of documents currently being processed through the pipeline:
- Shows each document's current stage
- Progress indicators
- Time elapsed
- Estimated time remaining

### 10.4 Extraction Confidence

A confidence analysis section showing:
- Distribution of confidence scores across all documents
- Trend of extraction quality over time
- Breakdown of confidence by document category and source

### 10.5 System Health Panel

Displays the health of critical system components:

| Component | Status Indicators |
|---|---|
| **Vector DB** | Healthy / Degraded / Down |
| **API Server** | Running / Stopped |
| **Firestore** | Connected / Disconnected |

### 10.6 Export & Share

Top-right action buttons allow you to:
- **Export Data** — Download analytics data in a standard format
- **Share** — Share the analytics view
- **More Options** — Additional configuration options

---

## 11. Admin Panel

The Admin Panel (`/admin`) provides organization-level management capabilities for system administrators.

> **Access**: Only users with the `org_admin` role can access the Admin Panel. Unauthorized users are redirected to `/documents`.

### 11.1 Admin Dashboard Overview

The Admin Dashboard landing page (`/admin`) displays:

**Stats Cards**:

| Card | Description |
|---|---|
| **Total Users** | Number of registered users in the organization |
| **Total Documents** | Number of documents in the system |
| **Total Chunks** | Number of document chunks for RAG retrieval |
| **Connected Files** | Files connected from external data sources |

**Quick Actions** — Three clickable cards linking to:
- **Manage Users** — Roles, permissions & access
- **Categories** — Organize documents
- **Audit Log** — Security & activity trail

**Recent Audit Events** — A feed of the latest 10 system events with:
- Event type badge
- Timestamp
- Entity type and ID
- Actor email

### 11.2 User Management

The User Management page (`/admin/users`) allows admins to manage all users in the organization.

**User List**:
- Searchable list of all users
- Each user card shows:
  - User avatar (initial letter)
  - Display name and email
  - Role badge (colored: amber for admin, blue for user)
  - Clearance level badge
  - Active/Inactive status badge

**Expanded User Panel** (click a user to expand):

1. **Role**:
   - Dropdown to change role: User, Org Admin, Analyst, Viewer
   - Changes take effect immediately

2. **Clearance Level**:
   - Slider control (0–10)
   - Real-time update as you drag

3. **Categories**:
   - Multi-select dropdown to assign allowed categories
   - Users will only see documents in their allowed categories

4. **Source Permissions**:
   - A **permission grid** showing all sources (S3, Google Drive, SharePoint, Direct Upload) vs. all actions (View, Download, Filter, Sync, Preview)
   - Toggle switches for each permission
   - An **"All"** toggle to grant/revoke all permissions for a source
   - **"Save Permissions"** button appears when changes are made
   - Org admin users show a notice: *"⚡ Org admins have full access to all sources and actions."* with all toggles locked to ON

**Refresh**: Click the **"Refresh"** button to reload the user list from the server.

### 11.3 Category Management

The Category Management page (`/admin/categories`) allows admins to create, edit, and delete document categories.

**Creating a Category**:
1. Click **"New Category"** button.
2. Fill in the form:
   - **Category Name** (required) — e.g., "Contract", "Legal", "HR"
   - **Description** — Brief description of the category's purpose
   - **Color** — Choose a color for visual identification using the color picker
3. Click **"Create"** to save.

**Editing a Category**:
1. Click the **pencil icon** on a category card.
2. Modify the name, description, or color.
3. Click **"Update"** to save changes.

**Deleting a Category**:
1. Click the **trash icon** on a category card.
2. The category will be permanently deleted.

> **Warning**: Deleting a category may affect documents that are assigned to it and users whose access is filtered by it.

**Category Cards** display:
- Color swatch
- Category name
- Description
- Edit and Delete action buttons

### 11.4 Audit Log

The Audit Log page (`/admin/audit-log`) provides a complete record of all system activities.

**Filters**:
- **Search by actor** — Filter events by the actor's email address
- **Event type filter** — Dropdown to filter by specific event types:
  - `USER_CREATED`, `USER_UPDATED`, `USER_DELETED`
  - `DOCUMENT_UPLOADED`, `DOCUMENT_DELETED`
  - `CATEGORY_CREATED`, `CATEGORY_UPDATED`
  - `LOGIN`, `LOGOUT`

**Audit Table Columns**:

| Column | Description |
|---|---|
| **Timestamp** | Date and time of the event |
| **Event Type** | Colored badge showing the type of activity |
| **Actor** | Email of the user who performed the action |
| **Details** | Additional information (JSON diff of changes) |
| **IP Address** | Source IP address of the request |

**Pagination**:
- Shows 20 events per page
- Page number buttons and Previous/Next navigation
- Event count summary

**Auto-Refresh**: The audit log automatically refreshes every 30 seconds to show the latest events.

---

## 12. Troubleshooting & FAQ

### Q: I can't log in. What should I do?
**A**: Verify that you're using the correct email and password. If using a demo account, use the exact credentials listed in Section 2.5. If the problem persists, clear your browser's local storage and cookies, then try again.

### Q: I don't see the Dashboard or Analytics pages.
**A**: These pages are only available to users with the `org_admin` role. If you need access, ask your organization administrator to change your role in the Admin Panel.

### Q: I can't see any documents in the library.
**A**: Check the following:
1. Ensure your account has the correct **source permissions** (View permission for the relevant source).
2. Check that your **categories** include categories that documents are assigned to.
3. Verify that your **clearance level** is high enough for the documents' classification levels.
4. Try **resetting all filters** to ensure no filter is unintentionally hiding documents.

### Q: Google Drive says "OAuth is not configured."
**A**: The server-side Google Drive OAuth credentials may not be set up. Contact your organization administrator to configure Google OAuth credentials on the backend.

### Q: Document processing is stuck at "OCR Extraction."
**A**: OCR processing can take several minutes for large or complex documents, especially those with Arabic text. If a document remains in this stage for more than 15 minutes, it may have failed silently — try checking the document's details in the preview panel.

### Q: The AI chat gives irrelevant answers.
**A**: Try the following:
1. Use **Document-Isolated Analysis Mode** (select specific documents and click "Ask AI") for focused answers.
2. Be more specific in your question.
3. Verify that the relevant documents have reached the **Completed** stage with high confidence scores.

### Q: How do I change the interface language to Arabic?
**A**: Click the language indicator (e.g., "EN") at the bottom of the Navigation Rail and select "AR - العربية". The entire interface will switch to Arabic with RTL layout.

### Q: Documents show 0% confidence.
**A**: This typically means the document is still being processed. Wait for the processing to complete (stage should be "Completed"). If confidence remains at 0% after completion, the AI extraction may have encountered difficulties with the document format.

### Q: How do I delete multiple documents at once?
**A**: Only admin users can delete documents. Select documents using checkboxes, click "Delete Selected" in the bulk actions bar, wait for the 3-second countdown, then confirm by clicking "Delete Now."

### Q: The sync from S3/SharePoint/Google Drive shows 0 new files.
**A**: This means all files in the source are already tracked by the system. If you've added new files to the source, try clicking **"Full Resync"** to force a complete scan instead of an incremental sync.

---

## 13. Glossary

| Term | Definition |
|---|---|
| **IDP** | Intelligent Document Processing — automated extraction of data from documents |
| **RAG** | Retrieval-Augmented Generation — AI technique that grounds answers in retrieved source documents |
| **OCR** | Optical Character Recognition — converting images of text into machine-readable text |
| **Docling** | Local document-to-markdown conversion engine with built-in OCR |
| **Gemini** | Google's AI model used for semantic field extraction and document understanding |
| **Vector Embedding** | A high-dimensional numerical representation of text, used for semantic search |
| **pgvector** | PostgreSQL extension for storing and querying vector embeddings |
| **Firestore** | Google Cloud Firestore — NoSQL database used for document metadata and user data |
| **Firebase Auth** | Google Firebase Authentication — manages user identity and JWT tokens |
| **JWT** | JSON Web Token — secure token containing user identity and claims (role, clearance, tenant) |
| **Custom Claims** | Additional data (role, clearance, tenant_id) embedded in the user's JWT token |
| **Clearance Level** | Numeric security level (0–10) controlling access to classified documents |
| **Classification Level** | Security level assigned to a document, controlling who can access it |
| **Source Permission** | Granular permission (view, download, filter, sync, preview) per data source |
| **Fingerprint** | A hash-based identifier used for detecting duplicate documents |
| **Chunk** | A segment of document text, created for embedding and retrieval |
| **Citation** | A reference to a source document used by the AI to generate an answer |
| **Strict Grounding** | Chat mode where AI answers are limited to only the selected documents |
| **OAuth** | Open Authorization — protocol for granting third-party access (Google Drive, SharePoint) |
| **Tenant** | An organizational unit in a multi-tenant architecture; isolates data between organizations |
| **RTL** | Right-to-Left — text direction used for Arabic and similar languages |
| **Navigation Rail** | The vertical sidebar containing navigation icons |
| **Sync** | The process of connecting to an external source and discovering/fetching files |
| **Ingestion** | The process of importing a file into the system for processing |
| **Pipeline** | The series of processing stages a document passes through (parse → OCR → embed → complete) |

---

*© 2026 Teclusion AI. All rights reserved.*  
*For support, contact: [support@teclusion.ai](mailto:support@teclusion.ai)*
