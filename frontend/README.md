# ScrapeSET Frontend

A modern React web interface for the ScrapeSET web scraping and RAG tool.

## Features

- **Dashboard**: Overview of collections, statistics, and quick actions
- **Web Scraping**: Interactive URL scraping with text element selection
- **Collections Management**: View, manage, and organize document collections
- **Chat Interface**: Real-time conversation with RAG-powered responses
- **Conversation History**: View and manage saved chat sessions
- **Settings Panel**: Configure LLM providers, embedding models, and processing options

## Technology Stack

- **React 18** with TypeScript
- **Vite** for fast development and building
- **Tailwind CSS** for styling
- **Lucide React** for icons
- **Axios** for API communication
- **React Router** for navigation

## Development Setup

1. **Install dependencies**:
   ```bash
   cd frontend
   npm install
   ```

2. **Start development server**:
   ```bash
   npm run dev
   ```

3. **Start the backend** (in another terminal):
   ```bash
   # From the project root
   python web_server.py
   ```

4. **Access the application**:
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000

## Project Structure

```
frontend/
├── public/                 # Static files
├── src/
│   ├── components/         # Reusable UI components
│   │   └── Layout.tsx     # Main application layout
│   ├── pages/             # Page components
│   │   ├── Dashboard.tsx  # Main dashboard
│   │   ├── ScrapeWeb.tsx  # Web scraping interface
│   │   ├── Collections.tsx # Collections management
│   │   ├── Chat.tsx       # Chat interface
│   │   ├── Conversations.tsx # Conversation history
│   │   └── Settings.tsx   # Settings panel
│   ├── services/          # API and external services
│   │   └── api.ts         # Backend API client
│   ├── App.tsx            # Main application component
│   ├── main.tsx           # Application entry point
│   └── index.css          # Global styles
├── package.json           # Dependencies and scripts
├── tailwind.config.js     # Tailwind CSS configuration
├── vite.config.ts         # Vite configuration
└── tsconfig.json          # TypeScript configuration
```

## Key Components

### Dashboard
- Collection statistics overview
- Quick action buttons for main functions
- Recent collections list
- System status indicators

### Web Scraping Interface
- URL input with validation
- Real-time scraping progress
- Interactive text element selection
- Batch processing to collections

### Collections Management
- List all collections with statistics
- View collection details and sources
- Delete/clear collections
- Source URL management

### Chat Interface
- Real-time messaging with the RAG system
- Conversation memory toggle
- Source citation display
- Session management
- Configurable result count

### Settings Panel
- LLM provider configuration (OpenAI, Anthropic, OpenRouter)
- Embedding model selection
- Text processing parameters
- Conversation memory settings
- API key management

## API Integration

The frontend communicates with the FastAPI backend through a centralized API service (`src/services/api.ts`) that handles:

- Collection management
- Web scraping operations
- RAG queries and chat
- Conversation persistence
- Settings management

## Build and Deployment

1. **Build for production**:
   ```bash
   npm run build
   ```

2. **Preview production build**:
   ```bash
   npm run preview
   ```

3. **Lint code**:
   ```bash
   npm run lint
   ```

## Configuration

The frontend can be configured through environment variables:

- `VITE_API_URL`: Backend API URL (defaults to `/api` for proxy)

## Responsive Design

The interface is fully responsive and works well on:
- Desktop computers
- Tablets
- Mobile phones

Key responsive features:
- Collapsible sidebar navigation
- Adaptive layouts for different screen sizes
- Touch-friendly controls
- Optimized chat interface for mobile

## Development Guidelines

- Use TypeScript for type safety
- Follow React best practices and hooks patterns
- Implement proper error handling
- Use Tailwind CSS utility classes
- Maintain component reusability
- Add loading states for async operations

## Future Enhancements

- Real-time WebSocket integration for live updates
- Advanced search and filtering
- Export/import functionality
- Dark mode theme
- Keyboard shortcuts
- Advanced visualizations