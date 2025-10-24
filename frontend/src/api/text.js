// src/api/text.js
import { http } from './index'

export const getText  = () => http.get('/text').then(res => res.data.content || '')
export const saveText = (content) =>
  http.post('/text', { content }).then(res => res.data)
