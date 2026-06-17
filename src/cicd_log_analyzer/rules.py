from dataclasses import dataclass
import re
from typing import Pattern


@dataclass(frozen=True)
class Rule:
    """A detection rule for CI/CD log lines."""

    rule_id: str
    category: str
    severity: str
    pattern: Pattern[str]
    recommendation: str


RULES: list[Rule] = [
    Rule(
        "PROXY_407",
        "Network / Proxy",
        "high",
        re.compile(r"(407 Proxy Authentication Required|ProxyError|proxy.*authentication)", re.I),
        "Check HTTP_PROXY/HTTPS_PROXY and Docker daemon proxy configuration.",
    ),
    Rule(
        "DNS_RESOLUTION",
        "Network / DNS",
        "medium",
        re.compile(r"(NameResolutionError|Temporary failure in name resolution|Could not resolve host)", re.I),
        "Verify DNS configuration, VPN/corporate network access, and Artifactory host name.",
    ),
    Rule(
        "DISK_SPACE",
        "Infrastructure",
        "high",
        re.compile(r"(No space left on device|ENOSPC|Use%\s+100%|100% used)", re.I),
        "Clean workspace/Docker cache or increase disk size on the build agent.",
    ),
    Rule(
        "AUTH_FAILURE",
        "Authentication",
        "high",
        re.compile(r"(401 Unauthorized|403 Forbidden|invalid credentials|Authentication failed)", re.I),
        "Validate Jenkins/Bamboo credentials and token permissions.",
    ),
    Rule(
        "DOCKER_DAEMON",
        "Docker",
        "medium",
        re.compile(r"(Cannot connect to the Docker daemon|docker: Error response from daemon|docker pull.*failed)", re.I),
        "Check Docker service status, registry access, and daemon proxy settings.",
    ),
    Rule(
        "TIMEOUT",
        "Timeout",
        "medium",
        re.compile(r"(timed out|timeout exceeded|Read timed out)", re.I),
        "Increase timeout only after confirming that network and dependency services are healthy.",
    ),
    Rule(
        "TEST_FAILURE",
        "Tests",
        "medium",
        re.compile(r"(^FAILED\s+.+::|AssertionError|\b\d+\s+failed,\s+\d+\s+passed\b|There were test failures)", re.I,),
        "Open the failing test output and reproduce locally before retrying the pipeline.",
    ),
    Rule(
        "COMPILATION_ERROR",
        "Build / Compilation",
        "high",
        re.compile(r"(^|\s)(fatal error:|compilation terminated|undefined reference|error: command .* failed)", re.I),
        "Inspect compiler output and recent source/header dependency changes.",
    ),
]

SEVERITY_SCORE = {"low": 1, "medium": 2, "high": 3}
