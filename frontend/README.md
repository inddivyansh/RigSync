# RigSync Frontend

Professional web interface for RigSync Asset Intelligence Platform.

## Features

- **Clean, Professional Design**: Enterprise-grade UI/UX without unnecessary elements
- **Real-time Chat Interface**: Natural language interaction with the AI copilot
- **Source Citations**: Transparent display of data sources and analysis tools used
- **Responsive Layout**: Works seamlessly on desktop and mobile devices
- **User Management**: Switch between different users for testing multi-user scenarios

## Tech Stack

- **React 18** with TypeScript
- **Vite** for fast development and optimized builds
- **Tailwind CSS** for professional styling
- **Lucide React** for clean, consistent icons
- **React Markdown** for formatted responses
- **Axios** for API communication

## Getting Started

### Prerequisites

- Node.js 18 or higher
- npm or yarn
- Backend API running on http://localhost:8000

### Installation

```bash
# Install dependencies
npm install

# Start development server
npm run dev
```

The application will be available at http://localhost:3000

### Build for Production

```bash
# Create optimized production build
npm run build

# Preview production build
npm run preview
```

## Project Structure

```
src/
├── components/
│   ├── Chat/           # Chat interface components
│   └── Layout/         # Layout components (Header, Sidebar)
├── contexts/           # React contexts for state management
├── types/              # TypeScript type definitions
├── App.tsx            # Main application component
├── main.tsx           # Application entry point
└── index.css          # Global styles and Tailwind directives
```

## Configuration

The frontend is configured to proxy API requests to the backend:

```typescript
// vite.config.ts
server: {
  port: 3000,
  proxy: {
    '/api': {
      target: 'http://localhost:8000',
      changeOrigin: true,
    },
  },
}
```

## Design Principles

1. **Clean and Professional**: No emojis, no excessive cards, no cluttered UI
2. **Information Hierarchy**: Clear visual hierarchy with proper typography
3. **Subtle Animations**: Smooth transitions without being distracting
4. **Accessible**: Proper ARIA labels and keyboard navigation
5. **Performance**: Optimized rendering and minimal re-renders

## Key Components

### Chat Interface
- Message history with user and assistant messages
- Markdown support for formatted responses
- Source citations and metadata display
- Example queries for easy onboarding

### Header
- User selector dropdown
- Application branding
- Settings access

### Sidebar
- Navigation menu
- Fleet statistics
- Version information

## API Integration

The frontend communicates with the FastAPI backend through the following endpoints:

- `POST /api/chat` - Send user queries and receive AI responses
- `GET /api/users` - Fetch available users
- `POST /api/sessions` - Create new chat sessions
- `GET /api/wells` - Fetch well data for statistics

## Customization

### Colors

The color scheme is defined in `tailwind.config.js`:

```javascript
colors: {
  primary: { /* Blue shades for primary actions */ },
  slate: { /* Gray shades for UI elements */ },
}
```

### Fonts

Using Inter for body text:

```html
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
```

## Development

### Hot Module Replacement

Vite provides instant hot module replacement during development for a smooth developer experience.

### Type Checking

TypeScript is configured for strict type checking:

```bash
npm run build  # Includes TypeScript compilation
```

### Linting

ESLint is configured for code quality:

```bash
npm run lint
```

## Production Deployment

The built files will be in the `dist` directory:

```bash
npm run build
```

Serve with any static file server or integrate with your deployment pipeline.

## Browser Support

- Chrome/Edge 90+
- Firefox 88+
- Safari 14+

## License

MIT License - see LICENSE file for details
