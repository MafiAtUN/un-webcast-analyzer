from pathlib import Path


def test_readme_mentions_project_name():
    readme_text = Path("README.md").read_text(encoding="utf-8")
    assert "UN WebTV Analysis Platform" in readme_text


def test_env_example_has_required_keys():
    env_example = Path(".env.example").read_text(encoding="utf-8")
    assert "AZURE_OPENAI_API_KEY" in env_example
    assert "AZURE_OPENAI_ENDPOINT" in env_example
