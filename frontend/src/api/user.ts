import request from './request'

export function login(username: string, password: string) {
  return request.post('/user/login', { username, password })
}

export function getUserInfo() {
  return request.get('/user/info')
}

export function register(data: { username: string; password: string; email?: string }) {
  return request.post('/user/register', data)
}
