import request from '../utils/request'

/**
 * 逆地理编码 — 将 GPS 坐标转为中文地址
 * @param {number} lat
 * @param {number} lng
 * @returns {Promise<{ address: string, full_address: string }>}
 */
export function reverseGeocode(lat, lng) {
  return request.get('/utils/geocode', { params: { lat, lng } })
}
