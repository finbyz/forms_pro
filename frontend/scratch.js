import { createRouter, createWebHistory } from 'vue-router'
const router = createRouter({
  history: createWebHistory(),
  routes: [{ path: '/p/:route(.*)', name: 'Form Submission Page', component: {} }]
})
try {
  console.log(router.resolve({ name: 'Form Submission Page', params: { route: 'my_form' } }).href)
} catch (e) {
  console.error("ERROR 1:", e.message)
}

try {
  const routeRecord = router.getRoutes().find(r => r.name === 'Form Submission Page')
  const path = routeRecord.path.replace(/:\w+\(.*?\)/, 'my_form')
  console.log(router.resolve(path).href)
} catch (e) {
  console.error("ERROR 2:", e.message)
}
