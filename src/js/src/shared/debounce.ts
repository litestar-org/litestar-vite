/**
 * Shared debounce utility for litestar-vite.
 *
 * @module
 */

/**
 * Creates a debounced function that delays invoking `func` until after
 * `wait` milliseconds have elapsed since the last invocation.
 *
 * This implementation is type-safe and properly infers argument types.
 *
 * @param func - The function to debounce
 * @param wait - Milliseconds to wait before invoking
 * @returns Debounced function with the same signature
 *
 * @example
 * ```ts
 * const debouncedSave = debounce((data: string) => {
 *   console.log('Saving:', data)
 * }, 300)
 *
 * debouncedSave('hello') // Delayed
 * debouncedSave('world') // Cancels previous, delays again
 * // Only 'world' is logged after 300ms
 * ```
 */
export function debounce<Args extends unknown[]>(func: (...args: Args) => void, wait: number): (...args: Args) => void {
  let timeout: ReturnType<typeof setTimeout> | null = null

  return (...args: Args): void => {
    if (timeout !== null) {
      clearTimeout(timeout)
    }
    timeout = setTimeout(() => {
      func(...args)
      timeout = null
    }, wait)
  }
}
