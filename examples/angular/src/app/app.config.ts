import { provideHttpClient } from "@angular/common/http"
import type { ApplicationConfig } from "@angular/core"
import { provideRouter } from "@angular/router"

import { appRoutes } from "./app.routes"

export const appConfig: ApplicationConfig = {
  providers: [provideHttpClient(), provideRouter(appRoutes)],
}
