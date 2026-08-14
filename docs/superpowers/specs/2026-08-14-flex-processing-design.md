# Flex processing for evaluation configurations

## Goal

Let users opt an evaluation configuration into OpenAI Flex processing. Every
Responses API request made while using that configuration must request the
Flex service tier when enabled.

## Scope

- Persist a `flex_enabled` boolean on `EvalConfig`, defaulting to `false`.
- Expose the flag through config create, update, and response schemas.
- Add a checkbox to the configuration create and edit forms.
- Pass the flag to the main evaluation request, prompt-grader requests, and
  Playground requests that execute the saved configuration.
- Send `service_tier="flex"` only when the flag is enabled.

## Deliberate exclusions

- Semantic-similarity graders use the embeddings endpoint, which does not
  accept the Responses API `service_tier` parameter, so they remain unchanged.
- OpenAI resources managed independently of an evaluation configuration, such
  as vector stores and containers, are outside this setting.
- The application will not maintain a model allowlist. OpenAI determines
  whether a selected model and project can use Flex, and any API rejection is
  surfaced through the existing run or Playground error handling.

## Data flow

`EvalConfig.flex_enabled` flows from the API and UI into the saved config.
When the config is executed, the evaluation runner passes the flag to the LLM
client for primary Responses calls and includes it in prompt-grader
configuration. The OpenAI provider and custom prompt grader add
`service_tier="flex"` to their Responses request only when enabled. The
Playground follows the same provider path using its selected config.

## Tests

- Configuration API tests cover the default and persisted flag.
- Provider tests assert the primary Responses request includes the Flex tier
  only when enabled.
- Prompt-grader tests assert its Responses request includes the tier when the
  inherited config flag is enabled.
- Runner and Playground tests assert propagation from `EvalConfig`.
