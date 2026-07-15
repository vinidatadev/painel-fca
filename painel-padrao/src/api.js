const BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

let _getMsal = null
export function setMsalGetter(fn) { _getMsal = fn }

const LOCAL_TOKEN_KEY = 'local_token'
export function saveLocalToken(token) { localStorage.setItem(LOCAL_TOKEN_KEY, token) }
export function clearLocalToken() { localStorage.removeItem(LOCAL_TOKEN_KEY) }
export function getLocalToken() { return localStorage.getItem(LOCAL_TOKEN_KEY) }

async function getToken() {
  const local = localStorage.getItem(LOCAL_TOKEN_KEY)
  if (local) return local
  const msal = _getMsal?.()
  if (!msal) throw new Error('Usuário não autenticado')
  const accounts = msal.getAllAccounts()
  if (!accounts.length) throw new Error('Usuário não autenticado')
  const response = await msal.acquireTokenSilent({ scopes: ['User.Read'], account: accounts[0] })
  return response.idToken
}

function parseError(err) {
  if (Array.isArray(err.detail)) return err.detail.map(e => e.msg).join(', ')
  return err.detail || 'Erro desconhecido'
}

async function request(method, path, body = null) {
  const token = await getToken()
  const res = await fetch(`${BASE_URL}${path}`, {
    method,
    headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
    body: body ? JSON.stringify(body) : undefined
  })
  if (res.status === 204) return null
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Erro desconhecido' }))
    throw new Error(parseError(err))
  }
  return res.json()
}

