import os
import re
import json
import csv
import codecs
import time
import threading
import ssl
import gzip
import zlib
import urllib.request
import urllib.error
import tempfile
from urllib.parse import urljoin, urlparse
from typing import List, Dict, Any, Set, Optional, Iterator

# =============================================================================
# SECTION: Constants & Scraping Configuration
# =============================================================================
_MR_URL = "https://www.maprunner.info/michigan/black-river?loc=_CL_1"
_MR_DEBUG = False
_MR_TIMEOUT_SECONDS = 20
_MR_CANONICAL_NAMES = {"data": "data.js", "desc": "desc.js"}
_MR_IN_MEM_FILES: Dict[str, bytes] = {}
_MR_IN_MEM_META: Dict[str, Dict[str, str]] = {}
_MR_DATA_SIGNATURE = "const _=JSON.parse('[{\"name\":\"RU_02_01_SERVHUB_GAS\""
_MR_DESC_SIGNATURE = "const t={UI_TRUCK_TYPE_HEAVY_DUTY:{t:0,b:{t:2,i:[{t:3}],s:\"HEAVY DUTY\""

# Configuration thresholds
_MR_ENGLISH_MIN_ENTRIES = 2800 
_MR_MIN_LOCALIZATION_ENTRIES = 400
_MR_CHUNK_MAX = 45
_MR_LOCALIZATION_CANDIDATE_MAX = 12
_MR_ENGLISH_AVG_MIN = 2.4
_MR_ENGLISH_AVG_DELTA = 0.45
_MR_ENGLISH_HITS_MIN = 3
_MR_NON_ASCII_RATIO_MAX = 0.08
_MR_ENGLISH_SAMPLE_MAX = 240

# Heuristic data for language detection
_MR_DIACRITICS = set("ąćęłńóśźżĄĆĘŁŃÓŚŹŻáčďéěíňóřšťúůýžäöüß@âäçéèêëîïôöùûüÿœæáéíñóúü")
_MR_CYRILLIC_RE = re.compile(r"[\u0400-\u04FF]")
_MR_ENGLISH_WORDS = ["the", "cargo", "delivery", "mission", "truck", "repair", "fuel", "scout"]
_MR_FORBIDDEN_LANG_WORDS = ["и", "в", "на", "что", "jest", "nie", "się", "und", "der", "die", "pour", "avec"]

# Region and Category metadata (Matches snowrunner_editor.py)
_MR_ALLOWED_CATEGORIES = {"_TSK", "_CNT", "_CNS", "_CONTRACTS", "_TASKS", "_CONTESTS"}
_MR_CATEGORY_PRIORITY = ["_CONTRACTS", "_TASKS", "_CONTESTS", "_CNT", "_TSK", "_CNS"]
_MR_TYPE_PRIORITY = ["truckDelivery", "cargoDelivery", "exploration"]

_MR_REGION_LIST = [
    ("US_01", "Michigan"), ("US_02", "Alaska"), ("RU_02", "Taymyr"),
    ("RU_03", "Kola Peninsula"), ("US_04", "Yukon"), ("US_03", "Wisconsin"),
    ("RU_04", "Amur"), ("RU_05", "Don"), ("US_06", "Maine"),
    ("US_07", "Tennessee"), ("RU_08", "Glades"), ("US_09", "Ontario"),
    ("US_10", "British Columbia"), ("US_11", "Scandinavia"), ("US_12", "North Carolina"),
    ("RU_13", "Almaty"), ("US_14", "Austria"), ("US_15", "Quebec"),
    ("US_16", "Washington"), ("RU_17", "Zurdania")
]
_MR_REGION_ORDER = [r for r, _ in _MR_REGION_LIST]
_MR_REGION_LOOKUP = dict(_MR_REGION_LIST)

# [v113.10] MapRunner Nuxt 3 Hashed Bundles (Dynamic)
_MR_DATA_URL_DEFAULT = "https://cdn4.maprunner.info/mr/ChUX6nGL.js"
_MR_DESC_URL_DEFAULT = "https://cdn4.maprunner.info/mr/BRwAfUvc.js"

_MR_SAFE_FALLBACK_URLS = [
    "https://raw.githubusercontent.com/Nikunjxx/snowrunner-save-editor-web/main/public/mr/data.js",
    "https://raw.githubusercontent.com/Nikunjxx/snowrunner-save-editor-web/main/public/mr/desc.js",
    "https://cdn4.maprunner.info/mr/ChUX6nGL.js",
    "https://cdn4.maprunner.info/mr/BRwAfUvc.js"
]

