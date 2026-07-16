export default defineNuxtConfig({
  compatibilityDate: '2025-07-16',
  devtools: { enabled: true },
  css: ['~/assets/css/main.css'],
  modules: ['@nuxt/eslint', '@pinia/nuxt'],
  runtimeConfig: {
    apiBaseUrl: process.env.NUXT_API_BASE_URL || 'http://localhost:8000',
    public: {
      appName: 'AgentLab',
    },
  },
  nitro: {
    devProxy: {
      '/api': {
        target: process.env.NUXT_API_BASE_URL || 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
  app: {
    head: {
      title: 'AgentLab',
      link: [
        {
          rel: 'stylesheet',
          href: 'https://fonts.googleapis.com/css2?family=DM+Sans:ital,opsz,wght@0,9..40,400;0,9..40,500;0,9..40,600;0,9..40,700;1,9..40,400&family=IBM+Plex+Mono:wght@400;500&display=swap',
        },
      ],
    },
  },
})
