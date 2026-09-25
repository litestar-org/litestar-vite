import { describe, expectTypeOf, it } from "vitest"
import { createTypedChannels } from "../../src/helpers/channels.js"
import { createEventStream } from "../../src/helpers/stream.js"
import type { InboundMessage, OutboundMessage, RealtimeChannels } from "./generated-channels.fixture.js"

describe("stream send type contracts", () => {
  it("verifies typed send and reject invalid channel keys or payloads", () => {
    const channels = createTypedChannels<RealtimeChannels>()
    const chat = channels.stream("ws_chat", {
      onEvent: (frame) => {
        expectTypeOf(frame).toEqualTypeOf<OutboundMessage>()
      },
      params: { room_id: "1" },
    })

    expectTypeOf(chat.send).parameter(0).toEqualTypeOf<InboundMessage>()

    // @ts-expect-error invalid payload property
    chat.send({ wrong: true })

    // @ts-expect-error unknown channel key
    channels.stream("does_not_exist", { onEvent: () => {} })

    expectTypeOf(createEventStream<string>({ url: "/x", onEvent: () => {} }).send)
      .parameter(0)
      .toEqualTypeOf<never>()
  })
})