# Shared state between scraping functions (Migrated from snowrunner_editor.py)
_MR_LAST_LOCALIZATION_FILES: List[str] = []
_MR_LAST_LOCALIZATION_BLOCKED: bool = False

# =============================================================================
# SECTION: ObjectiveDatabase Class
# =============================================================================

class ObjectiveDatabase:
    """
    Singleton database for SnowRunner objectives, handling MapRunner data 
    scraping, local CSV caching, and reward lookup.
    """
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(ObjectiveDatabase, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self.items: Dict[str, Dict[str, Any]] = {}
        self.raw_list: List[Dict[str, Any]] = []
        self._cache_path = self._get_cache_path()
        self._initialized = True

    @property
    def csv_path(self) -> str:
        return self._cache_path

    def _get_cache_path(self) -> str:
        """Derive standard location in app data folder."""
        app_data_dir = os.path.join(os.path.expanduser("~"), "snowrunner_save_editor_data")
        os.makedirs(app_data_dir, exist_ok=True)
        return os.path.join(app_data_dir, ".snowrunner_editor_maprunner_data.csv")

    def load_local(self, force_reload=False, allow_build=True) -> bool:
        """Loads data from local CSV cache."""
        if self.items and not force_reload:
            return True

        if not os.path.exists(self._cache_path):
            if allow_build:
                return self.refresh_from_web()
            return False

        try:
            with open(self._cache_path, "r", encoding="utf-8", newline="") as f:
                reader = csv.DictReader(f)
                rows = []
                for r in reader:
                    row = {k.strip(): v for k, v in r.items()}
                    rows.append(row)
                    if 'key' in row:
                        self.items[row['key']] = row
                self.raw_list = rows
            return bool(self.raw_list)
        except Exception:
            return False

    def get_objective(self, objective_id: str) -> Optional[Dict[str, Any]]:
        """Finds metadata for a specific objective."""
        self.load_local()
        return self.items.get(objective_id.upper())

    def get_rewards(self, objective_id: str) -> Dict[str, int]:
        """Returns {'money': int, 'xp': int} for a given objective."""
        obj = self.get_objective(objective_id)
        if not obj:
            return {"money": 0, "xp": 0}
        
        try:
            money = int(obj.get("money") or 0)
            xp = int(obj.get("experience") or 0)
            return {"money": money, "xp": xp}
        except (ValueError, TypeError):
            return {"money": 0, "xp": 0}

    def refresh_from_web(self, use_safe_fallback=False) -> bool:
        """Central hub for scraping MapRunner and rebuilding the CSV."""
        return _mr_build_csv(self._cache_path, use_safe_fallback=use_safe_fallback)

    def get_js_texts(self) -> List[str]:
        """Provides raw JS text blobs for other systems (e.g. Vehicle Inspector)."""
        texts = []
        for name in ["data.js", "desc.js"]:
            bs = _MR_IN_MEM_FILES.get(name)
            if bs:
                txt = _mr_decode_bytes_to_text(bs)
                if txt: texts.append(txt)
        
        # Also include any other JS files found in memory
        for name, bs in _MR_IN_MEM_FILES.items():
            if name not in ["data.js", "desc.js"] and name.endswith(".js"):
                txt = _mr_decode_bytes_to_text(bs)
                if txt: texts.append(txt)
        return texts

# =============================================================================
# SECTION: Scraper Helpers (Migrated from snowrunner_editor.py)
# =============================================================================

def _mr_http_get(url: str, timeout: int = 15, range_bytes: Optional[tuple] = None):
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "*/*",
        "Accept-Encoding": "identity",
        "Referer": "https://www.maprunner.info/",
        "Origin": "https://www.maprunner.info",
    }
    if range_bytes:
        headers["Range"] = f"bytes={range_bytes[0]}-{range_bytes[1]}"
    
    req = urllib.request.Request(url, headers=headers)
    
    def _open(ctx=None):
        return urllib.request.urlopen(req, timeout=timeout, context=ctx)

    try:
        with _open() as resp:
            data = resp.read()
            resp_headers = {k.lower(): v for k, v in resp.headers.items()}
    except (ssl.SSLCertVerificationError, ssl.SSLError):
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        with _open(ctx) as resp:
            data = resp.read()
            resp_headers = {k.lower(): v for k, v in resp.headers.items()}
            
    # Handle compression
    enc = resp_headers.get("content-encoding", "").lower()
    if enc == "gzip":
        data = gzip.decompress(data)
    elif enc == "deflate":
        data = zlib.decompress(data)
    
    return data, resp_headers