async function uploadRequest(path, file) {
  const token = await getToken()
  const form = new FormData()
  form.append('file', file)
  const res = await fetch(`${BASE_URL}${path}`, {
    method: 'POST',
    headers: { 'Authorization': `Bearer ${token}` },
    body: form
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Erro desconhecido' }))
    throw new Error(parseError(err))
  }
  return res.json()
}

async function downloadRequest(method, path) {
  const token = await getToken()
  const res = await fetch(`${BASE_URL}${path}`, {
    method,
    headers: { 'Authorization': `Bearer ${token}` },
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Erro desconhecido' }))
    throw new Error(parseError(err))
  }
  const blob = await res.blob()
  const contentDisposition = res.headers.get('Content-Disposition') || ''
  const match = contentDisposition.match(/filename=([^;]+)/)
  const filename = match ? match[1] : 'export'
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}

export const api = {
  auth: {
    me: () => request('GET', '/api/auth/me'),
    changePassword: (nova_senha) => request('POST', '/api/auth/change-password', { nova_senha }),
    login: (email, password) =>
      fetch(`${BASE_URL}/api/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password })
      }).then(async res => {
        if (!res.ok) {
          const err = await res.json().catch(() => ({ detail: 'Erro desconhecido' }))
          throw new Error(parseError(err))
        }
        return res.json()
      }),
    setup: (email, name, password) =>
      fetch(`${BASE_URL}/api/auth/setup`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, name, password })
      }).then(async res => {
        if (!res.ok) {
          const err = await res.json().catch(() => ({ detail: 'Erro desconhecido' }))
          throw new Error(parseError(err))
        }
        return res.json()
      })
  },

  fcas: {
    list: (params = {}) => {
      const q = new URLSearchParams(Object.fromEntries(Object.entries(params).filter(([, v]) => v !== undefined && v !== null && v !== '')))
      return request('GET', `/api/fcas/?${q}`)
    },
    get: (id) => request('GET', `/api/fcas/${id}`),
    create: (data) => request('POST', '/api/fcas/', data),
    responder: (id, data) => request('POST', `/api/fcas/${id}/responder`, data),
    encerrar: (id) => request('POST', `/api/fcas/${id}/encerrar`),
    export: (params = {}, format = 'xlsx') => {
      const q = new URLSearchParams(Object.fromEntries(Object.entries(params).filter(([, v]) => v !== undefined && v !== null && v !== '')))
      return downloadRequest('GET', `/api/fcas/export?format=${format}&${q}`)
    },
    comentarios: {
      list: (id) => request('GET', `/api/fcas/${id}/comentarios`),
      create: (id, texto) => request('POST', `/api/fcas/${id}/comentarios`, { texto }),
    },
    audit: (id) => request('GET', `/api/fcas/${id}/audit`),
    reabrir: (id, setor, empresa) => request('POST', `/api/fcas/${id}/reabrir`, { setor, empresa }),
    reatribuir: (id, setor, empresa, justificativa) => request('POST', `/api/fcas/${id}/reatribuir`, { setor, empresa, justificativa }),
    cancelar: (id, motivo) => request('POST', `/api/fcas/${id}/cancelar`, { motivo }),
  },

  dashboard: {
    get: () => request('GET', '/api/dashboard/'),
    metricas: (agrupamento = 'semana') => request('GET', `/api/dashboard/metricas?agrupamento=${agrupamento}`),
  },

  admin: {
    relatorio: (params = {}) => {
      const q = new URLSearchParams(Object.fromEntries(Object.entries(params).filter(([, v]) => v !== undefined && v !== null && v !== '')))
      return request('GET', `/api/admin/relatorio?${q}`)
    },
  },

  bi: {
    fca: (params = {}) => {
      const q = new URLSearchParams(
        Object.fromEntries(
          Object.entries(params).filter(([, v]) => v !== undefined && v !== null && v !== '')
        )
      )
      return request('GET', `/api/bi/fca?${q}`)
    }
  },

  usuarios: {
    list: (params = {}) => {
      const q = new URLSearchParams(Object.fromEntries(Object.entries(params).filter(([, v]) => v !== undefined && v !== null && v !== '')))
      return request('GET', `/api/usuarios/?${q}`)
    },
    get: (id) => request('GET', `/api/usuarios/${id}`),
    create: (data) => request('POST', '/api/usuarios/', data),
    update: (id, data) => request('PUT', `/api/usuarios/${id}`, data),
    desativar: (id) => request('PATCH', `/api/usuarios/${id}/desativar`),
    patch: (id, data) => request('PATCH', `/api/usuarios/${id}`, data),
  },

  upload: {
    file: (file) => uploadRequest('/api/upload/', file),
    url: (key) => request('GET', `/api/upload/${encodeURIComponent(key)}/url`),
  },

  perfil: {
    get: () => request('GET', '/api/perfil/'),
    update: (data) => request('PATCH', '/api/perfil/', data),
    uploadAvatar: (file) => uploadRequest('/api/perfil/avatar', file),
    deleteAvatar: () => request('DELETE', '/api/perfil/avatar'),
  },

  sla: {
    list: () => request('GET', '/api/sla/'),
    create: (data) => request('POST', '/api/sla/', data),
    update: (id, data) => request('PUT', `/api/sla/${id}`, data),
    remove: (id) => request('DELETE', `/api/sla/${id}`),
  },

  opcoes: {
    get: () => request('GET', '/api/opcoes/'),
    adminList: (tipo) => request('GET', `/api/opcoes/admin${tipo ? '?tipo=' + tipo : ''}`),
    create: (data) => request('POST', '/api/opcoes/', data),
    update: (id, data) => request('PUT', `/api/opcoes/${id}`, data),
    remove: (id) => request('DELETE', `/api/opcoes/${id}`),
  },

  help: {
    list: () => request('GET', '/api/help/'),
    get: (id) => request('GET', `/api/help/${id}`),
    create: (data) => request('POST', '/api/help/', data),
    responder: (id, texto) => request('POST', `/api/help/${id}/mensagens`, { texto }),
    status: (id, status) => request('PATCH', `/api/help/${id}/status`, { status }),
  },

  notifications: {
    list: () => request('GET', '/api/notifications/'),
    unreadCount: () => request('GET', '/api/notifications/unread-count'),
    markRead: (id) => request('POST', `/api/notifications/${id}/read`),
    markAllRead: () => request('POST', '/api/notifications/read-all'),
    comunicado: (data) => request('POST', '/api/notifications/comunicado', data),
  },

  onboarding: {
    videos: () => request('GET', '/api/onboarding/videos'),
    videoUrl: (id) => request('GET', `/api/onboarding/videos/${id}/url`),
    concluir: (id) => request('POST', `/api/onboarding/videos/${id}/concluir`),
    status: () => request('GET', '/api/onboarding/status'),
    // admin
    adminVideos: () => request('GET', '/api/onboarding/admin/videos'),
    adminCreate: (formData) => {
      return getToken().then(token =>
        fetch(`${BASE_URL}/api/onboarding/admin/videos`, {
          method: 'POST',
          headers: { 'Authorization': `Bearer ${token}` },
          body: formData,
        }).then(async res => {
          if (!res.ok) {
            const err = await res.json().catch(() => ({ detail: 'Erro desconhecido' }))
            throw new Error(parseError(err))
          }
          return res.json()
        })
      )
    },
    adminUpdate: (id, data) => request('PUT', `/api/onboarding/admin/videos/${id}`, data),
    adminDelete: (id) => request('DELETE', `/api/onboarding/admin/videos/${id}`),
    adminReorder: (items) => request('POST', '/api/onboarding/admin/videos/reorder', items),
  },
}
