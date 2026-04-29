# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Environment Setup
```bash
# Install all dependencies
npm install

# Setup Python virtual environment (OS-specific)
npm run init:windows    # Windows
npm run init:default    # macOS  
npm run init:linux      # Linux (with Qt5/GTK setup)
```

### Development
```bash
# Start development server (frontend + Python backend)
npm start

# Frontend-only development
npm run dev             # Vite dev server on port 3000
```

### Building
```bash
# Clean build artifacts
npm run clean

# Build frontend only
npm run frontend:prod   # Outputs to gui/ directory

# Full production build (frontend + packaged executable)
npm run build           # Cross-platform
npm run build:windows   # Windows executable
npm run build:macos     # macOS app bundle
npm run build:linux     # Linux executable
```

## Architecture Overview

### Technology Stack
- **Backend**: Python with pywebview for desktop wrapper
- **Frontend**: React + TypeScript + Chakra UI + Vite
- **Database**: SQLite with SQLAlchemy ORM
- **Blockchain**: Dual-mode (Local ledger simulation + MintBlue BSV)
- **Packaging**: PyInstaller for desktop executables

### Application Structure
The app uses a hybrid Python-JavaScript architecture:

1. **Python Backend** (`src/index.py`): Main application entry point that launches pywebview
2. **React Frontend** (`src/index.jsx`): UI served either from Vite dev server (development) or `gui/` folder (production)
3. **API Communication**: JavaScript frontend calls Python backend via pywebview's API bridge

### Key Directories
- `src/backend/`: Python API, notarization service, blockchain clients, file scanner
- `src/frontend/`: React components, organized by feature (Panels/, Navigation/, etc.)
- `src/database/`: SQLAlchemy models and repository pattern for data access
- `gui/`: Frontend build output (created by `npm run frontend:prod`)
- `dist/`: Final packaged executables (created by platform-specific build commands)

### Backend Architecture
The Python backend follows a layered architecture:

- **API Layer** (`src/backend/api.py`): Exposed to frontend via pywebview
- **Service Layer** (`src/backend/notarizer/`): Core business logic for file notarization
- **Repository Layer** (`src/database/repositories/`): Data access abstraction
- **Infrastructure Layer** (`src/backend/blockchain/`, `src/backend/file_scanner/`): External integrations

### Frontend Architecture
React app uses a panel-based layout:

- **MainWindow**: Top-level component managing active panel state
- **Panels/**: Main content areas (Dashboard, Settings, Database, Verify, About)
- **Navigation/**: Sidebar for switching between panels
- **Modals/**: Reusable dialog components

### Environment Modes
The app supports two blockchain modes controlled by `USE_LOCAL_BLOCKCHAIN`:
- **Local Mode**: Simulated blockchain for development/testing
- **Production Mode**: Real Bitcoin SV blockchain via MintBlue API

### Build Process
1. **Development**: Vite serves frontend on port 3000, Python loads it via pywebview
2. **Production**: Frontend built to `gui/`, Python packaged with PyInstaller, final executable in `dist/`

## Important Notes

### File Operations
The app performs cryptographic file hashing and blockchain notarization. Key components:
- File scanning with size limits and recursive directory traversal
- SHA-256 hash generation for file integrity
- Progress tracking with callback mechanisms for UI updates

### Database Schema
Uses repository pattern with these main entities:
- `Directory`: Tracked folder paths
- `FileRecord`: Individual file metadata and blockchain transaction records  
- `Settings`: Application configuration

### Development vs Production
- Development: `npm start` launches Python app loading frontend from Vite dev server
- Production: `npm run build` creates standalone executable with bundled frontend assets