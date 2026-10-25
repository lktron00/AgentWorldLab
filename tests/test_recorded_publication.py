"""Publication contracts: privacy, usage accounting and inert HTML model text."""
import base64
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path
import re
from decimal import Decimal
import pytest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("recorded_publication",ROOT/"scripts/build-study-example.py")
publication=importlib.util.module_from_spec(spec);spec.loader.exec_module(publication)


def test_public_decision_keeps_observation_without_private_provider_ids():
    observation={"view":"study-agent-v1","feed":[{"content":"<script>doSomething()</script>"}]}
    row={"seed":4,"branch":"generic","step":0,"actor":1,"case_id":"test-case",
         "observation":observation,"observation_sha256":publication.fingerprint(observation),
         "action":{"kind":"wait"},"call_id":"private-call","response_id":"private-response"}
    result=publication.public_decision(row,False)
    assert result["observation"]==observation
    assert result["observation_sha256"]==row["observation_sha256"]
    assert result["applied"] is False
    assert "call_id" not in result and "response_id" not in result
    row["observation"]={"unexpected_path":"/Users/someone/private"}
    with pytest.raises(ValueError,match="private content"):
        publication.public_decision(row,False)


def test_public_usage_reconciles_cache_writes_without_charging_reasoning_twice():
    rates={"input":"0.10","cached_input":"0.01","cache_write":"0.125","output":"0.50"}
    usage={"input_tokens":1000,"output_tokens":100,
           "input_tokens_details":{"cached_tokens":200,"cache_write_tokens":100},
           "output_tokens_details":{"reasoning_tokens":30}}
    assert publication.usage_cost(usage,rates)==Decimal("0.0001345")
    usage["output_tokens_details"]["reasoning_tokens"]=101
    with pytest.raises(ValueError,match="Inconsistent"):
        publication.usage_cost(usage,rates)


def test_viewer_embeds_untrusted_model_text_as_data_and_has_exact_script_csp():
    attack="</script><img src=x onerror=alert(1)>"
    report={"title":attack};rows=[{"reason":attack}]
    template=(ROOT/"web/recorded-study-template.html").read_text()
    source=publication.html(report,rows,template)
    assert attack not in source
    packed=re.search(r"const PACKED='([^']+)'",source).group(1)
    assert json.loads(gzip.decompress(base64.b64decode(packed)))=={"report":report,"decisions":rows}
    script=re.search(r'<script id="viewer">(.*?)</script>',source,re.S).group(1)
    digest=base64.b64encode(hashlib.sha256(script.encode()).digest()).decode()
    assert "script-src 'sha256-"+digest+"'" in source
    assert source.count('<script id="viewer">')==1
