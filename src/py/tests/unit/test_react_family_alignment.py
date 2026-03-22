import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
EXAMPLES_ROOT = ROOT / "examples"
TEMPLATE_ROOT = ROOT / "src" / "py" / "litestar_vite" / "templates"


def _load_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text())


def test_react_spa_entrypoints_match_current_vite_bootstrap() -> None:
    example_main = (EXAMPLES_ROOT / "react" / "src" / "main.tsx").read_text()
    template_main = (TEMPLATE_ROOT / "react" / "src" / "main.tsx.j2").read_text()

    for text in (example_main, template_main):
        assert 'import App from "./App.tsx"' in text
        assert 'createRoot(document.getElementById("root")!).render(' in text
        assert "StrictMode" in text


def test_react_inertia_bootstrap_matches_current_adapter_shape() -> None:
    hybrid_main = (EXAMPLES_ROOT / "react-inertia" / "resources" / "main.tsx").read_text()
    jinja_main = (EXAMPLES_ROOT / "react-inertia-jinja" / "resources" / "main.tsx").read_text()
    template_main = (TEMPLATE_ROOT / "react-inertia" / "resources" / "main.tsx.j2").read_text()
    template_ssr = (TEMPLATE_ROOT / "react-inertia" / "resources" / "ssr.tsx.j2").read_text()

    for text in (hybrid_main, jinja_main):
        assert "StrictMode" not in text
        assert "defaults:" in text
        assert "future: {" in text
        assert "useScriptElementForInitialPage: true" in text
        assert "createRoot(el).render(<App {...props} />)" in text

    assert "StrictMode" not in template_main
    assert "use_script_element=True" in template_main
    assert "createRoot(el).render(<App {...props} />);" in template_main
    assert "use_script_element=True" in template_ssr


def test_react_family_examples_pin_current_stable_versions() -> None:
    react_package = _load_json(EXAMPLES_ROOT / "react" / "package.json")
    react_inertia_package = _load_json(EXAMPLES_ROOT / "react-inertia" / "package.json")
    react_inertia_jinja_package = _load_json(EXAMPLES_ROOT / "react-inertia-jinja" / "package.json")

    assert react_package["dependencies"] == {
        "react": "19.2.4",
        "react-dom": "19.2.4",
        "react-router-dom": "7.13.1",
        "axios": "1.13.6",
    }
    assert react_package["devDependencies"] == {
        "@vitejs/plugin-react": "6.0.1",
        "@types/react": "19.2.14",
        "@types/react-dom": "19.2.3",
        "@tailwindcss/vite": "4.2.2",
        "tailwindcss": "4.2.2",
        "typescript": "5.9.3",
        "litestar-vite-plugin": "file:../..",
        "vite": "8.0.1",
        "@hey-api/openapi-ts": "0.94.0",
    }

    for package in (react_inertia_package, react_inertia_jinja_package):
        assert package["dependencies"] == {
            "@inertiajs/react": "2.3.17",
            "react": "19.2.4",
            "react-dom": "19.2.4",
            "axios": "1.13.6",
            "zod": "4.3.6",
        }
        assert package["devDependencies"] == {
            "@types/react": "19.2.14",
            "@types/react-dom": "19.2.3",
            "@vitejs/plugin-react": "6.0.1",
            "@tailwindcss/vite": "4.2.2",
            "tailwindcss": "4.2.2",
            "litestar-vite-plugin": "file:../..",
            "typescript": "5.9.3",
            "vite": "8.0.1",
            "@hey-api/openapi-ts": "0.94.0",
        }

    assert react_inertia_package["name"] == "react-inertia"
    assert react_inertia_jinja_package["name"] == "react-inertia-jinja"


def test_react_inertia_template_package_pins_current_stable_versions() -> None:
    text = (TEMPLATE_ROOT / "react-inertia" / "package.json.j2").read_text()

    expected_fragments = (
        '"{{ dep }}": "{{ package_version(dep) }}"',
        '"axios": "{{ package_version(\'axios\') }}"',
        '"zod": "{{ package_version(\'zod\') }}"',
        '"@tailwindcss/vite": "{{ package_version(\'@tailwindcss/vite\') }}"',
        '"tailwindcss": "{{ package_version(\'tailwindcss\') }}"',
        '"@hey-api/openapi-ts": "{{ package_version(\'@hey-api/openapi-ts\') }}"',
        '"litestar-vite-plugin": "{{ package_version(\'litestar-vite-plugin\') }}"',
    )

    for fragment in expected_fragments:
        assert fragment in text

    assert '"latest"' not in text


def test_react_inertia_jinja_example_uses_script_element_config() -> None:
    hybrid_app_text = (EXAMPLES_ROOT / "react-inertia" / "app.py").read_text()
    app_text = (EXAMPLES_ROOT / "react-inertia-jinja" / "app.py").read_text()

    assert "~37% smaller" not in hybrid_app_text
    assert "use_script_element requires matching client bootstrap" in hybrid_app_text
    assert "use_script_element=True" in app_text
    assert "{{ page | tojson | e }}" not in app_text
