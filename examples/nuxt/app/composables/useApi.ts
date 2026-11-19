/**
 * Composable for making API requests to the Litestar backend.
 * In development, client-side requests are proxied through Nuxt and SSR requests go directly to Litestar.
 */
export function useApi() {
  const config = useRuntimeConfig()
  const apiPrefix = (config.public.apiPrefix as string) || "/api"

  function resolveUrl(path: string): string {
    const normalizedPath = path.startsWith(apiPrefix) ? path : `${apiPrefix}${path.startsWith("/") ? path : `/${path}`}`

    if (import.meta.client) {
      return normalizedPath
    }

    const apiProxy = (config.litestar as { apiProxy?: string } | undefined)?.apiProxy || "http://127.0.0.1:8000"
    return new URL(normalizedPath, apiProxy).toString()
  }

  return {
    async get<T>(path: string): Promise<T> {
      return await $fetch<T>(resolveUrl(path))
    },

    async post<T>(path: string, body: unknown): Promise<T> {
      return await $fetch<T>(resolveUrl(path), {
        method: "POST",
        body,
      })
    },
  }
}