def _mr_decode_bytes_to_text(bs: Optional[bytes]) -> Optional[str]:
    if bs is None: return None
    if isinstance(bs, str): return bs
    try:
        return bs.decode("utf-8")
    except Exception:
        for enc in ("latin-1", "windows-1252", "iso-8859-1"):
            try: return bs.decode(enc, errors="replace")
            except Exception: continue
    return None

def _mr_store_in_memory(name: str, data: bytes, url: Optional[str] = None) -> None:
    _MR_IN_MEM_FILES[name] = data
    if url: _MR_IN_MEM_META[name] = {"url": url}

def _mr_get_file_bytes_or_mem(name: str) -> Optional[bytes]:
    if name in _MR_IN_MEM_FILES: return _MR_IN_MEM_FILES[name]
    return None

def _mr_score_data_js(text: str) -> int:
    if not text or "JSON.parse" not in text: return 0
    score = 0
    for key in ['"category"', '"objectives"', '"rewards"', '"key"']:
        if key in text: score += 10
    return score

def _mr_score_desc_js(text: str) -> int:
    if not text or not re.search(r'\bs\s*:\s*(?:"|\')', text): return 0
    score = 0
    if "UI_" in text: score += 10
    if "_NAME" in text or "_DESC" in text: score += 5
    return score

def _mr_choose_best_js_roles() -> None:
    best_data = (0, None)
    best_desc = (0, None)
    for name, bs in _MR_IN_MEM_FILES.items():
        if not name.lower().endswith(".js"): continue
        text = _mr_decode_bytes_to_text(bs) or ""
        ds = _mr_score_data_js(text)
        cs = _mr_score_desc_js(text)
        if ds > best_data[0]: best_data = (ds, name)
        if cs > best_desc[0]: best_desc = (cs, name)
    
    if best_data[1]:
        _MR_IN_MEM_FILES["data.js"] = _MR_IN_MEM_FILES[best_data[1]]
    if best_desc[1]:
        _MR_IN_MEM_FILES["desc.js"] = _MR_IN_MEM_FILES[best_desc[1]]

def _mr_extract_js_string_literal(text: str, start_idx: int) -> Optional[str]:
    if start_idx >= len(text): return None
    quote = text[start_idx]
    if quote not in ("'", '"'): return None
    k = start_idx + 1
    escaped = False
    out = []
    while k < len(text):
        ch = text[k]
        if escaped:
            out.append(ch); escaped = False; k += 1; continue
        if ch == "\\":
            escaped = True; k += 1; continue
        if ch == quote: return "".join(out)
        out.append(ch)
        k += 1
    return None

def _mr_parse_localization_from_desc_text(txt: str) -> Dict[str, str]:
    result: Dict[str, str] = {}
    pattern = re.compile(
        r'(?:\"([^\"]+)\"|([A-Za-z0-9_\\-]+))\s*:\s*\{.*?s\s*:\s*(?:\"((?:\\.|[^\"\\])*)\"|\'((?:\\.|[^\'\\])*)\')',
        re.DOTALL
    )
    for match in pattern.finditer(txt):
        key = match.group(1) or match.group(2)
        val = match.group(3) or match.group(4) or ""
        if key:
            try:
                val = codecs.decode(val.replace(r"\/", "/"), "unicode_escape")
            except Exception: pass
            result[key] = val.strip()
    return result

def _mr_text_english_score(s: Any) -> float:
    if not s or not isinstance(s, str): return -99.0
    score = 0.0
    s_lower = s.lower()
    for w in _MR_ENGLISH_WORDS:
        if w in s_lower: score += 1.0
    for w in _MR_FORBIDDEN_LANG_WORDS:
        if w in s_lower: score -= 5.0
    if _MR_CYRILLIC_RE.search(s): score -= 10.0
    return score

def _mr_localization_avg_score(loc: Dict[str, str]) -> float:
    if not loc: return -99.0
    vals = list(loc.values())
    sample = vals[:240]
    total = sum(_mr_text_english_score(v) for v in sample)
    return total / max(1, len(sample))

def _mr_collect_localization(desc_js_file: Optional[str]) -> Dict[str, str]:
    merged: Dict[str, str] = {}
    candidates: List[Dict[str, Any]] = []
    
    for name, bs in list(_MR_IN_MEM_FILES.items()):
        if not name.endswith(".js"): continue
        txt = _mr_decode_bytes_to_text(bs) or ""
        parsed = _mr_parse_localization_from_desc_text(txt)
        if not parsed: continue
        avg = _mr_localization_avg_score(parsed)
        candidates.append({"name": name, "loc": parsed, "avg": avg, "count": len(parsed)})

    if not candidates: return {}
    # Sort by avg score (English likeness) then count
    candidates.sort(key=lambda x: (x['avg'], x['count']), reverse=True)
    
    # Merge values from the best candidate
    best = candidates[0]
    for k, v in best['loc'].items():
        merged[k] = v
    return merged

