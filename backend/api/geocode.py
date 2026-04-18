"""
逆地理编码 API — 使用高德地图获取中文街道地址
"""
from fastapi import APIRouter, Depends, Query
import httpx
import os

from api.deps import get_current_user

router = APIRouter()

AMAP_KEY = os.getenv("AMAP_KEY", "8d0326d4cd59fc0ee6cfebc04fdd40bd")
AMAP_URL = "https://restapi.amap.com/v3/geocode/regeo"


def _extract_address(comp: dict) -> str:
    """从高德 addressComponent 提取简短地址"""
    parts = []
    for key in ["province", "city", "district", "township"]:
        val = comp.get(key)
        if val and isinstance(val, str) and val not in parts:
            parts.append(val)
    # street 和 streetNumber 特殊处理
    street = comp.get("street")
    if street and isinstance(street, str):
        parts.append(street)
    sn = comp.get("streetNumber")
    if isinstance(sn, dict):
        num = sn.get("number", "")
        s = sn.get("street", "")
        if s and s not in parts:
            parts.append(s)
        if num:
            parts.append(num)
    elif isinstance(sn, str) and sn:
        parts.append(sn)
    return "".join(parts) if parts else ""


@router.get("/geocode")
async def reverse_geocode(
    lat: float = Query(...),
    lng: float = Query(...),
    current_user=Depends(get_current_user)
):
    """GPS坐标转中文地址"""
    if AMAP_KEY:
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(AMAP_URL, params={
                    "key": AMAP_KEY,
                    "location": f"{lng},{lat}",
                    "extensions": "base",
                    "output": "json",
                })
                if resp.status_code == 200:
                    data = resp.json()
                    if data.get("status") == "1":
                        regeocode = data.get("regeocode", {})
                        formatted = regeocode.get("formatted_address", "")
                        comp = regeocode.get("addressComponent", {})
                        short_address = _extract_address(comp) or formatted
                        return {"address": short_address, "full_address": formatted}
        except Exception as e:
            print(f"[GEO] Amap exception: {e}")

    return {"address": f"{lat:.4f}, {lng:.4f}", "full_address": ""}
