import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import Components from 'unplugin-vue-components/vite'
import { VantResolver } from '@vant/auto-import-resolver'

export default defineConfig({
  plugins: [
    vue(),
    Components({
      resolvers: [VantResolver()]
    })
  ],
  server: {
    port: 5173,
    host: '0.0.0.0',
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true
      }
    }
  },
  build: {
    // 生产构建优化
    target: 'es2015',  // 兼容主流浏览器
    cssCodeSplit: true,  // CSS 代码分割
    sourcemap: false,    // 禁用 sourcemap 减小体积
    chunkSizeWarningLimit: 1000,  // chunk 大小警告阈值(kB)
    rollupOptions: {
      output: {
        // 手动分包配置
        manualChunks: {
          // Vue 核心库单独打包
          'vue-vendor': ['vue', 'vue-router', 'pinia'],
          // Element Plus 单独打包（体积大）
          'element-plus': ['element-plus'],
          // Vant 单独打包
          'vant': ['vant'],
          // 图表库单独打包
          'echarts': ['echarts'],
          // 工具库打包
          'utils': ['axios', 'file-saver', 'xlsx'],
        }
      }
    }
  },
  // 生产环境启用压缩
  esbuild: {
    drop: ['console', 'debugger']
  }
})
