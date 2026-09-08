"""
WP-001 bilingual: тесты языкового параметра (params.yaml → language).

Покрывает:
  1. day-open-scaffold.sh — frontmatter `lang:` + agent: + заголовок DayPlan
     на языке установки (en/ru/по умолчанию).
  2. strategist.sh — INSTALL_LANGUAGE parsing (изолированный фрагмент через bash -c).
"""

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent  # FMT-exocortex-template/
SCAFFOLD = ROOT / "scripts" / "day-open-scaffold.sh"
STRATEGIST = ROOT / "roles" / "strategist" / "scripts" / "strategist.sh"


def _make_ws(tmp_path: Path, params: str | None) -> Path:
    ws = tmp_path / "workspace"
    (ws / "DS-strategy").mkdir(parents=True)
    if params is not None:
        (ws / "params.yaml").write_text(params, encoding="utf-8")
    return ws


def _scaffold_stdout(ws: Path) -> str:
    return subprocess.run(
        ["bash", str(SCAFFOLD)],
        capture_output=True, text=True,
        env={"PATH": "/usr/bin:/bin", "HOME": str(ws.parent / "home"),
             "IWE_WORKSPACE": str(ws)},
    ).stdout


# --- day-open-scaffold: frontmatter + заголовок ---

def test_scaffold_en_language(tmp_path):
    ws = _make_ws(tmp_path, "language: en\n")
    out = _scaffold_stdout(ws)
    assert "lang: en" in out
    assert "agent: Strategist" in out
    assert "# Day Plan: " in out
    assert "Strategist" in out


def test_scaffold_ru_language_explicit(tmp_path):
    ws = _make_ws(tmp_path, "language: ru\n")
    out = _scaffold_stdout(ws)
    assert "lang: ru" in out
    assert "agent: Стратег" in out


def test_scaffold_ru_default_no_params(tmp_path):
    ws = _make_ws(tmp_path, None)
    out = _scaffold_stdout(ws)
    assert "lang: ru" in out
    assert "agent: Стратег" in out


def test_scaffold_unknown_value_falls_back_ru(tmp_path):
    ws = _make_ws(tmp_path, "language: de\n")
    out = _scaffold_stdout(ws)
    assert "lang: ru" in out


# --- strategist: INSTALL_LANGUAGE parsing (extracted snippet) ---

SNIPPET = r'''
IWE_WS_ROOT="{ws}"
INSTALL_LANGUAGE="ru"
if [ -f "$IWE_WS_ROOT/params.yaml" ]; then
    _lang_val=$(grep -E '^language:[[:space:]]*' "$IWE_WS_ROOT/params.yaml" 2>/dev/null | head -1 | sed 's/^language:[[:space:]]*//;s/[[:space:]]*#.*//;s/"//g' | tr -d '[:space:]')
    case "$_lang_val" in
        en|EN) INSTALL_LANGUAGE="en" ;;
        ru|RU|"") INSTALL_LANGUAGE="ru" ;;
        *) INSTALL_LANGUAGE="ru" ;;
    esac
fi
echo "$INSTALL_LANGUAGE"
'''


def _parse_language(ws: Path) -> str:
    script = SNIPPET.replace("{ws}", str(ws))
    r = subprocess.run(["bash", "-c", script], capture_output=True, text=True)
    return r.stdout.strip()


def test_strategist_parse_en(tmp_path):
    ws = _make_ws(tmp_path, "language: en\n")
    assert _parse_language(ws) == "en"


def test_strategist_parse_en_quoted_and_comment(tmp_path):
    ws = _make_ws(tmp_path, 'language: "en"  # installation language\n')
    assert _parse_language(ws) == "en"


def test_strategist_parse_ru_default(tmp_path):
    ws = _make_ws(tmp_path, None)
    assert _parse_language(ws) == "ru"


def test_strategist_parse_unknown_falls_back(tmp_path):
    ws = _make_ws(tmp_path, "language: de\n")
    assert _parse_language(ws) == "ru"


def test_strategist_script_contains_no_hardcoded_language_ban():
    """Жёсткий запрет «ТОЛЬКО на русском» исчез из strategist.sh (WP-001)."""
    assert "ТОЛЬКО на русском" not in STRATEGIST.read_text(encoding="utf-8")


def test_language_check_py_reference_removed():
    """Мёртвые ссылки lib/language-check.py удалены из peer-адаптеров (WP-001, P3)."""
    for adapter in ["codex-peer-adapter.sh", "hermes-peer-adapter.sh"]:
        text = (ROOT / "scripts" / adapter).read_text(encoding="utf-8")
        assert "language-check.py" not in text.replace(
            "WP-484 Ф89: language-check блок удалён (WP-001): файл lib/language-check.py", ""
        ).replace("# никогда не поставлялся (мёртвая ссылка)", ""), adapter


def test_scaffold_no_hardcoded_russian_header_in_en(tmp_path):
    """EN: frontmatter + заголовок DayPlan без русских слов месяца (WP-001 объём:
    frontmatter/заголовок/автономные дайджесты; перевод тела DayPlan — WP-415)."""
    ws = _make_ws(tmp_path, "language: en\n")
    out = _scaffold_stdout(ws)
    header = next(line for line in out.splitlines() if line.startswith("# Day Plan"))
    fm_lang = next(line for line in out.splitlines() if line.startswith("lang:"))
    assert "lang: en" == fm_lang
    assert not any(m in header for m in ["января", "сентября", "Понедельник", "Вторник"]), header
    assert "September" in header
