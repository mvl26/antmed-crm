import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import vueJsx from '@vitejs/plugin-vue-jsx'
import path from 'path'
import { VitePWA } from 'vite-plugin-pwa'

// https://vitejs.dev/config/
export default defineConfig(async ({ mode }) => {
  const isDev = mode === 'development'
  const config = {
    plugins: [
      vue(),
      vueJsx(),
      VitePWA({
        registerType: 'autoUpdate',
        devOptions: {
          // Tắt service worker ở DEV: tránh SW cache app-shell cũ → màn trắng / UI cũ khi
          // đang phát triển (rule 02). PWA vẫn đầy đủ ở production build (yarn build).
          enabled: false,
        },
        workbox: {
          // App-shell có file CSS ~2.5 MiB (leaflet + tailwind...) vượt mặc định 2 MiB.
          // Nâng giới hạn để service worker precache đủ app-shell (offline) và build không vỡ.
          maximumFileSizeToCacheInBytes: 4 * 1024 * 1024,
        },
        manifest: {
          display: 'standalone',
          name: 'AntMed CRM',
          short_name: 'AntMed CRM',
          start_url: '/antmed',
          description:
            'AntMed CRM — quản lý kinh doanh thiết bị và vật tư y tế',
          icons: [
            {
              src: '/assets/antmed_crm/manifest/manifest-icon-192.maskable.png',
              sizes: '192x192',
              type: 'image/png',
              purpose: 'any',
            },
            {
              src: '/assets/antmed_crm/manifest/manifest-icon-192.maskable.png',
              sizes: '192x192',
              type: 'image/png',
              purpose: 'maskable',
            },
            {
              src: '/assets/antmed_crm/manifest/manifest-icon-512.maskable.png',
              sizes: '512x512',
              type: 'image/png',
              purpose: 'any',
            },
            {
              src: '/assets/antmed_crm/manifest/manifest-icon-512.maskable.png',
              sizes: '512x512',
              type: 'image/png',
              purpose: 'maskable',
            },
          ],
        },
      }),
    ],
    resolve: {
      alias: {
        '@': path.resolve(__dirname, 'src'),
      },
    },
    optimizeDeps: {
      include: [
        'feather-icons',
        'tailwind.config.js',
        'prosemirror-state',
        'prosemirror-view',
        'lowlight',
        'interactjs',
      ],
    },
    server: {
      port: 3001,
      strictPort: true,
      allowedHosts: ['miyano', 'antmed.local', 'localhost', '127.0.0.1'],
      fs: {
        allow: [path.resolve(__dirname, '..')],
      },
      // Dev local CHỈ dùng localhost:3001 → ép mọi request API về site `miyano`.
      // (Frappe phân giải site theo Host; "localhost" không phải site → 404/Guest.)
      // changeOrigin gửi Host=miyano cho backend; bỏ Domain của Set-Cookie để session
      // sống trên localhost. Thay cho frappeProxy (định tuyến site theo Host trình duyệt).
      proxy: {
        '^/(desk|app|login|api|assets|files|private)': {
          target: 'http://miyano:8000',
          changeOrigin: true,
          ws: true,
          configure: (proxy) => {
            proxy.on('proxyRes', (proxyRes) => {
              const sc = proxyRes.headers['set-cookie']
              if (Array.isArray(sc)) {
                proxyRes.headers['set-cookie'] = sc.map((c) =>
                  c.replace(/;\s*Domain=[^;]+/i, ''),
                )
              }
            })
          },
        },
      },
    },
  }

  const frappeui = await importFrappeUIPlugin(isDev, config)
  config.plugins.unshift(
    frappeui({
      // Dev: proxy tự cấu hình ở server.proxy (ghim site miyano, chỉ dùng localhost:3001).
      // Tắt frappeProxy mặc định vì nó định tuyến site theo Host trình duyệt (localhost fail).
      frappeProxy: false,
      lucideIcons: true,
      jinjaBootData: true,
      buildConfig: {
        indexHtmlPath: '../antmed_crm/www/antmed.html',
        emptyOutDir: true,
        sourcemap: true,
      },
    }),
  )

  return config
})

async function importFrappeUIPlugin(isDev, config) {
  if (isDev) {
    try {
      // Check if local frappe-ui has the vite plugin file
      const fs = await import('node:fs')
      const localVitePluginPath = path.resolve(__dirname, '../frappe-ui/vite')

      if (fs.existsSync(localVitePluginPath)) {
        const module = await import('../frappe-ui/vite')
        console.info('Local frappe-ui vite plugin found, using local plugin')
        config.resolve.alias = getAliases(config)
        return module.default
      }
      // Không có frappe-ui local → dùng npm package (mặc định, im lặng — không cảnh báo).
    } catch (error) {
      console.warn(
        'Local frappe-ui not found, falling back to npm package:',
        error.message,
      )
    }
  }
  // Fall back to npm package if local import fails
  const module = await import('frappe-ui/vite')
  return module.default
}

function getAliases(config) {
  return {
    ...config.resolve.alias,
    'frappe-ui/tailwind': path.resolve(
      __dirname,
      '../frappe-ui/tailwind/preset.js',
    ),
    'frappe-ui/style.css': path.resolve(
      __dirname,
      '../frappe-ui/src/style.css',
    ),
    'frappe-ui/frappe': path.resolve(__dirname, '../frappe-ui/frappe/index.js'),
    'frappe-ui': path.resolve(__dirname, '../frappe-ui/src/index.ts'),
  }
}
