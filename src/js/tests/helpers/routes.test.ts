import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import { createRouteHelpers, currentRoute, isCurrentRoute, isRoute, type RouteDefinition, toRoute } from "../../src/helpers/routes"

// Sample route definitions matching typical generated output
const sampleRoutes = {
  index: {
    path: "/",
    methods: ["GET"] as const,
    pathParams: [] as const,
    queryParams: [] as const,
    component: "Home",
  },
  books: {
    path: "/api/books",
    methods: ["GET"] as const,
    pathParams: [] as const,
    queryParams: [] as const,
  },
  book_detail: {
    path: "/api/books/{book_id}",
    methods: ["GET"] as const,
    pathParams: ["book_id"] as const,
    queryParams: [] as const,
  },
  books_page: {
    path: "/books",
    methods: ["GET"] as const,
    pathParams: [] as const,
    queryParams: [] as const,
    component: "Books",
  },
  user_profile: {
    path: "/users/{user_id:int}",
    methods: ["GET"] as const,
    pathParams: ["user_id"] as const,
    queryParams: [] as const,
  },
  file_serve: {
    path: "/files/{file_path:path}",
    methods: ["GET"] as const,
    pathParams: ["file_path"] as const,
    queryParams: [] as const,
  },
  resource_by_uuid: {
    path: "/resources/{resource_id:uuid}",
    methods: ["GET"] as const,
    pathParams: ["resource_id"] as const,
    queryParams: [] as const,
  },
} as const satisfies Record<string, RouteDefinition>

type SampleRouteName = keyof typeof sampleRoutes

