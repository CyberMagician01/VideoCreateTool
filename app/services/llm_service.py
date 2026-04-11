import json
import re
from typing import Any, Dict, List, Optional

import requests

from app.config import (
    DEFAULT_PROVIDER,
    MODEL_PROVIDERS,
    QINIU_AK,
    QINIU_SK,
    QINIU_LLM_TIMEOUT,
    QINIU_LLM_TIMEOUT_RETRIES,
    QINIU_TEXT_API_KEY,
    QINIU_LLM_FALLBACK_MODELS,
)

_NO_PROXY_SESSION = requests.Session()
_NO_PROXY_SESSION.trust_env = False


def _request_no_proxy(method: str, url: str, **kwargs: Any) -> requests.Response:
    return _NO_PROXY_SESSION.request(method=method, url=url, **kwargs)


def _request_chat_completion(url: str, headers: Dict[str, str], body: Dict[str, Any]) -> Dict[str, Any]:
    last_error: Optional[Exception] = None
    retry_count = max(QINIU_LLM_TIMEOUT_RETRIES, 0)
    timeout_sec = max(QINIU_LLM_TIMEOUT, 1)

    for attempt in range(retry_count + 1):
        try:
            response = _request_no_proxy(
                "POST",
                url,
                headers=headers,
                json=body,
                timeout=timeout_sec,
                verify=False,
            )
            response.raise_for_status()
            return response.json()
        except requests.Timeout as e:
            last_error = e
            if attempt >= retry_count:
                break

    if last_error:
        raise requests.ReadTimeout(
            f"LLM request timed out after {timeout_sec}s (retried {retry_count} times)"
        ) from last_error

    raise RuntimeError("Model request failed")


def _extract_json(text: str) -> Dict[str, Any]:
    text = text.strip()

    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?", "", text).strip()
        text = re.sub(r"```$", "", text).strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    match = re.search(r"\{[\s\S]*\}", text)
    if not match:
        raise ValueError("Model did not return JSON.")

    return json.loads(match.group(0))


def _resolve_url(base_url: str, path_or_url: str) -> str:
    text = str(path_or_url or "").strip()
    if text.startswith("http://") or text.startswith("https://"):
        return text

    base = str(base_url or "").strip().rstrip("/")
    if not base:
        raise RuntimeError("QINIU base url is missing in .env")

    if not text:
        return base

    if not text.startswith("/"):
        text = f"/{text}"
    return f"{base}{text}"


def _build_url_candidates(base_url: str, path_or_url: str) -> List[str]:
    primary = _resolve_url(base_url, path_or_url)
    candidates = [primary]

    base = str(base_url or "").strip().rstrip("/")
    path = str(path_or_url or "").strip()

    if path and not path.startswith("/"):
        path = f"/{path}"

    if base.endswith("/api/v1"):
        alt_base = base[: -len("/api/v1")] + "/v1"
        candidates.append(f"{alt_base}{path}")
    elif base.endswith("/v1"):
        alt_base = base[: -len("/v1")] + "/api/v1"
        candidates.append(f"{alt_base}{path}")

    deduped: List[str] = []
    for url in candidates:
        if url not in deduped:
            deduped.append(url)
    return deduped


def _is_not_found_or_method_not_allowed(err: requests.HTTPError) -> bool:
    response = err.response
    if response is None:
        return False

    if response.status_code in {404, 405}:
        return True

    detail = response.text.lower()
    return ("not found" in detail) or ("method not allowed" in detail)


def _build_qiniu_aksk_headers(*, include_content_type: bool = True) -> Dict[str, str]:
    if not QINIU_AK or not QINIU_SK:
        raise RuntimeError("QINIU_AK or QINIU_SK is missing in .env")

    headers = {
        "X-Qiniu-AK": QINIU_AK,
        "X-Qiniu-SK": QINIU_SK,
        "Authorization": f"QiniuAKSK {QINIU_AK}:{QINIU_SK}",
    }
    if include_content_type:
        headers["Content-Type"] = "application/json"
    return headers


def _has_qiniu_text_credential() -> bool:
    return bool(QINIU_TEXT_API_KEY or (QINIU_AK and QINIU_SK))


def _build_qiniu_headers(scope: str, *, include_content_type: bool = True) -> Dict[str, str]:
    headers: Dict[str, str] = {}
    if include_content_type:
        headers["Content-Type"] = "application/json"

    if scope == "text" and QINIU_TEXT_API_KEY:
        headers["Authorization"] = f"Bearer {QINIU_TEXT_API_KEY}"
        return headers

    if scope == "video" and QINIU_TEXT_API_KEY:
        headers["Authorization"] = f"Bearer {QINIU_TEXT_API_KEY}"
        return headers

    return {**headers, **_build_qiniu_aksk_headers(include_content_type=False)}


