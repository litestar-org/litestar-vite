/**
 * Logging utilities for litestar-vite with configurable output.
 *
 * @module
 */

import { formatPath } from "./format-path.js"

/**
 * Logging configuration matching the Python LoggingConfig.
 */
export interface LoggingConfig {
  level: "quiet" | "normal" | "verbose"
  showPathsAbsolute: boolean
  suppressNpmOutput: boolean
  suppressViteBanner: boolean
  timestamps: boolean
}

/**
 * Default logging configuration.
 */
export const defaultLoggingConfig: LoggingConfig = {
  level: "normal",
  showPathsAbsolute: false,
  suppressNpmOutput: false,
  suppressViteBanner: false,
  timestamps: false,
}

/**
 * Log levels in order of verbosity.
 */
const LOG_LEVELS = {
  quiet: 0,
  normal: 1,
  verbose: 2,
} as const

/**
 * Logger instance with configurable behavior.
 */
export interface Logger {
  /** Log a message at normal level */
  info: (message: string) => void
  /** Log a message at verbose level */
  debug: (message: string) => void
  /** Log a warning (always shown except in quiet mode) */
  warn: (message: string) => void
  /** Log an error (always shown) */
  error: (message: string) => void
  /** Format a path according to config (relative or absolute) */
  path: (absolutePath: string, root?: string) => string
  /** Get the current config */
  config: LoggingConfig
}

/**
 * Create a logger instance with the given configuration.
 *
 * @param config - Logging configuration (partial, will be merged with defaults)
 * @returns A Logger instance
 */
export function createLogger(config?: Partial<LoggingConfig> | null): Logger {
  const mergedConfig: LoggingConfig = {
    ...defaultLoggingConfig,
    ...config,
  }

  const levelNum = LOG_LEVELS[mergedConfig.level]

  const formatMessage = (message: string): string => {
    if (mergedConfig.timestamps) {
      const now = new Date().toISOString().slice(11, 23) // HH:mm:ss.SSS
      return `[${now}] ${message}`
    }
    return message
  }

  const formatPathValue = (absolutePath: string, root?: string): string => {
    if (mergedConfig.showPathsAbsolute) {
      return absolutePath
    }
    return formatPath(absolutePath, root)
  }

  return {
    info: (message: string) => {
      if (levelNum >= LOG_LEVELS.normal) {
        console.log(formatMessage(message))
      }
    },
    debug: (message: string) => {
      if (levelNum >= LOG_LEVELS.verbose) {
        console.log(formatMessage(message))
      }
    },
    warn: (message: string) => {
      // Warnings shown at normal and verbose, suppressed at quiet
      if (levelNum >= LOG_LEVELS.normal) {
        console.warn(formatMessage(message))
      }
    },
    error: (message: string) => {
      // Errors always shown
      console.error(formatMessage(message))
    },
    path: formatPathValue,
    config: mergedConfig,
  }
}
