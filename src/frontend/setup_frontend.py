"""
Next.js project scaffolding script.
Creates basic Next.js app structure with Mapbox integration.
"""

import json
from pathlib import Path

# Project root
FRONTEND_DIR = Path(__file__).parent.parent.parent / "src" / "frontend"

# package.json
package_json = {
    "name": "climate-burden-index-frontend",
    "version": "1.0.0",
    "description": "Climate Burden Index interactive dashboard",
    "scripts": {
        "dev": "next dev",
        "build": "next build",
        "start": "next start",
        "lint": "next lint",
        "type-check": "tsc --noEmit"
    },
    "dependencies": {
        "next": "^14.0.0",
        "react": "^18.2.0",
        "react-dom": "^18.2.0",
        "mapbox-gl": "^2.15.0",
        "@mapbox/mapbox-gl-draw": "^1.4.0",
        "axios": "^1.6.0",
        "zustand": "^4.4.0",
        "recharts": "^2.10.0",
        "tailwindcss": "^3.3.0",
        "postcss": "^8.4.31",
        "autoprefixer": "^10.4.16"
    },
    "devDependencies": {
        "@types/node": "^20.0.0",
        "@types/react": "^18.2.0",
        "typescript": "^5.0.0",
        "eslint": "^8.50.0",
        "eslint-config-next": "^14.0.0"
    }
}

# tsconfig.json
tsconfig = {
    "compilerOptions": {
        "target": "ES2020",
        "useDefineForClassFields": True,
        "lib": ["ES2020", "DOM", "DOM.Iterable"],
        "module": "ESNext",
        "skipLibCheck": True,
        "esModuleInterop": True,
        "allowSyntheticDefaultImports": True,
        "strict": True,
        "forceConsistentCasingInFileNames": True,
        "noEmit": True,
        "resolveJsonModule": True,
        "isolatedModules": True,
        "moduleResolution": "bundler",
        "allowImportingTsExtensions": True,
        "noUncheckedIndexedAccess": True,
        "paths": {
            "@/*": ["./*"]
        }
    },
    "include": ["next-env.d.ts", "**/*.ts", "**/*.tsx"],
    "exclude": ["node_modules"],
    "extends": "next/tsconfig"
}

# next.config.js
next_config = """
/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  env: {
    NEXT_PUBLIC_API_BASE_URL: process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000',
    NEXT_PUBLIC_MAPBOX_TOKEN: process.env.NEXT_PUBLIC_MAPBOX_TOKEN,
  },
  webpack: (config, { isServer }) => {
    config.module.rules.push({
      test: /mapbox-gl\\\\.css$/,
      use: ['style-loader', 'css-loader'],
    });
    return config;
  },
};

module.exports = nextConfig;
"""

# .env.example
env_example = """# API Configuration
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000

# Mapbox
NEXT_PUBLIC_MAPBOX_TOKEN=your_mapbox_token_here

# Analytics (optional)
NEXT_PUBLIC_GA_ID=
"""

# Create directories
(FRONTEND_DIR / "public").mkdir(parents=True, exist_ok=True)
(FRONTEND_DIR / "src" / "components").mkdir(parents=True, exist_ok=True)
(FRONTEND_DIR / "src" / "pages").mkdir(parents=True, exist_ok=True)
(FRONTEND_DIR / "src" / "styles").mkdir(parents=True, exist_ok=True)
(FRONTEND_DIR / "src" / "hooks").mkdir(parents=True, exist_ok=True)
(FRONTEND_DIR / "src" / "store").mkdir(parents=True, exist_ok=True)
(FRONTEND_DIR / "src" / "types").mkdir(parents=True, exist_ok=True)
(FRONTEND_DIR / "src" / "lib").mkdir(parents=True, exist_ok=True)

print(f"Created frontend directories in {FRONTEND_DIR}")
print("Run: npm install to set up dependencies")
