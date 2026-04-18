/**
 * 照片压缩工具
 *
 * 策略：拍照/选图时压缩到合理尺寸再存入 IndexedDB，
 * 单张照片控制在 ~300KB 以内，避免离线存储和同步上传超限。
 */

const MAX_WIDTH = 1280
const MAX_HEIGHT = 1280
const QUALITY = 0.7        // JPEG 质量 70%
const MAX_BLOB_SIZE = 512 * 1024  // 单张上限 512KB，超出则再压缩

/**
 * 压缩单个 File/Blob 为较小的 Blob
 * @param {File|Blob} file
 * @returns {Promise<Blob>}
 */
export function compressPhoto(file) {
  return new Promise((resolve) => {
    // 非图片直接返回
    if (!file.type.startsWith('image/')) {
      resolve(file)
      return
    }

    const img = new Image()
    const url = URL.createObjectURL(file)

    img.onload = () => {
      URL.revokeObjectURL(url)

      // 计算缩放尺寸
      let { width, height } = img
      if (width > MAX_WIDTH || height > MAX_HEIGHT) {
        const ratio = Math.min(MAX_WIDTH / width, MAX_HEIGHT / height)
        width = Math.round(width * ratio)
        height = Math.round(height * ratio)
      }

      // Canvas 绘制并导出
      const canvas = document.createElement('canvas')
      canvas.width = width
      canvas.height = height
      const ctx = canvas.getContext('2d')
      ctx.drawImage(img, 0, 0, width, height)

      canvas.toBlob(
        (blob) => {
          if (!blob) {
            resolve(file)  // 压缩失败，返回原图
            return
          }

          // 如果仍然过大，再降质量压缩一次
          if (blob.size > MAX_BLOB_SIZE) {
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
        QUALITY
      )
    }

    img.onerror = () => {
      URL.revokeObjectURL(url)
      resolve(file)  // 加载失败返回原图
    }

    img.src = url
  })
}

/**
 * 批量压缩照片数组（每个元素含 file 属性）
 * @param {Array<{file: File}>} photos
 * @returns {Promise<Array<{file: Blob}>>}
 */
export async function compressPhotos(photos) {
  const results = []
  for (const photo of photos) {
    if (photo.file) {
      const compressed = await compressPhoto(photo.file)
      results.push({
        ...photo,
        file: compressed,
        // 保留原始文件名
        _compressed: compressed.size < (photo.file.size || 0)
      })
    } else {
      results.push(photo)
    }
  }
  return results
}
