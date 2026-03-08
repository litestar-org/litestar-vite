// Example route snapshot for stable builds. Update when the example backend routes change.

type EmptyParams = Record<string, never>

export type RouteName = "book_detail" | "books" | "books_page" | "index" | "summary"

export interface RoutePathParams {
  book_detail: {
    book_id: number
  }
  books: EmptyParams
  books_page: EmptyParams
  index: EmptyParams
  summary: EmptyParams
}

export interface RouteQueryParams {
  book_detail: EmptyParams
  books: EmptyParams
  books_page: EmptyParams
  index: EmptyParams
  summary: EmptyParams
}

type MergeParams<A, B> = A extends EmptyParams ? (B extends EmptyParams ? EmptyParams : B) : B extends EmptyParams ? A : A & B
export type RouteParams<T extends RouteName> = MergeParams<RoutePathParams[T], RouteQueryParams[T]>

export const routeDefinitions = {
  book_detail: {
    path: "/api/books/{book_id}",
    methods: ["GET"] as const,
    method: "get",
    pathParams: ["book_id"] as const,
    queryParams: [] as const,
  },
  books: {
    path: "/api/books",
    methods: ["GET"] as const,
    method: "get",
    pathParams: [] as const,
    queryParams: [] as const,
  },
  books_page: {
    path: "/books",
    methods: ["GET"] as const,
    method: "get",
    pathParams: [] as const,
    queryParams: [] as const,
  },
  index: {
    path: "/",
    methods: ["GET"] as const,
    method: "get",
    pathParams: [] as const,
    queryParams: [] as const,
  },
  summary: {
    path: "/api/summary",
    methods: ["GET"] as const,
    method: "get",
    pathParams: [] as const,
    queryParams: [] as const,
  },
} as const

type RoutesWithRequiredParams = "book_detail"
type RoutesWithoutRequiredParams = Exclude<RouteName, RoutesWithRequiredParams>

export function route<T extends RoutesWithoutRequiredParams>(name: T, params?: RouteParams<T>): string
export function route<T extends RoutesWithRequiredParams>(name: T, params: RouteParams<T>): string
export function route<T extends RouteName>(name: T, params?: RouteParams<T>): string {
  const definition = routeDefinitions[name]
  let url: string = definition.path

  if (params) {
    for (const param of definition.pathParams) {
      const value = (params as Record<string, unknown>)[param]
      if (value !== undefined) {
        url = url.replace(`{${param}}`, String(value))
      }
    }
  }

  return url
}
