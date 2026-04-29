# Suite Components

Most AIO repos should stay simple: one repo, one image, one Unraid template.
Some upstream ecosystems need tightly related companion images such as agents,
workers, proxies, or collectors. Use the optional suite component pattern only
when those components share the same upstream product, support surface, catalog
identity, and release ownership.

## When To Use This Pattern

Use a suite repo when:

- the companion is only useful with the primary AIO app
- the repo should share issues, docs, icon assets, and support expectations
- separate Docker images and CA templates are still required
- maintaining another GitHub repository would add overhead without improving the
  user experience

Create a separate repo instead when the app is independently useful, has a
different support audience, or would force unrelated releases into the same
history.

## `components.toml`

Add `components.toml` at the repo root:

```toml
[components.example-aio]
type = "aio"
context = "."
dockerfile = "Dockerfile"
template = "example-aio.xml"
image = "jsonbored/example-aio"
dockerhub_image = "jsonbored/example-aio"
cache_scope = "example-aio-image"
upstream_config = "upstream.toml"
release_suffix = "aio"
test_paths = ["tests/unit", "tests/template", "tests/integration"]
sync_paths = ["example-aio.xml", "assets/app-icon.png"]

[components.example-agent]
type = "agent"
context = "components/example-agent"
dockerfile = "components/example-agent/Dockerfile"
template = "example-agent.xml"
image = "jsonbored/example-agent"
dockerhub_image = "jsonbored/example-agent"
cache_scope = "example-agent-image"
upstream_config = "components/example-agent/upstream.toml"
release_suffix = "agent"
test_paths = ["tests/unit", "tests/template", "tests/integration_agent"]
sync_paths = ["example-agent.xml", "assets/app-icon.png"]
```

Without `components.toml`, scripts fall back to the traditional single-component
repo behavior.

## Release And Security Expectations

- Each component publishes to its own image repository so `latest` remains
  unambiguous.
- Component image publish jobs must require a build-impacting change for that
  component. XML, icon, README, and catalog-only changes should validate and
  sync catalog assets without publishing unchanged images.
- App components should keep upstream-aligned release suffixes like `aio`.
- Companion components should use an explicit suffix like `agent`, `worker`, or
  `proxy`.
- Agents and workers that use host mounts, Docker sockets, or log directories
  must keep those mounts blank by default and document the security tradeoff in
  the XML `Description` and `Requires` text.
- Source XML must validate before any catalog sync to `awesome-unraid`.
