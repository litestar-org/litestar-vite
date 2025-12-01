import { provideHttpClient } from "@angular/common/http"
import type { ApplicationConfig } from "@angular/core"
import { provideRouter } from "@angular/router"

import { appRoutes } from "./app.routes"

// Angular 21+ is zoneless by default - no provideZonelessChangeDetection() needed
export const appConfig: ApplicationConfig = {
  providers: [provideHttpClient(), provideRouter(appRoutes)],
}
