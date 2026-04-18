/**
 * 水印绘制工具 — Canvas 叠加水印并压缩输出
 *
 * 水印样式：左下角半透明背景条，白色层级文字
 * 内容：时间 > 日期 > GPS地址 > 经纬度坐标 > 检查员姓名
 *
 * 内部完成缩放+压缩（1280px / JPEG 0.7），避免外部二次压缩。
 */

const MAX_WIDTH = 1280
const MAX_HEIGHT = 1280
const FONT_FAMILY = "'PingFang SC', 'Microsoft YaHei', 'Helvetica Neue', sans-serif"

/**
 * 给照片添加水印
 * @param {Blob|File} imageBlob - 原始照片
 * @param {Object} options
 * @param {string} options.projectName - 小区名称（如"碧桂园凤凰城"）
 * @param {string} options.address - GPS街道地址
 * @param {number|null} options.latitude - GPS纬度
 * @param {number|null} options.longitude - GPS经度
 * @param {string} options.inspectorName - 检查员姓名
 * @param {Date|null} options.captureTime - 拍摄时间（优先使用，否则取当前时间）
 * @returns {Promise<Blob>} - 带水印的压缩JPEG
 */
export async function addWatermark(imageBlob, { projectName = '', address = '', latitude = null, longitude = null, inspectorName = '', captureTime = null } = {}) {
  const img = await _loadImage(imageBlob)

  // 1. 计算缩放尺寸
  let { width, height } = img
  if (width > MAX_WIDTH || height > MAX_HEIGHT) {
    const ratio = Math.min(MAX_WIDTH / width, MAX_HEIGHT / height)
    width = Math.round(width * ratio)
    height = Math.round(height * ratio)
  }

  // 2. 绘制原图到canvas
  const canvas = document.createElement('canvas')
  canvas.width = width
  canvas.height = height
  const ctx = canvas.getContext('2d')
  ctx.drawImage(img, 0, 0, width, height)

  // 3. 计算水印参数（基于1280px宽度等比缩放）
  const scale = width / 1280

  // 使用传入的拍摄时间或当前时间
  const now = captureTime || new Date()
  const timeStr = `${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}`
  const dateStr = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`

  // 组合地点：小区名 · 地址
  let locationParts = []
  if (projectName) locationParts.push(projectName)
  if (address && address !== '定位失败' && !address.match(/^\d+\.\d+/)) {
    locationParts.push(address)
  }
  const locationStr = locationParts.join(' · ') || '定位失败'

  // 经纬度坐标（新增）
  let coordStr = ''
  if (latitude !== null && longitude !== null) {
    coordStr = `${latitude.toFixed(4)}°N, ${longitude.toFixed(4)}°E`
  }

  const lines = [
    { text: timeStr, fontSize: Math.round(112 * scale), bold: true },
    { text: dateStr, fontSize: Math.round(64 * scale), bold: false },
    { text: locationStr, fontSize: Math.round(56 * scale), bold: false },
  ]
  if (coordStr) {
    lines.push({ text: coordStr, fontSize: Math.round(44 * scale), bold: false })
  }
  if (inspectorName) {
    lines.push({ text: inspectorName, fontSize: Math.round(52 * scale), bold: false })
  }

  // 4. 计算水印条尺寸
  const padding = Math.round(48 * scale)
  const lineHeight = (fontSize) => Math.round(fontSize * 1.4)
  const barWidth = width
  const barHeight = padding * 2 + lines.reduce((sum, l) => sum + lineHeight(l.fontSize), 0)
  const barY = height - barHeight

  // 5. 绘制半透明背景
  ctx.fillStyle = 'rgba(0, 0, 0, 0.55)'
  ctx.fillRect(0, barY, barWidth, barHeight)

  // 6. 绘制文字
  ctx.fillStyle = '#ffffff'
  ctx.textBaseline = 'top'
  let textY = barY + padding
  for (const line of lines) {
    ctx.font = `${line.bold ? 'bold ' : ''}${line.fontSize}px ${FONT_FAMILY}`
    // 截断过长文本
    let displayText = line.text
    const maxWidth = width - padding * 2
    while (ctx.measureText(displayText).width > maxWidth && displayText.length > 3) {
      displayText = displayText.slice(0, -4) + '...'
    }
    ctx.fillText(displayText, padding, textY)
    textY += lineHeight(line.fontSize)
  }

  // 7. 导出为压缩JPEG
  return new Promise((resolve) => {
    canvas.toBlob(
      (blob) => {
        if (blob && blob.size > 512 * 1024) {
          // 过大则降低质量
          canvas.toBlob(
            (blob2) => resolve(blob2 || blob),
            'image/jpeg',
            0.4
          )
        } else {
          resolve(blob)
        }
      },
      'image/jpeg',
      0.7
    )
  })
}

/**
 * 加载图片文件为 Image 元素
 */
function _loadImage(blob) {
  return new Promise((resolve, reject) => {
    const img = new Image()
    const url = URL.createObjectURL(blob)
    img.onload = () => {
      URL.revokeObjectURL(url)
      resolve(img)
    }
    img.onerror = () => {
      URL.revokeObjectURL(url)
      reject(new Error('Failed to load image'))
    }
    img.src = url
  })
}
