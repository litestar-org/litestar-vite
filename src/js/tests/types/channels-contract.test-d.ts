import { describe, expectTypeOf, it } from "vitest"
import type { InboundMessage, OutboundMessage, RealtimeChannels, ServerEvent } from "./generated-channels.fixture.js"

describe("channels contract types", () => {
  it("verifies channel send and receive payload contracts", () => {
    expectTypeOf<RealtimeChannels["ws_chat"]["send"]>().toEqualTypeOf<InboundMessage>()
    expectTypeOf<RealtimeChannels["ws_chat"]["receive"]>().toEqualTypeOf<OutboundMessage>()
    expectTypeOf<RealtimeChannels["stream_events"]["send"]>().toEqualTypeOf<never>()
    expectTypeOf<RealtimeChannels["stream_events"]["receive"]>().toEqualTypeOf<ServerEvent>()
    expectTypeOf<RealtimeChannels["ws_chat"]["params"]>().toEqualTypeOf<{ room_id: string }>()
    expectTypeOf<RealtimeChannels["notifications"]["protocol"]>().toEqualTypeOf<"channels">()
  })
})