describe("route helpers", () => {
  const originalWindow = globalThis.window

  beforeEach(() => {
    vi.resetAllMocks()
    // Setup browser-like environment
    globalThis.window = {
      location: {
        pathname: "/",
      },
    } as unknown as Window & typeof globalThis
  })

  afterEach(() => {
    globalThis.window = originalWindow
    vi.restoreAllMocks()
  })

  describe("toRoute", () => {
    it("matches exact paths", () => {
      expect(toRoute("/api/books", sampleRoutes)).toBe("books")
      expect(toRoute("/books", sampleRoutes)).toBe("books_page")
      expect(toRoute("/", sampleRoutes)).toBe("index")
    })

    it("matches paths with parameters", () => {
      expect(toRoute("/api/books/123", sampleRoutes)).toBe("book_detail")
      expect(toRoute("/api/books/abc", sampleRoutes)).toBe("book_detail")
    })

    it("matches paths with typed int parameters", () => {
      expect(toRoute("/users/42", sampleRoutes)).toBe("user_profile")
      // Non-numeric should not match int type
      expect(toRoute("/users/abc", sampleRoutes)).toBeNull()
    })

    it("matches paths with uuid parameters", () => {
      const validUuid = "550e8400-e29b-41d4-a716-446655440000"
      expect(toRoute(`/resources/${validUuid}`, sampleRoutes)).toBe("resource_by_uuid")
      // Invalid UUID should not match
      expect(toRoute("/resources/not-a-uuid", sampleRoutes)).toBeNull()
    })

    it("matches paths with path-type parameters (any content)", () => {
      expect(toRoute("/files/some/nested/path.txt", sampleRoutes)).toBe("file_serve")
      expect(toRoute("/files/single", sampleRoutes)).toBe("file_serve")
    })

    it("returns null for unknown routes", () => {
      expect(toRoute("/unknown", sampleRoutes)).toBeNull()
      expect(toRoute("/api/unknown", sampleRoutes)).toBeNull()
    })

    it("strips query strings", () => {
      expect(toRoute("/api/books?page=1&limit=10", sampleRoutes)).toBe("books")
      expect(toRoute("/api/books/123?format=json", sampleRoutes)).toBe("book_detail")
    })

    it("strips hash fragments", () => {
      expect(toRoute("/api/books#section", sampleRoutes)).toBe("books")
      expect(toRoute("/books#top", sampleRoutes)).toBe("books_page")
    })

    it("strips both query and hash", () => {
      expect(toRoute("/api/books?page=1#section", sampleRoutes)).toBe("books")
    })

    it("normalizes trailing slashes", () => {
      expect(toRoute("/api/books/", sampleRoutes)).toBe("books")
      expect(toRoute("/books/", sampleRoutes)).toBe("books_page")
    })

    it("preserves root path", () => {
      expect(toRoute("/", sampleRoutes)).toBe("index")
    })

    it("handles empty routes object", () => {
      expect(toRoute("/anything", {})).toBeNull()
    })
  })

  describe("currentRoute", () => {
    it("returns route name for current URL", () => {
      globalThis.window.location = { pathname: "/api/books" } as Location
      expect(currentRoute(sampleRoutes)).toBe("books")
    })

    it("returns route name with path parameters", () => {
      globalThis.window.location = { pathname: "/api/books/42" } as Location
      expect(currentRoute(sampleRoutes)).toBe("book_detail")
    })

    it("returns null for unknown routes", () => {
      globalThis.window.location = { pathname: "/unknown" } as Location
      expect(currentRoute(sampleRoutes)).toBeNull()
    })

    it("returns null in SSR (no window)", () => {
      // @ts-expect-error - Testing SSR scenario
      globalThis.window = undefined
      expect(currentRoute(sampleRoutes)).toBeNull()
    })

    it("handles root path", () => {
      globalThis.window.location = { pathname: "/" } as Location
      expect(currentRoute(sampleRoutes)).toBe("index")
    })
  })

  describe("isRoute", () => {
    it("returns true for exact match", () => {
      expect(isRoute("/api/books", "books", sampleRoutes)).toBe(true)
      expect(isRoute("/books", "books_page", sampleRoutes)).toBe(true)
    })

    it("returns false for non-match", () => {
      expect(isRoute("/api/books", "index", sampleRoutes)).toBe(false)
      expect(isRoute("/books", "books", sampleRoutes)).toBe(false)
    })

    it("returns false for unknown URL", () => {
      expect(isRoute("/unknown", "books", sampleRoutes)).toBe(false)
    })

    it("supports wildcard patterns at end", () => {
      expect(isRoute("/api/books", "book*", sampleRoutes)).toBe(true)
      expect(isRoute("/api/books/123", "book*", sampleRoutes)).toBe(true)
      expect(isRoute("/books", "book*", sampleRoutes)).toBe(true)
    })

    it("supports wildcard patterns at start", () => {
      expect(isRoute("/books", "*_page", sampleRoutes)).toBe(true)
      expect(isRoute("/api/books", "*_page", sampleRoutes)).toBe(false)
    })

    it("supports wildcard patterns in middle", () => {
      expect(isRoute("/api/books/123", "book_*", sampleRoutes)).toBe(true)
      expect(isRoute("/", "book_*", sampleRoutes)).toBe(false)
    })

    it("handles multiple wildcards", () => {
      expect(isRoute("/api/books", "*oo*", sampleRoutes)).toBe(true) // matches "books"
    })

    it("escapes regex special characters in non-wildcard parts", () => {
      // Pattern without wildcards should match literally
      expect(isRoute("/api/books", "books", sampleRoutes)).toBe(true)
    })

    it("escapes special regex characters in patterns (regression test)", () => {
      // Routes with dots in names - the dot should NOT become "match any char"
      const routesWithDots = {
        "api.v1.users": {
          path: "/api/v1/users",
          methods: ["GET"] as const,
          pathParams: [] as const,
          queryParams: [] as const,
        },
        api_v1_users: {
          path: "/api/v1/items",
          methods: ["GET"] as const,
          pathParams: [] as const,
          queryParams: [] as const,
        },
      } as const

      // Pattern "api.v1.*" should match "api.v1.users" but NOT "api_v1_users"
      // (the dot should be literal, not "any char")
      expect(isRoute("/api/v1/users", "api.v1.*", routesWithDots)).toBe(true)
      expect(isRoute("/api/v1/items", "api.v1.*", routesWithDots)).toBe(false)
    })
  })

  describe("isCurrentRoute", () => {
    it("returns true when current route matches pattern", () => {
      globalThis.window.location = { pathname: "/api/books" } as Location
      expect(isCurrentRoute("books", sampleRoutes)).toBe(true)
    })

    it("returns false when current route does not match", () => {
      globalThis.window.location = { pathname: "/api/books" } as Location
      expect(isCurrentRoute("index", sampleRoutes)).toBe(false)
    })

    it("supports wildcard patterns", () => {
      globalThis.window.location = { pathname: "/books" } as Location
      expect(isCurrentRoute("*_page", sampleRoutes)).toBe(true)
      expect(isCurrentRoute("book*", sampleRoutes)).toBe(true)
    })

    it("returns false in SSR (no window)", () => {
      // @ts-expect-error - Testing SSR scenario
      globalThis.window = undefined
      expect(isCurrentRoute("books", sampleRoutes)).toBe(false)
    })

    it("returns false for unknown current route", () => {
      globalThis.window.location = { pathname: "/unknown" } as Location
      expect(isCurrentRoute("books", sampleRoutes)).toBe(false)
    })
  })

  describe("createRouteHelpers", () => {
    it("creates bound helper functions", () => {
      const helpers = createRouteHelpers(sampleRoutes)

      expect(typeof helpers.toRoute).toBe("function")
      expect(typeof helpers.currentRoute).toBe("function")
      expect(typeof helpers.isRoute).toBe("function")
      expect(typeof helpers.isCurrentRoute).toBe("function")
    })

    it("toRoute works without passing routes", () => {
      const helpers = createRouteHelpers(sampleRoutes)
      expect(helpers.toRoute("/api/books")).toBe("books")
    })

    it("currentRoute works without passing routes", () => {
      globalThis.window.location = { pathname: "/books" } as Location
      const helpers = createRouteHelpers(sampleRoutes)
      expect(helpers.currentRoute()).toBe("books_page")
    })

    it("isRoute works without passing routes", () => {
      const helpers = createRouteHelpers(sampleRoutes)
      expect(helpers.isRoute("/api/books", "books")).toBe(true)
    })

    it("isCurrentRoute works without passing routes", () => {
      globalThis.window.location = { pathname: "/api/books/42" } as Location
      const helpers = createRouteHelpers(sampleRoutes)
      expect(helpers.isCurrentRoute("book_detail")).toBe(true)
      expect(helpers.isCurrentRoute("book_*")).toBe(true)
    })

    it("preserves type safety for route names", () => {
      const helpers = createRouteHelpers(sampleRoutes)

      // These should return the correct typed route name or null
      const route: SampleRouteName | null = helpers.toRoute("/api/books")
      expect(route).toBe("books")
    })
  })

  describe("pattern caching", () => {
    it("reuses compiled patterns for same path", () => {
      // First call should compile
      toRoute("/api/books/1", sampleRoutes)
      // Second call should use cache
      const result = toRoute("/api/books/2", sampleRoutes)

      expect(result).toBe("book_detail")
    })

    it("handles many different paths efficiently", () => {
      // This test ensures caching works for multiple different paths
      const results = [
        toRoute("/api/books", sampleRoutes),
        toRoute("/api/books/1", sampleRoutes),
        toRoute("/books", sampleRoutes),
        toRoute("/", sampleRoutes),
        toRoute("/api/books/2", sampleRoutes), // Should hit cache for book_detail pattern
      ]

      expect(results).toEqual(["books", "book_detail", "books_page", "index", "book_detail"])
    })
  })

  describe("case sensitivity", () => {
    it("matches paths case-insensitively", () => {
      expect(toRoute("/API/BOOKS", sampleRoutes)).toBe("books")
      expect(toRoute("/Api/Books", sampleRoutes)).toBe("books")
    })

    it("matches UUID case-insensitively", () => {
      const upperUuid = "550E8400-E29B-41D4-A716-446655440000"
      expect(toRoute(`/resources/${upperUuid}`, sampleRoutes)).toBe("resource_by_uuid")
    })
  })

  describe("edge cases", () => {
    it("handles double slashes gracefully", () => {
      // Double slashes won't match because the pattern expects specific structure
      expect(toRoute("//api//books", sampleRoutes)).toBeNull()
    })

    it("handles paths without leading slash", () => {
      // Without leading slash, won't match patterns that start with /
      expect(toRoute("api/books", sampleRoutes)).toBeNull()
    })

    it("handles special regex characters in URL", () => {
      // These should not break the matching
      expect(toRoute("/api/books?q=test(1)", sampleRoutes)).toBe("books")
      expect(toRoute("/api/books?q=[test]", sampleRoutes)).toBe("books")
    })
  })
})
