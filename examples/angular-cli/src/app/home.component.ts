import { Component } from "@angular/core"

@Component({
  selector: "app-home",
  standalone: true,
  template: `
    <main>
      <section class="card">
        <h1>angular-cli</h1>
        <p>Angular CLI scaffold wired for Litestar APIs via <code>proxy.conf.json</code>.</p>
        <p>Run <code>npm start</code> and the backend on port 8000 to develop.</p>
      </section>
    </main>
  `,
  styles: [
    `
      main {
        max-width: 960px;
        margin: 4rem auto;
        padding: 0 1.5rem;
      }
      .card {
        background: white;
        border-radius: 12px;
        padding: 24px;
        box-shadow: 0 12px 30px rgba(15, 23, 42, 0.08);
        border: 1px solid #e2e8f0;
      }
      h1 {
        font-size: 2rem;
        margin-bottom: 0.75rem;
      }
      code {
        background: #0f172a;
        color: #e2e8f0;
        padding: 2px 6px;
        border-radius: 6px;
        font-size: 0.9em;
      }
    `,
  ],
})
export class HomeComponent {}