def _get_model_candidates(primary_model: str) -> List[str]:
    candidates: List[str] = []
    if primary_model:
        candidates.append(primary_model)
    for item in QINIU_LLM_FALLBACK_MODELS:
        if item not in candidates:
            candidates.append(item)
    return candidates


def _call_openai_compatible_json(provider_config: Dict[str, Any], system_prompt: str, user_prompt: str) -> Dict[str, Any]:
    url = _resolve_url(provider_config.get("base_url", ""), "/chat/completions")
    headers: Dict[str, str] = {"Content-Type": "application/json"}

    if provider_config.get("type") == "qiniu_openai_compatible":
        headers.update(_build_qiniu_headers("text", include_content_type=False))
    else:
        api_key = str(provider_config.get("api_key", "")).strip()
        if not api_key:
            raise RuntimeError(f"{provider_config.get('name', 'Provider')} API key is missing in .env")
        headers["Authorization"] = f"Bearer {api_key}"

    model_candidates = _get_model_candidates(str(provider_config.get("model", "")).strip())
    if not model_candidates:
        raise RuntimeError("No model configured for qiniu provider")

    last_error: Optional[Exception] = None
    for model_name in model_candidates:
        body = {
            "model": model_name,
            "temperature": 0.7,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }

        try:
            data = _request_chat_completion(url, headers, body)
            content = data["choices"][0]["message"]["content"]
            return _extract_json(content)
        except requests.HTTPError as e:
            last_error = e
            detail = (e.response.text if e.response is not None else "").lower()
            if "no available channels for model" in detail:
                continue
            raise
        except requests.Timeout as e:
            last_error = e
            continue

    if last_error:
        raise last_error
    raise RuntimeError("Model request failed")


def _call_openai_compatible_text(provider_config: Dict[str, Any], system_prompt: str, user_prompt: str) -> str:
    url = _resolve_url(provider_config.get("base_url", ""), "/chat/completions")
    headers: Dict[str, str] = {"Content-Type": "application/json"}

    if provider_config.get("type") == "qiniu_openai_compatible":
        headers.update(_build_qiniu_headers("text", include_content_type=False))
    else:
        api_key = str(provider_config.get("api_key", "")).strip()
        if not api_key:
            raise RuntimeError(f"{provider_config.get('name', 'Provider')} API key is missing in .env")
        headers["Authorization"] = f"Bearer {api_key}"

    model_candidates = _get_model_candidates(str(provider_config.get("model", "")).strip())
    if not model_candidates:
        raise RuntimeError("No model configured for qiniu provider")

    last_error: Optional[Exception] = None
    for model_name in model_candidates:
        body = {
            "model": model_name,
            "temperature": 0.8,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }

        try:
            data = _request_chat_completion(url, headers, body)
            return data["choices"][0]["message"]["content"].strip()
        except requests.HTTPError as e:
            last_error = e
            detail = (e.response.text if e.response is not None else "").lower()
            if "no available channels for model" in detail:
                continue
            raise
        except requests.Timeout as e:
            last_error = e
            continue

    if last_error:
        raise last_error
    raise RuntimeError("Model request failed")


def _call_provider_json(provider: str, system_prompt: str, user_prompt: str) -> Dict[str, Any]:
    provider_config = MODEL_PROVIDERS.get(provider)
    if not provider_config:
        raise ValueError(f"Unknown provider: {provider}")

    if provider_config.get("requires_qiniu_credential") and (not _has_qiniu_text_credential()):
        raise RuntimeError("QINIU_TEXT_API_KEY or QINIU_AK/QINIU_SK is missing in .env")

    return _call_openai_compatible_json(provider_config, system_prompt, user_prompt)


def _call_provider_text(provider: str, system_prompt: str, user_prompt: str) -> str:
    provider_config = MODEL_PROVIDERS.get(provider)
    if not provider_config:
        raise ValueError(f"Unknown provider: {provider}")

    if provider_config.get("requires_qiniu_credential") and (not _has_qiniu_text_credential()):
        raise RuntimeError("QINIU_TEXT_API_KEY or QINIU_AK/QINIU_SK is missing in .env")

    return _call_openai_compatible_text(provider_config, system_prompt, user_prompt)


def _call_qwen_json(system_prompt: str, user_prompt: str) -> Dict[str, Any]:
    return _call_provider_json(DEFAULT_PROVIDER, system_prompt, user_prompt)


def _call_qwen_text(system_prompt: str, user_prompt: str) -> str:
    return _call_provider_text(DEFAULT_PROVIDER, system_prompt, user_prompt)
