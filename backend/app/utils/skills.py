"""Skill normalization: maps spelling variants and synonyms to one canonical key, so "JS",
"Javascript" and "javascript" count as the same skill in matching."""

import re
import unicodedata

# canonical key -> variants (all compared after `_basic_normalize`)
_SYNONYMS: dict[str, list[str]] = {
    "javascript": ["js", "ecmascript", "es6"],
    "typescript": ["ts"],
    "python": ["python3", "py"],
    "java": ["java se", "java ee", "jakarta ee"],
    "csharp": ["c#", "c sharp"],
    "dotnet": [".net", "net core", ".net core", "asp.net", "asp.net core", "dot net"],
    "cpp": ["c++"],
    "nodejs": ["node", "node.js", "node js"],
    "react": ["reactjs", "react.js", "react js"],
    "vue": ["vuejs", "vue.js", "vue 3", "vue3"],
    "angular": ["angularjs", "angular.js"],
    "nextjs": ["next.js", "next js", "next"],
    "spring boot": ["springboot", "spring"],
    "postgresql": ["postgres", "psql", "postgre sql"],
    "mysql": ["my sql"],
    "mongodb": ["mongo"],
    "sql": ["t-sql", "tsql", "pl/sql", "plsql"],
    "kubernetes": ["k8s"],
    "docker": ["containers", "docker compose"],
    "aws": ["amazon web services"],
    "azure": ["microsoft azure"],
    "gcp": ["google cloud", "google cloud platform"],
    "ci/cd": ["cicd", "ci cd", "continuous integration", "continuous delivery"],
    "git": ["github", "gitlab"],
    "rest api": ["rest", "restful", "rest apis", "restful api", "api design"],
    "machine learning": ["ml"],
    "artificial intelligence": ["ai"],
    "large language models": ["llm", "llms"],
    "power automate": ["microsoft flow", "ms flow"],
    "power apps": ["powerapps"],
    "power bi": ["powerbi"],
    "sap btp": ["btp", "sap business technology platform"],
    "excel": ["ms excel", "microsoft excel"],
    "scrum": ["agile scrum"],
    "agile": ["agile methodologies"],
    "project management": ["projectmanagement", "projectbeheer"],
    "customer service": ["klantenservice", "service client", "klantendienst"],
    "accounting": ["boekhouding", "comptabilité", "comptabilite"],
    "sales": ["verkoop", "vente"],
    "marketing": [],
    "seo": ["search engine optimization"],
    "html": ["html5"],
    "css": ["css3"],
    "tailwind css": ["tailwind", "tailwindcss"],
    "figma": [],
    "communication": ["communicatie", "communicatievaardigheden"],
    "leadership": ["leiderschap", "leidinggeven"],
}


def _basic_normalize(value: str) -> str:
    value = unicodedata.normalize("NFKC", value).strip().lower()
    value = re.sub(r"\s+", " ", value)
    return value.strip(" .,;:-")


_LOOKUP: dict[str, str] = {}
for canonical, variants in _SYNONYMS.items():
    _LOOKUP[_basic_normalize(canonical)] = canonical
    for variant in variants:
        _LOOKUP[_basic_normalize(variant)] = canonical


def normalize_skill(name: str) -> str:
    key = _basic_normalize(name)
    return _LOOKUP.get(key, key)


def skill_variants(canonical: str) -> list[str]:
    """All spellings of a canonical skill, for finding it in free text."""
    variants = {canonical, *(_SYNONYMS.get(canonical, []))}
    # Single letters / two-letter abbreviations are too ambiguous to search for in prose.
    return sorted((v for v in variants if len(v) > 2 or v in {"c#", "go", "r"}), key=len, reverse=True)


def text_mentions_skill(text: str, canonical: str) -> bool:
    haystack = f" {_basic_normalize(text)} "
    for variant in skill_variants(canonical):
        pattern = r"(?<![\w#+.])" + re.escape(_basic_normalize(variant)) + r"(?![\w#+])"
        if re.search(pattern, haystack):
            return True
    return False
