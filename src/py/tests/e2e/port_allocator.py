"""Port allocation utilities for example E2E tests."""

from typing import Final

EXAMPLE_NAMES: Final[list[str]] = [
    "angular",
    "angular-cli",
    "astro",
    "basic",
    "flash",
    "fullstack-typed",
    "jinja",
    "nuxt",
    "react",
    "react-inertia",
    "react-inertia-jinja",
    "svelte",
    "sveltekit",
    "template-htmx",
    "vue",
    "vue-inertia",
    "vue-inertia-jinja",
]


def get_ports_for_example(example_name: str) -> tuple[int, int]:
    """Return deterministic Vite and Litestar ports for an example.

    Ports are derived from the example's index to avoid collisions when running in
    parallel via xdist. Each example owns a block of 10 ports.

    Args:
        example_name: Example directory name from ``EXAMPLE_NAMES``.

    Returns:
        Tuple of ``(vite_port, litestar_port)``.

    Raises:
        ValueError: If ``example_name`` is unknown.
    """
    try:
        index = EXAMPLE_NAMES.index(example_name)
    except ValueError as exc:
        raise ValueError(f"Unknown example name: {example_name}") from exc

    vite_port = 5000 + index * 10
    litestar_port = 8000 + index * 10
    return vite_port, litestar_port


def validate_unique_ports() -> None:
    """Ensure all allocated ports are unique."""
    pairs = [get_ports_for_example(name) for name in EXAMPLE_NAMES]
    if len(pairs) != len(set(pairs)):
        raise AssertionError("Port allocation produced duplicate pairs")
