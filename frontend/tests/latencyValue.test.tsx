import assert from "node:assert/strict";
import test from "node:test";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";

import {
  FLEX_LATENCY_TITLE,
  LatencyValue,
} from "../src/components/LatencyValue.tsx";

test("LatencyValue marks Flex latency as unreliable", () => {
  const markup = renderToStaticMarkup(
    createElement(LatencyValue, { unreliable: true }, "125ms"),
  );

  assert.match(markup, /line-through/);
  assert.match(markup, new RegExp(FLEX_LATENCY_TITLE));
});

test("LatencyValue leaves standard latency unmodified", () => {
  const markup = renderToStaticMarkup(
    createElement(LatencyValue, { unreliable: false }, "125ms"),
  );

  assert.equal(markup, "125ms");
});
