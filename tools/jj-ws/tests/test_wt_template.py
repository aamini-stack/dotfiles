import subprocess

import pytest
from jjws.wt.template import TemplateError, hash_port, render, sanitize_db

VARS = {
    "name": "feat/auth",
    "repo": "app",
    "workspace_path": "/workspaces/app/feat-auth",
    "primary_path": "/src/app",
}


def test_renders_variables_and_filters():
    assert render("{{ repo }}/{{ name | sanitize }}", VARS) == "app/feat-auth"
    assert sanitize_db("Feature/Auth").startswith("feature_auth_")
    port = int(hash_port("feat/auth"))
    assert 10000 <= port <= 19999


def test_supports_worktrunk_style_concatenation():
    app = render("{{ name | hash_port }}", VARS)
    database = render("{{ ('db-' ~ name) | hash_port }}", VARS)
    assert app != database


def test_unknown_variable_and_filter_fail():
    with pytest.raises(TemplateError, match="unknown variable"):
        render("{{ branch }}", VARS)
    with pytest.raises(TemplateError, match="unknown filter"):
        render("{{ name | nope }}", VARS)


def test_shell_rendering_is_safe_inside_existing_quotes(tmp_path):
    injected = tmp_path / "injected"
    value = f"x'$(touch {injected})"
    command = render(
        "VALUE='{{ name }}'; printf %s \"$VALUE\" > result",
        {"name": value},
        shell=True,
    )

    subprocess.run(command, cwd=tmp_path, shell=True, check=True)

    assert not injected.exists()
    assert (tmp_path / "result").read_text() == value


def test_shell_rendering_ignores_apostrophes_in_comments(tmp_path):
    injected = tmp_path / "injected"
    value = f"$(touch {injected})"
    command = render(
        "# don't treat this apostrophe as a quote\nprintf '%s' {{ name }} > result",
        {"name": value},
        shell=True,
    )

    subprocess.run(command, cwd=tmp_path, shell=True, check=True)

    assert not injected.exists()
    assert (tmp_path / "result").read_text() == value


def test_shell_rendering_recognizes_comments_after_operator(tmp_path):
    injected = tmp_path / "injected"
    value = f"$(touch {injected})"
    command = render(
        "true;# don't lose quote state\nprintf '%s' {{ name }} > result",
        {"name": value},
        shell=True,
    )

    subprocess.run(command, cwd=tmp_path, shell=True, check=True)

    assert not injected.exists()
    assert (tmp_path / "result").read_text() == value
