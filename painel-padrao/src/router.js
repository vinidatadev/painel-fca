import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  { path: '/', redirect: '/dashboard' },
  { path: '/dashboard', component: () => import('./views/DashboardView.vue') },
  { path: '/fca', component: () => import('./views/FcaListView.vue') },
  { path: '/fca/novo', component: () => import('./views/FcaNovoView.vue') },
  { path: '/fca/:id', component: () => import('./views/FcaDetalheView.vue') },
  { path: '/admin/usuarios', component: () => import('./views/AdminUsuariosView.vue') },
  { path: '/admin/usuarios/novo', component: () => import('./views/AdminUsuarioFormView.vue') },
  { path: '/admin/usuarios/:id', component: () => import('./views/AdminUsuarioFormView.vue') },
  { path: '/admin/config', component: () => import('./views/AdminConfigView.vue') },
  { path: '/admin/sla', component: () => import('./views/AdminSlaView.vue') },
  { path: '/admin/help', component: () => import('./views/AdminHelpView.vue') },
  { path: '/admin/relatorio', component: () => import('./views/AdminBiView.vue'),
    beforeEnter: (_to, _from, next) => {
      // Guarda de acesso: user vem do localStorage via token decodificado
      // A verificação definitiva acontece dentro da view via inject('user')
      next()
    }
  },
  { path: '/admin/comunicados', component: () => import('./views/AdminComunicadosView.vue') },
  { path: '/admin/onboarding', component: () => import('./views/AdminOnboardingView.vue') },
  { path: '/help', component: () => import('./views/HelpView.vue') },
  { path: '/perfil', component: () => import('./views/PerfilView.vue') },
  { path: '/login', redirect: '/dashboard' },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach((to, _from, next) => {
  next()
})

export default router
