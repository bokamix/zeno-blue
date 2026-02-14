import { createI18n } from 'vue-i18n'
import en from './en.json'
import pl from './pl.json'

// Get stored language or default to 'en'
const savedLanguage = localStorage.getItem('app-language') || 'en'

const i18n = createI18n({
  legacy: false,
  locale: savedLanguage,
  fallbackLocale: 'en',
  messages: { en, pl }
})

export default i18n

// Helper to change language and persist
export function setLanguage(lang) {
  i18n.global.locale.value = lang
  localStorage.setItem('app-language', lang)
  document.documentElement.setAttribute('lang', lang)
}

export function getCurrentLanguage() {
  return i18n.global.locale.value
}
