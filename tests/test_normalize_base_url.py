from fastcontext.agent.llm import normalize_base_url


def test_bare_root_gets_v1():
    assert normalize_base_url("http://localhost:1234") == "http://localhost:1234/v1"


def test_bare_root_trailing_slash():
    assert normalize_base_url("http://127.0.0.1:11434/") == "http://127.0.0.1:11434/v1"


def test_existing_v1_path_kept():
    assert normalize_base_url("http://127.0.0.1:11434/v1/") == "http://127.0.0.1:11434/v1"


def test_api_v1_provider_untouched():
    # OpenRouter and many gateways legitimately serve the OpenAI API at /api/v1.
    assert normalize_base_url("https://openrouter.ai/api/v1") == "https://openrouter.ai/api/v1"


def test_api_v0_untouched():
    assert normalize_base_url("http://localhost:1234/api/v0") == "http://localhost:1234/api/v0"


def test_custom_prefix_untouched():
    assert normalize_base_url("https://llm.corp.com/gateway/v1") == "https://llm.corp.com/gateway/v1"
