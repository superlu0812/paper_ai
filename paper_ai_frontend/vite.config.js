import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  // 支持通过环境变量配置 base，默认使用 /ai_paper/
  // 如果部署到其他路径，可以在 .env.production 中设置 VITE_BASE_URL=/your-path/
  const base = process.env.VITE_BASE_URL || '/ai_paper/'
  
  return {
    plugins: [vue()],
    base: base,
  }
})
