import { onBeforeUnmount, onMounted, ref } from 'vue'

const QUERY = '(max-width: 767px)'

export function useIsMobile() {
  const isMobile = ref(window.matchMedia(QUERY).matches)
  const mq = window.matchMedia(QUERY)
  const update = (e: MediaQueryListEvent) => { isMobile.value = e.matches }
  onMounted(() => mq.addEventListener('change', update))
  onBeforeUnmount(() => mq.removeEventListener('change', update))
  return isMobile
}
