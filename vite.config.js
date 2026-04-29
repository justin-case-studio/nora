import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import viteTsconfigPaths from 'vite-tsconfig-paths'

export default defineConfig({
    base: '',
    plugins: [react(), viteTsconfigPaths()],
    server: {
        port: 3000,
        hmr: {
            overlay: true,
        },
        watch: {
            usePolling: true,
        },
        open: true,
    },
    build: {
        outDir: 'gui',
        emptyOutDir: true,
        sourcemap: true,
    },
    optimizeDeps: {
        include: ['react', 'react-dom', '@chakra-ui/react', 'react-icons'],
    },
})