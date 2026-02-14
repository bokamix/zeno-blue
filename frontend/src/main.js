import { createApp } from 'vue'
import * as Sentry from '@sentry/vue'
import App from './App.vue'
import i18n from './locales'
import './styles/main.css'

const app = createApp(App)

// Initialize Sentry if DSN is configured
if (import.meta.env.VITE_SENTRY_DSN) {
  Sentry.init({
    app,
    dsn: import.meta.env.VITE_SENTRY_DSN,
    environment: import.meta.env.VITE_SENTRY_ENVIRONMENT || 'development',
    release: import.meta.env.VITE_BUILD_VERSION || 'dev',
    integrations: [
      Sentry.browserTracingIntegration(),
      Sentry.replayIntegration(),
    ],
    tracesSampleRate: 0.1,
    replaysSessionSampleRate: 0.1,
    replaysOnErrorSampleRate: 1.0,
  })
}

app.use(i18n)
app.mount('#app')
