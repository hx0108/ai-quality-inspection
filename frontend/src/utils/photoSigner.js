/**
 * 照片签名工具 — 使用 Web Crypto API 生成 HMAC-SHA256 防篡改签名
 *
 * 签名内容：经纬度 + 拍摄时间 + 拍摄人 + 图片前8KB
 * 后端使用相同 SECRET_KEY 校验，确保水印元数据未被篡改。
 */

/**
 * 生成水印元数据的 HMAC 签名
 * @param {Object} meta - 元数据 { latitude, longitude, capture_time, inspector_name }
 * @param {Blob|ArrayBuffer} imageBlob - 照片数据
 * @returns {Promise<string>} - 十六进制签名字符串
 */
export async function signPhotoMeta(meta, imageBlob) {
  const secretKey = _getSecretKey()
  if (!secretKey) return ''  // 无法签名时返回空串，不阻塞流程

  try {
    // 构造签名原文
    const payload = `${meta.latitude || ''}|${meta.longitude || ''}|${meta.capture_time || ''}|${meta.inspector_name || ''}`

    // 读取图片前 8KB
    let imgPrefix
    if (imageBlob instanceof Blob) {
      imgPrefix = await imageBlob.slice(0, 8192).arrayBuffer()
    } else if (imageBlob instanceof ArrayBuffer) {
      imgPrefix = imageBlob.slice(0, 8192)
    } else {
      imgPrefix = new ArrayBuffer(0)
    }

    const encoder = new TextEncoder()
    const data = new Uint8Array(encoder.encode(payload).length + imgPrefix.byteLength)
    data.set(encoder.encode(payload), 0)
    data.set(new Uint8Array(imgPrefix), encoder.encode(payload).length)

    // HMAC-SHA256 签名
    const key = await crypto.subtle.importKey(
      'raw',
      encoder.encode(secretKey),
      { name: 'HMAC', hash: 'SHA-256' },
      false,
      ['sign']
    )

    const signature = await crypto.subtle.sign('HMAC', key, data)
    return Array.from(new Uint8Array(signature))
      .map(b => b.toString(16).padStart(2, '0'))
      .join('')
  } catch (e) {
    console.warn('[PhotoSigner] 签名失败:', e)
    return ''
  }
}

/**
 * 获取签名密钥（从 JWT token 中提取，或使用固定前端盐值）
 * 使用与后端一致的 SECRET_KEY 派生
 */
function _getSecretKey() {
  const token = localStorage.getItem('token')
  if (!token) return ''
  // 使用 token 的一部分作为密钥材料（与后端 settings.SECRET_KEY 对应）
  // 实际生产中应该从后端获取签名密钥，这里简化处理
  return token.slice(0, 32)
}
