/**
 * 地理位置工具 — 高德地图JS SDK定位（不依赖浏览器GPS）
 *
 * 高德定位使用 IP + WiFi + 基站 + GPS 融合定位，HTTP环境下也能工作。
 * 流程：加载高德JS SDK → AMap.Geolocation定位 → AMap.Geocoder逆地理编码
 * 全部失败时返回 '定位失败'
 */

const AMAP_KEY = '97a5b039869823457a2569d7d7ca5ef1'
const AMAP_SDK_URL = `https://webapi.amap.com/maps?v=1.4.15&key=${AMAP_KEY}`

const CACHE_TTL = 10 * 60 * 1000
let _cached = null
let _sdkReady = null

/**
 * 加载高德JS SDK（仅一次）
 */
function loadAmapSDK() {
  if (window.AMap) return Promise.resolve(window.AMap)
  if (_sdkReady) return _sdkReady

  _sdkReady = new Promise((resolve, reject) => {
    const s = document.createElement('script')
    s.src = AMAP_SDK_URL
    s.onload = () => {
      if (window.AMap) resolve(window.AMap)
      else reject(new Error('AMap undefined'))
    }
    s.onerror = () => { _sdkReady = null; reject(new Error('SDK load failed')) }
    document.head.appendChild(s)
  })
  return _sdkReady
}

/**
 * 高德定位：获取坐标（含精度信息）
 */
function amapGetPosition(AMap) {
  return new Promise((resolve, reject) => {
    AMap.plugin('AMap.Geolocation', () => {
      const geo = new AMap.Geolocation({
        enableHighAccuracy: true,
        timeout: 10000,
        maximumAge: 0,          // 不使用缓存位置，强制重新获取
        GeoLocationFirst: true,
        extensions: 'all'
      })
      geo.getCurrentPosition((status, result) => {
        if (status === 'complete' && result.position) {
          resolve({
            lat: result.position.lat || result.position.getLat(),
            lng: result.position.lng || result.position.getLng(),
            address: result.formattedAddress || '',
            accuracy: result.accuracy || null  // 定位精度（米）
          })
        } else {
          reject(new Error(result.message || '定位失败'))
        }
      })
    })
  })
}

/**
 * 高德逆地理编码：坐标 → 地址
 */
function amapGetAddress(AMap, lat, lng) {
  return new Promise((resolve, reject) => {
    AMap.plugin('AMap.Geocoder', () => {
      const coder = new AMap.Geocoder({ radius: 100, extensions: 'base' })
      coder.getAddress([lng, lat], (status, result) => {
        if (status === 'complete' && result.regeocode) {
          resolve(result.regeocode.formattedAddress || '')
        } else {
          reject(new Error('Geocoder failed'))
        }
      })
    })
  })
}

/**
 * 获取当前位置（高德地图）— 使用缓存
 * @returns {Promise<{ address: string, latitude: number|null, longitude: number|null, accuracy: number|null }>}
 */
export async function getLocationInfo() {
  // 缓存
  if (_cached && Date.now() - _cached.timestamp < CACHE_TTL) {
    return { address: _cached.address, latitude: _cached.latitude, longitude: _cached.longitude, accuracy: _cached.accuracy }
  }

  return _doLocate()
}

/**
 * 强制刷新定位 — 水印拍摄时使用，不走缓存
 * @returns {Promise<{ address: string, latitude: number|null, longitude: number|null, accuracy: number|null }>}
 */
export async function getFreshLocation() {
  return _doLocate()
}

/**
 * 执行定位（内部函数）
 */
async function _doLocate() {
  try {
    const AMap = await loadAmapSDK()

    // 第一步：高德定位获取坐标
    const pos = await amapGetPosition(AMap)

    // 第二步：如果有地址直接用，没有则逆地理编码
    let address = pos.address
    if (!address) {
      try {
        address = await amapGetAddress(AMap, pos.lat, pos.lng)
      } catch (e) {
        address = `${pos.lat.toFixed(4)}, ${pos.lng.toFixed(4)}`
      }
    }

    const result = { address, latitude: pos.lat, longitude: pos.lng, accuracy: pos.accuracy }
    _cached = { ...result, timestamp: Date.now() }
    return result

  } catch (e) {
    console.warn('[Geo] 高德定位失败:', e.message)
    const result = { address: '定位失败', latitude: null, longitude: null, accuracy: null }
    _cached = { ...result, timestamp: Date.now() }
    return result
  }
}

export function clearLocationCache() {
  _cached = null
}
