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

    def _loads_with_light_repair(raw_text: str) -> Dict[str, Any]:
        try:
            return json.loads(raw_text)
        except json.JSONDecodeError:
            pass

        repaired = re.sub(r",(\s*[}\]])", r"\1", raw_text)
        repaired = re.sub(r'(?<=[}\]"0-9])\s+(?="[^"\n]+"\s*:)', ", ", repaired)
        repaired = re.sub(r"}\s+{", "}, {", repaired)
        repaired = repaired.replace("：", ":")
        try:
            return json.loads(repaired)
        except json.JSONDecodeError as err:
            start = max(0, err.pos - 120)
            end = min(len(raw_text), err.pos + 120)
            snippet = raw_text[start:end].replace("\n", "\\n")
            raise ValueError(f"Model returned invalid JSON near: {snippet}") from err

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    match = re.search(r"\{[\s\S]*\}", text)
    if not match:
        raise ValueError("Model did not return JSON.")

    return _loads_with_light_repair(match.group(0))


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

    primary_model = model_candidates[0]
    final_model = primary_model
    fallback_triggered = False
    fallback_reason = ""
    fallback_from = ""
    fallback_to = ""

    last_error: Optional[Exception] = None
    retry_count = 0
    max_retries = 3
    for model_name in model_candidates[:max_retries]:  # 限制最多重试次数
        body = {
            "model": model_name,
            "temperature": 0.7,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }

        try:
            data = _request_chat_completion(url, headers, body)
            content = data["choices"][0]["message"]["content"]
            result = _extract_json(content)
            # 新增：计算 actual_cost，优先使用模型返回的 token 用量
            usage = data.get("usage") if isinstance(data, dict) else {}
            usage = usage if isinstance(usage, dict) else {}
            prompt_tokens = int(usage.get("prompt_tokens") or usage.get("input_tokens") or 0)
            completion_tokens = int(usage.get("completion_tokens") or usage.get("output_tokens") or 0)
            total_tokens = int(usage.get("total_tokens") or 0)
            if not prompt_tokens:
                prompt_tokens = max(1, len(f"{system_prompt}\n{user_prompt}") // 2)
            if not completion_tokens:
                completion_tokens = max(0, total_tokens - prompt_tokens) if total_tokens > prompt_tokens else max(1, len(content) // 2)
            if not total_tokens:
                total_tokens = prompt_tokens + completion_tokens
            prompt_details = usage.get("prompt_tokens_details") if isinstance(usage.get("prompt_tokens_details"), dict) else {}
            cache_hit_tokens = int(
                usage.get("prompt_cache_hit_tokens")
                or usage.get("cache_hit_tokens")
                or prompt_details.get("cached_tokens")
                or 0
            )
            cache_miss_tokens = int(usage.get("prompt_cache_miss_tokens") or 0)
            if not cache_miss_tokens and cache_hit_tokens:
                cache_miss_tokens = max(0, prompt_tokens - cache_hit_tokens)

            from app.config import _get_model_price_per_1m
            price = _get_model_price_per_1m(model_name)
            input_cache_hit_price = price.get("input_cache_hit", price["input"])
            input_cost = (
                cache_hit_tokens * input_cache_hit_price
                + (cache_miss_tokens or max(0, prompt_tokens - cache_hit_tokens)) * price["input"]
            ) / 1_000_000
            output_cost = completion_tokens * price["output"] / 1_000_000
            actual_cost = input_cost + output_cost
            cost_per_token = actual_cost / total_tokens if total_tokens else 0.0
            cost_per_1k_tokens = cost_per_token * 1000
            final_model = model_name
            fallback_triggered = retry_count > 0
            if fallback_triggered:
                fallback_reason = "no available channels for model"
                fallback_from = primary_model
                fallback_to = final_model
            return {"result": result, "actual_cost": actual_cost, "input_cost": input_cost, "output_cost": output_cost, "retry_count": retry_count, "primary_model": primary_model, "final_model": final_model, "fallback_triggered": fallback_triggered, "fallback_reason": fallback_reason, "fallback_from": fallback_from, "fallback_to": fallback_to, "estimated_tokens": total_tokens, "prompt_tokens": prompt_tokens, "completion_tokens": completion_tokens, "cache_hit_tokens": cache_hit_tokens, "cache_miss_tokens": cache_miss_tokens, "cost_per_token": cost_per_token, "cost_per_1k_tokens": cost_per_1k_tokens, "input_price_per_1m_tokens": price["input"], "input_cache_hit_price_per_1m_tokens": input_cache_hit_price, "output_price_per_1m_tokens": price["output"]}
        except requests.HTTPError as e:
            last_error = e
            retry_count += 1
            detail = (e.response.text if e.response is not None else "").lower()
            if "no available channels for model" in detail and retry_count < max_retries:
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

    response = _call_openai_compatible_json(provider_config, system_prompt, user_prompt)
    return response


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
