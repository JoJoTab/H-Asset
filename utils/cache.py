from functools import wraps
import time

# 메모리 캐시 저장소
_cache = {}


def cache_key(prefix, *args, **kwargs):
    """캐시 키 생성"""
    key_parts = [prefix]
    key_parts.extend([str(arg) for arg in args])
    key_parts.extend([f"{k}:{v}" for k, v in sorted(kwargs.items())])
    return ":".join(key_parts)


def cache(prefix, timeout=300):
    """함수 결과를 메모리에 캐시하는 데코레이터"""

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            key = cache_key(prefix, *args, **kwargs)

            # 캐시에서 결과 확인
            current_time = time.time()
            if key in _cache:
                result, timestamp = _cache[key]
                # 캐시가 유효한지 확인
                if current_time - timestamp < timeout:
                    return result

            # 결과가 없거나 만료되었으면 함수 실행 후 캐시에 저장
            result = func(*args, **kwargs)
            _cache[key] = (result, current_time)
            return result

        return wrapper

    return decorator


def invalidate_cache(prefix, *args, **kwargs):
    """특정 캐시 무효화"""
    key = cache_key(prefix, *args, **kwargs)
    if key in _cache:
        del _cache[key]


def invalidate_cache_pattern(pattern):
    """패턴에 맞는 모든 캐시 무효화"""
    keys_to_delete = []
    for key in _cache.keys():
        if key.startswith(pattern):
            keys_to_delete.append(key)

    for key in keys_to_delete:
        del _cache[key]
