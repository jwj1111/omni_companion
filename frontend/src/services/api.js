/**
 * 后端 API 服务
 */
const BASE_URL = 'http://localhost:8000'

/**
 * 发送聊天消息（流式返回）
 * @param {string|Array} content - 文本或多模态内容
 * @param {boolean} outputAudio - 是否返回音频
 * @param {function} onChunk - 每收到一个 chunk 的回调 (chunk) => void
 */
export async function sendChatMessage(content, outputAudio, onChunk) {
  const resp = await fetch(`${BASE_URL}/api/chat/send`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ content, output_audio: outputAudio }),
  })

  const reader = resp.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break

    buffer += decoder.decode(value, { stream: true })
    const lines = buffer.split('\n')
    buffer = lines.pop() // 保留不完整的最后一行

    for (const line of lines) {
      if (line.trim()) {
        try {
          const chunk = JSON.parse(line)
          onChunk(chunk)
        } catch (e) {
          // 忽略解析错误
        }
      }
    }
  }
}

/**
 * 获取对话历史
 */
export async function getChatHistory() {
  const resp = await fetch(`${BASE_URL}/api/chat/history`)
  return resp.json()
}

/**
 * 清空对话历史
 */
export async function clearChatHistory() {
  const resp = await fetch(`${BASE_URL}/api/chat/clear`, { method: 'POST' })
  return resp.json()
}

/**
 * 获取所有设置
 */
export async function getSettings() {
  const resp = await fetch(`${BASE_URL}/api/settings/all`)
  return resp.json()
}

/**
 * 获取音色列表
 */
export async function getVoices() {
  const resp = await fetch(`${BASE_URL}/api/settings/voices`)
  return resp.json()
}

/**
 * 上传截屏
 */
export async function uploadScreenshot(imageB64) {
  const resp = await fetch(`${BASE_URL}/api/screenshot`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ image_b64: imageB64 }),
  })
  return resp.json()
}