def _mr_build_csv(out_path: str, use_safe_fallback: bool = False) -> bool:
    """Core logic for building the CSV from MapRunner data."""
    try:
        _MR_IN_MEM_FILES.clear()
        
        # Decide which URLs to try based on safe fallback preference
        if use_safe_fallback:
            urls_to_try = list(_MR_SAFE_FALLBACK_URLS)
        else:
            urls_to_try = _MR_SAFE_FALLBACK_URLS + [
                _MR_DATA_URL_DEFAULT,
                _MR_DESC_URL_DEFAULT
            ]
            
        for url in urls_to_try:
            try:
                data, _ = _mr_http_get(url)
                name = os.path.basename(urlparse(url).path)
                _mr_store_in_memory(name, data, url)
            except Exception: continue
            
        _mr_choose_best_js_roles()
        
        data_bs = _MR_IN_MEM_FILES.get("data.js")
        if not data_bs: return False
        
        data_text = _mr_decode_bytes_to_text(data_bs) or ""
        m = re.search(r'JSON\.parse\s*\(\s*(?:"|\')(.*?)(?:"|\')\s*\)', data_text, re.DOTALL)
        if m:
            raw_json = codecs.decode(m.group(1).replace(r'\/', '/'), "unicode_escape")
            data = json.loads(raw_json)
        else:
            return False

        localization = _mr_collect_localization("desc.js")
        
        rows = []
        def walk(o):
            if isinstance(o, dict):
                if "category" in o and "key" in o:
                    cat_key = str(o["key"]).upper()
                    raw_cat = str(o.get("category", "")).upper()
                    
                    if raw_cat in _MR_ALLOWED_CATEGORIES or any(suff in cat_key for suff in _MR_ALLOWED_CATEGORIES):
                        key = cat_key
                        region = "_".join(key.split("_")[:2]) if "_" in key else ""
                        
                        # 1. Classification
                        obj_type = "CONTRACT"
                        if any(x in cat_key for x in ["_TSK", "_TASK"]) or any(x in raw_cat for x in ["_TSK", "TASK"]):
                             obj_type = "TASK"
                        elif any(x in cat_key for x in ["_CNT", "_CONTEST"]) or any(x in raw_cat for x in ["_CNT", "CONTEST"]):
                             obj_type = "CONTEST"
                        elif any(x in cat_key for x in ["_CNS", "_CONTRACT"]) or any(x in raw_cat for x in ["_CNS", "CONTRACT"]):
                             obj_type = "CONTRACT"
                        
                        # 2. Rewards
                        exp = money = 0
                        for r in o.get("rewards", []):
                            if isinstance(r, dict):
                                exp = r.get("experience", exp)
                                money = r.get("money", money)
                        
                        # 3. Cargo Requirements
                        cargo_reqs = []
                        for sub_obj in o.get("objectives", []):
                            if isinstance(sub_obj, dict) and sub_obj.get("cargo"):
                                for c in sub_obj["cargo"]:
                                    if isinstance(c, dict):
                                        c_count = c.get("count", 1)
                                        c_name = localization.get(c.get("name", "")) or c.get("name") or c.get("key") or "Cargo"
                                        cargo_reqs.append(f"{c_count}x {c_name}")
                        
                        display = localization.get(key) or localization.get(o.get("name", "")) or key
                        
                        rows.append({
                            "key": key,
                            "displayName": display,
                            "category": raw_cat,
                            "region": region,
                            "region_name": _MR_REGION_LOOKUP.get(region, region),
                            "type": obj_type,
                            "cargo_needed": "; ".join(cargo_reqs),
                            "experience": exp,
                            "money": money,
                            "descriptionText": localization.get(o.get("description", "")) or "",
                            "Source": "MapRunner"
                        })
            # Recurse
            children = []
            if isinstance(o, dict): children = o.values()
            elif isinstance(o, list): children = o
            for v in children: walk(v)

        walk(data)
        if not rows: return False
        
        fieldnames = ["key", "displayName", "category", "region", "region_name", "type", "cargo_needed", "experience", "money", "descriptionText", "Source"]
        with open(out_path, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(rows)
            
        return True
    except Exception as e:
        print(f"Build CSV failed: {e}")
        return False

# Global accessor
def get_objective_db() -> ObjectiveDatabase:
    return ObjectiveDatabase()
