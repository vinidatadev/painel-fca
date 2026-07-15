import './assets/design-tokens.css'
import { createApp } from 'vue'
import App from './App.vue'
import router from './router.js'
import { PublicClientApplication } from '@azure/msal-browser'
import { msalConfig } from './authConfig'
import { setMsalGetter } from './api'

const msalInstance = new PublicClientApplication(msalConfig)

msalInstance.initialize().then(() => {
  setMsalGetter(() => msalInstance)

  const app = createApp(App)
  app.provide('msal', msalInstance)
  app.use(router)
  app.mount('#app')
})
