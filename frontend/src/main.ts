import { createApp } from 'vue'
import { createPinia } from 'pinia'
import PrimeVue from 'primevue/config'
import Tooltip from 'primevue/tooltip'
import Aura from '@primeuix/themes/aura'
import 'primeicons/primeicons.css'

import App from './App.vue'
import router from './router'
import { i18n } from './i18n'
import { applyTheme, cachedTheme } from './theme'
import './style.css'

const app = createApp(App)

app.use(createPinia())
app.use(i18n)
app.use(PrimeVue, {
  theme: {
    preset: Aura,
    options: {
      darkModeSelector: '.app-dark',
    },
  },
})
app.directive('tooltip', Tooltip)
app.use(router)

// Apply the last-known studio theme immediately to avoid a colour flash;
// the authoritative theme arrives from the server via the auth store.
const cached = cachedTheme()
applyTheme(cached.preset, cached.mode)

app.mount('#app')
