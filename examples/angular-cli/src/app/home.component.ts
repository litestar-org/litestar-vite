import { HttpClient } from "@angular/common/http"
import { Component, computed, inject, type OnInit, signal } from "@angular/core"

import { route, routeDefinitions } from "../generated/routes"

type Book = {
  id: number
  title: string
  author: string
  year: number
  tags: string[]
}

type Summary = {
  app: string
  headline: string
  total_books: number
  featured: Book
}
type RouteName = keyof typeof routeDefinitions
type RouteDefinition = (typeof routeDefinitions)[RouteName]
type RouteEntry = [RouteName, RouteDefinition]

@Component({
  selector: "app-home",
  standalone: true,
  template: `
    <main class="mx-auto max-w-5xl space-y-6 px-4 py-10">
      <header class="space-y-2">
        <p class="font-semibold text-[#edb641] text-sm uppercase tracking-[0.14em]">Litestar · Vite</p>
        <h1 class="font-semibold text-3xl text-[#202235]">Library (Angular CLI)</h1>
        <p class="max-w-3xl text-slate-600">Same API, different frontend. Angular 21 with zoneless signals via Angular CLI.</p>
        <nav class="inline-flex gap-2 rounded-full bg-slate-100 p-1 shadow-sm" aria-label="Views">
          <button
            class="rounded-full px-4 py-2 font-semibold text-sm transition"
            [class.bg-white]="view() === 'overview'"
            [class.text-slate-900]="view() === 'overview'"
            [class.shadow]="view() === 'overview'"
            [class.text-slate-600]="view() !== 'overview'"
            (click)="view.set('overview')"
          >
            Overview
          </button>
          <button
            class="rounded-full px-4 py-2 font-semibold text-sm transition"
            [class.bg-white]="view() === 'books'"
            [class.text-slate-900]="view() === 'books'"
            [class.shadow]="view() === 'books'"
            [class.text-slate-600]="view() !== 'books'"
            (click)="view.set('books')"
          >
            Books {{ summary() ? '(' + summary()!.total_books + ')' : '' }}
          </button>
        </nav>
      </header>

      @if (view() === 'overview') {
        <section class="space-y-2 rounded-2xl border border-slate-200 bg-white p-6 shadow-lg shadow-slate-200/40">
          @if (featured()) {
            <h2 class="font-semibold text-[#202235] text-xl">{{ summary()?.headline }}</h2>
            <p class="text-slate-600">Featured book</p>
            <article class="rounded-xl border border-slate-200 bg-gradient-to-b from-white to-slate-50 p-4">
              <h3 class="font-semibold text-[#202235] text-lg">{{ featured()!.title }}</h3>
              <p class="mt-1 text-slate-600">{{ featured()!.author }} • {{ featured()!.year }}</p>
              <p class="mt-1 text-[#202235] text-sm">{{ featured()!.tags.join(' · ') }}</p>
            </article>
          } @else {
            <div class="text-slate-600">Loading...</div>
          }
        </section>
      } @else {
        <section class="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3" aria-label="Books">
          @if (books().length > 0) {
            @for (book of books(); track book.id) {
              <article class="rounded-xl border border-slate-200 bg-gradient-to-b from-white to-slate-50 p-4 shadow-sm">
                <h3 class="font-semibold text-[#202235] text-lg">{{ book.title }}</h3>
                <p class="mt-1 text-slate-600">{{ book.author }} • {{ book.year }}</p>
                <p class="mt-1 text-[#202235] text-sm">{{ book.tags.join(' · ') }}</p>
              </article>
            }
          } @else {
            <div class="text-slate-600">Loading...</div>
          }
        </section>
      }

      <footer class="border-slate-200 border-t pt-8 text-slate-400 text-xs">
        <details>
          <summary class="cursor-pointer">Route definitions (from generated routes.ts)</summary>
          <div class="mt-2 grid grid-cols-1 gap-1 sm:grid-cols-2">
            @for (entry of routeEntries(); track entry[0]) {
              <span class="font-mono text-slate-600">
                {{ entry[0] }} → {{ entry[1].path }}
              </span>
            }
          </div>
        </details>
      </footer>
    </main>
  `,
})
export class HomeComponent implements OnInit {
  private http = inject(HttpClient)

  // Signals for reactive state
  summary = signal<Summary | null>(null)
  books = signal<Book[]>([])
  view = signal<"overview" | "books">("overview")

  // Computed signals
  featured = computed(() => this.summary()?.featured)
  routeEntries = computed(() => Object.entries(routeDefinitions) as RouteEntry[])

  ngOnInit() {
    // Fetch data on init
    this.http.get<Summary>(route("summary")).subscribe((data) => this.summary.set(data))
    this.http.get<Book[]>(route("books")).subscribe((data) => this.books.set(data))
  }
}
